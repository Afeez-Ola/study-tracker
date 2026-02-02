import time
import threading
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from database import DatabaseManager
from config import config

logger = logging.getLogger(__name__)


class SessionState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class SessionManager:
    """Core session management with state machine and productivity calculations"""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        self.current_session = None
        self.session_state = SessionState.IDLE
        self.state_lock = threading.Lock()

        # Time tracking
        self.session_start_time = None
        self.last_activity_time = None
        self.idle_start_time = None
        self.total_active_time = 0
        self.total_idle_time = 0

        # Session history
        self.state_history = []
        self.session_observers = []

        # Configuration
        self.idle_threshold = config.monitoring.idle_threshold_seconds

    def start_session(
        self, topic: str, description: str = "", metadata: Dict[str, Any] = None
    ) -> str:
        """Start a new study session"""
        with self.state_lock:
            if self.session_state != SessionState.IDLE:
                raise ValueError(
                    f"Cannot start session - currently in {self.session_state.value} state"
                )

            try:
                # Create session in database
                session_id = self.db_manager.create_session(
                    topic, description, metadata
                )

                # Initialize session state
                # Use time.time() for consistent timezone-agnostic timing
                start_timestamp = time.time()

                self.current_session = {
                    "id": session_id,
                    "topic": topic,
                    "description": description,
                    "metadata": metadata or {},
                    "created_at": datetime.utcnow().isoformat(),  # For display only
                    "start_timestamp": start_timestamp,  # For accurate timing
                }

                # Update timing
                self.session_start_time = start_timestamp
                self.last_activity_time = time.time()
                self.total_active_time = 0
                self.total_idle_time = 0
                self.idle_start_time = None

                # Transition state
                self._transition_state(SessionState.ACTIVE, "Session started")

                # Log activity event
                self.db_manager.log_activity_event(
                    session_id,
                    "session_started",
                    1.0,
                    {"topic": topic, "description": description},
                )

                logger.info(f"Started session {session_id}: {topic}")
                self._notify_observers(
                    "session_started", {"session_id": session_id, "topic": topic}
                )

                return session_id

            except Exception as e:
                logger.error(f"Failed to start session: {e}")
                self._cleanup_session()
                raise

    def pause_session(self, reason: str = "manual") -> Dict[str, Any]:
        """Pause the current session"""
        with self.state_lock:
            if self.session_state != SessionState.ACTIVE:
                raise ValueError(
                    f"Cannot pause session - currently in {self.session_state.value} state"
                )

            self._update_time_tracking()
            self.idle_start_time = time.time()

            session_data = self._transition_state(SessionState.PAUSED, reason)

            # Log pause event
            self.db_manager.log_activity_event(
                self.current_session["id"], "session_paused", 0.0, {"reason": reason}
            )

            logger.info(f"Paused session {self.current_session['id']}: {reason}")

            # Return current stats
            return self._get_session_stats()

    def resume_session(self) -> Dict[str, Any]:
        """Resume a paused session"""
        with self.state_lock:
            if self.session_state != SessionState.PAUSED:
                raise ValueError(
                    f"Cannot resume session - currently in {self.session_state.value} state"
                )

            # Calculate pause duration
            if self.idle_start_time:
                pause_duration = time.time() - self.idle_start_time
                self.total_idle_time += pause_duration
                self.idle_start_time = None

            self.last_activity_time = time.time()

            session_data = self._transition_state(
                SessionState.ACTIVE, "Session resumed"
            )

            # Log resume event
            self.db_manager.log_activity_event(
                self.current_session["id"], "session_resumed", 1.0, {}
            )

            logger.info(f"Resumed session {self.current_session['id']}")

            # Return current stats
            return self._get_session_stats()

    def stop_session(
        self, success: bool = True, completion_notes: str = ""
    ) -> Dict[str, Any]:
        """Complete the current session"""
        with self.state_lock:
            if self.session_state not in [SessionState.ACTIVE, SessionState.PAUSED]:
                raise ValueError(
                    f"Cannot stop session - currently in {self.session_state.value} state"
                )

            try:
                self._update_time_tracking()

                # Calculate final statistics
                stats = self._calculate_final_productivity()

                # Update session in database
                session_data = {
                    "end_time": datetime.utcnow().isoformat(),
                    "active_seconds": int(self.total_active_time),
                    "idle_seconds": int(self.total_idle_time),
                    "total_seconds": int(self.total_active_time + self.total_idle_time),
                    "productivity": stats["productivity"],
                    "success": success,
                    "completion_notes": completion_notes,
                    "state_history": json.dumps(self.state_history),
                }

                self.db_manager.update_session(self.current_session["id"], session_data)

                # Transition state
                final_state_data = self._transition_state(
                    SessionState.COMPLETED, f"Session completed: {completion_notes}"
                )

                # Log completion event
                self.db_manager.log_activity_event(
                    self.current_session["id"],
                    "session_completed",
                    stats["productivity"] / 100,
                    {
                        "success": success,
                        "notes": completion_notes,
                        "productivity": stats["productivity"],
                    },
                )

                # Create session summary
                session_summary = {
                    "session_id": self.current_session["id"],
                    "topic": self.current_session["topic"],
                    "total_minutes": int(self.total_active_time + self.total_idle_time)
                    // 60,
                    "active_minutes": int(self.total_active_time) // 60,
                    "idle_minutes": int(self.total_idle_time) // 60,
                    "productivity": stats["productivity"],
                    "productivity_level": stats["level"],
                    "success": success,
                }

                logger.info(
                    f"Completed session {self.current_session['id']}: {session_summary}"
                )
                self._notify_observers("session_completed", session_summary)

                # Clean up session
                self._cleanup_session()

                return session_summary

            except Exception as e:
                logger.error(f"Failed to stop session: {e}")
                self._cleanup_session()
                raise

    def get_current_status(self) -> Dict[str, Any]:
        """Get current session status and statistics"""
        with self.state_lock:
            if not self.current_session or self.session_state == SessionState.IDLE:
                return {
                    "active": False,
                    "state": "idle",
                    "total_seconds": 0,
                    "active_seconds": 0,
                    "idle_seconds": 0,
                    "productivity": 0,
                    "current_session": None,
                }

            self._update_time_tracking()
            current_time = time.time()
            total_elapsed = current_time - self.session_start_time

            # Calculate current productivity
            productivity = 0.0
            if total_elapsed > 0:
                productivity = (self.total_active_time / total_elapsed) * 100

            return {
                "active": True,
                "state": self.session_state.value,
                "total_seconds": int(total_elapsed),
                "active_seconds": int(self.total_active_time),
                "idle_seconds": int(self.total_idle_time),
                "productivity": round(productivity, 1),
                "current_session": {
                    "id": self.current_session["id"],
                    "topic": self.current_session["topic"],
                    "description": self.current_session.get("description", ""),
                    "start_time": self.current_session.get(
                        "start_timestamp", self.session_start_time
                    ),
                    "metadata": self.current_session.get("metadata", {}),
                },
            }

    def update_session_activity(self, activity_data: Dict[str, Any]) -> None:
        """Update session with new activity data"""
        with self.state_lock:
            if not self.current_session or self.session_state != SessionState.ACTIVE:
                return

            # Update last activity time
            if "timestamp" in activity_data:
                self.last_activity_time = activity_data["timestamp"]
            else:
                self.last_activity_time = time.time()

            # Log activity event
            if self.current_session:
                self.db_manager.log_activity_event(
                    self.current_session["id"],
                    activity_data.get("type", "unknown"),
                    activity_data.get("intensity", 0.0),
                    activity_data.get("details", {}),
                )

    def update_session_idle_state(self, is_idle: bool, timestamp: float) -> None:
        """Update session idle state"""
        with self.state_lock:
            if not self.current_session or self.session_state != SessionState.ACTIVE:
                return

            if is_idle:
                if not self.idle_start_time:
                    self.idle_start_time = timestamp
            else:
                if self.idle_start_time:
                    idle_duration = timestamp - self.idle_start_time
                    self.total_idle_time += idle_duration
                    self.idle_start_time = None

            self.last_activity_time = timestamp

    def add_observer(self, callback):
        """Add observer for session events"""
        self.session_observers.append(callback)

    def remove_observer(self, callback):
        """Remove observer"""
        if callback in self.session_observers:
            self.session_observers.remove(callback)

    def _transition_state(
        self, new_state: SessionState, reason: str = ""
    ) -> Dict[str, Any]:
        """Transition to new state and record in history"""
        old_state = self.session_state
        self.session_state = new_state

        state_change = {
            "timestamp": time.time(),
            "from_state": old_state.value,
            "to_state": new_state.value,
            "reason": reason,
            "session_time": time.time() - self.session_start_time
            if self.session_start_time
            else 0,
        }

        self.state_history.append(state_change)

        # Notify observers
        self._notify_observers("state_changed", state_change)

        return state_change

    def _update_time_tracking(self):
        """Update time tracking based on current state"""
        if not self.session_start_time:
            return

        current_time = time.time()

        if self.session_state == SessionState.ACTIVE:
            # Check if currently idle
            time_since_activity = current_time - self.last_activity_time

            if time_since_activity >= self.idle_threshold:
                # Currently idle
                if self.idle_start_time is None:
                    self.idle_start_time = self.last_activity_time + self.idle_threshold
            else:
                # Currently active
                if self.idle_start_time:
                    # Add idle time and reset
                    self.total_idle_time += time.time() - self.idle_start_time
                    self.idle_start_time = None

                # Add active time since last activity
                self.total_active_time += min(
                    time_since_activity, 1.0
                )  # Add at most 1 second

        elif self.session_state == SessionState.PAUSED:
            # All time is idle during pause
            if self.idle_start_time:
                self.total_idle_time += current_time - self.idle_start_time

    def _calculate_final_productivity(self) -> Dict[str, Any]:
        """Calculate final productivity metrics"""
        total_time = self.total_active_time + self.total_idle_time

        if total_time == 0:
            return {
                "productivity": 0.0,
                "level": "none",
                "efficiency": 0.0,
                "focus_ratio": 0.0,
            }

        # Base efficiency (active time / total time)
        efficiency = (self.total_active_time / total_time) * 100

        # Focus ratio (active time / session time)
        session_time = time.time() - self.session_start_time
        focus_ratio = (
            (self.total_active_time / session_time) * 100 if session_time > 0 else 0
        )

        # Final productivity score
        productivity = efficiency

        # Productivity level
        if productivity >= 90:
            level = "excellent"
        elif productivity >= 75:
            level = "good"
        elif productivity >= 60:
            level = "moderate"
        elif productivity >= 40:
            level = "poor"
        else:
            level = "very_poor"

        return {
            "productivity": round(productivity, 1),
            "level": level,
            "efficiency": round(efficiency, 1),
            "focus_ratio": round(focus_ratio, 1),
        }

    def _get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        if not self.session_start_time:
            return {}

        self._update_time_tracking()
        current_time = time.time()
        total_time = current_time - self.session_start_time

        return {
            "total_seconds": int(total_time),
            "active_seconds": int(self.total_active_time),
            "idle_seconds": int(self.total_idle_time),
            "productivity": round((self.total_active_time / total_time) * 100, 1)
            if total_time > 0
            else 0,
        }

    def _notify_observers(self, event_type: str, data: Dict[str, Any]):
        """Notify all observers of session events"""
        for observer in self.session_observers:
            try:
                observer(event_type, data)
            except Exception as e:
                logger.error(f"Error notifying observer: {e}")

    def _cleanup_session(self):
        """Clean up current session state"""
        self.current_session = None
        self.session_state = SessionState.IDLE
        self.session_start_time = None
        self.last_activity_time = None
        self.idle_start_time = None
        self.total_active_time = 0
        self.total_idle_time = 0
        self.state_history = []

    def get_session_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent session history"""
        return self.db_manager.get_sessions(limit=limit)

    def validate_session_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Validate session operations"""
        errors = []

        if operation == "start":
            topic = kwargs.get("topic", "")
            if not topic or len(topic.strip()) < 1:
                errors.append("Topic is required")
            elif len(topic) > 200:
                errors.append("Topic too long (max 200 characters)")

            # Check for recent sessions
            recent_sessions = self.db_manager.get_sessions(limit=5)
            if len(recent_sessions) >= 50:  # Too many sessions started recently
                errors.append("Too many sessions started recently")

        elif operation == "pause":
            if self.session_state != SessionState.ACTIVE:
                errors.append("No active session to pause")

        elif operation == "resume":
            if self.session_state != SessionState.PAUSED:
                errors.append("No paused session to resume")

        elif operation == "stop":
            if self.session_state not in [SessionState.ACTIVE, SessionState.PAUSED]:
                errors.append("No active session to stop")

        return {"valid": len(errors) == 0, "errors": errors}


# Global session manager instance
session_manager = SessionManager()
