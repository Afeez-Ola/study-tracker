import time
import threading
import platform
import logging
import gc
from collections import deque
from typing import Dict, Any, Optional, Callable, Set
from datetime import datetime, timedelta

# Import pynput with error handling
try:
    from pynput import keyboard, mouse

    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logging.warning("pynput not available - activity monitoring will be limited")

from database import DatabaseManager
from session_manager import SessionManager
from config import config

logger = logging.getLogger(__name__)


class ActivityType:
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    IDLE = "idle"
    SYSTEM = "system"


class ActivityEvent:
    def __init__(
        self,
        timestamp: float,
        activity_type: str,
        intensity: float = 0.0,
        details: Dict[str, Any] = None,
    ):
        self.timestamp = timestamp
        self.activity_type = activity_type
        self.intensity = intensity
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "activity_type": self.activity_type,
            "intensity": self.intensity,
            "details": self.details,
        }


class ActivityMonitor:
    """Cross-platform activity monitoring with privacy protection"""

    def __init__(
        self, session_manager: SessionManager = None, db_manager: DatabaseManager = None
    ):
        self.session_manager = session_manager or SessionManager()
        self.db_manager = db_manager or DatabaseManager()

        # Configuration
        self.idle_threshold = config.monitoring.idle_threshold_seconds
        self.check_interval_ms = config.monitoring.activity_check_interval_ms

        # State management
        self.is_monitoring = False
        self.is_paused = False
        self.current_session_id = None
        self.last_activity_time = time.time()
        self.idle_state = False
        self.idle_start_time = None

        # Activity tracking
        self.activity_history = deque(maxlen=1000)
        self.keypress_times = deque(maxlen=10)
        self.mouse_positions = deque(maxlen=5)
        self.last_intensity_calculation = time.time()

        # Time tracking
        self.total_active_time = 0
        self.total_idle_time = 0

        # Fallback mode (when pynput fails)
        self.fallback_mode = False

        # Threading
        self.shutdown_event = threading.Event()
        self.monitor_thread = None
        self.intensity_thread = None
        self.activity_lock = threading.Lock()

        # pynput listeners
        self.keyboard_listener = None
        self.mouse_listener = None

        # Platform
        self.platform = platform.system()
        self.permissions_ok = True

        # Callbacks
        self.activity_callbacks = []
        self.idle_callbacks = []
        self.error_callbacks = []

        # Performance
        self.last_cleanup = time.time()
        self.cleanup_interval = 60  # seconds

        # Check permissions
        self._check_permissions()

    def _check_permissions(self) -> bool:
        """Check platform-specific permissions"""
        if not PYNPUT_AVAILABLE:
            self.permissions_ok = False
            return False

        if self.platform == "Darwin":  # macOS
            try:
                # Test accessibility permissions
                controller = keyboard.Controller()
                controller.press(keyboard.Key.shift)
                controller.release(keyboard.Key.shift)
                logger.info("macOS accessibility permissions: OK")
                return True
            except Exception as e:
                logger.error(f"macOS accessibility permissions error: {e}")
                self.permissions_ok = False
                return False

        elif self.platform in ["Windows", "Linux"]:
            try:
                # Windows and Linux typically work without special permissions
                controller = keyboard.Controller()
                logger.info(f"{self.platform} input monitoring: OK")
                return True
            except Exception as e:
                logger.error(f"{self.platform} input monitoring error: {e}")
                self.permissions_ok = False
                return False

        return True

    def start_monitoring(self, session_id: str) -> bool:
        """Start activity monitoring for a session"""
        if not self.permissions_ok:
            logger.warning("Cannot start monitoring - permissions not available")
            return False

        with self.activity_lock:
            if self.is_monitoring:
                logger.warning("Monitoring already active")
                return True

            try:
                self.current_session_id = session_id
                self.last_activity_time = time.time()
                self.idle_state = False
                self.is_monitoring = True
                self.is_paused = False

                # Clear buffers
                self.activity_history.clear()
                self.keypress_times.clear()
                self.mouse_positions.clear()

                # Reset shutdown event
                self.shutdown_event.clear()

                # Start input listeners (with fallback if they fail)
                listeners_started = self._start_input_listeners()
                if not listeners_started:
                    logger.warning(
                        "Input listeners failed to start - falling back to timer-only mode"
                    )
                    self.fallback_mode = True
                else:
                    self.fallback_mode = False

                # Start background threads (always works even without listeners)
                self.monitor_thread = threading.Thread(
                    target=self._idle_detection_loop,
                    daemon=True,
                    name="ActivityMonitor-IdleDetection",
                )
                self.monitor_thread.start()

                self.intensity_thread = threading.Thread(
                    target=self._intensity_calculation_loop,
                    daemon=True,
                    name="ActivityMonitor-Intensity",
                )
                self.intensity_thread.start()

                if self.fallback_mode:
                    logger.info(
                        f"Started timer-based monitoring for session {session_id} (no system activity tracking)"
                    )
                else:
                    logger.info(f"Started activity monitoring for session {session_id}")

                # Log start event
                self._log_activity_event(
                    "monitoring_started", 1.0, {"session_id": session_id}
                )

                return True

            except Exception as e:
                logger.error(f"Failed to start monitoring: {e}")
                self._cleanup()
                return False

    def stop_monitoring(self) -> bool:
        """Stop activity monitoring"""
        with self.activity_lock:
            if not self.is_monitoring:
                return True

            try:
                self.is_monitoring = False
                self.shutdown_event.set()

                # Stop input listeners
                self._stop_input_listeners()

                # Stop threads
                self._wait_for_threads()

                # Log final stats
                final_stats = self._calculate_current_stats()
                self._log_activity_event(
                    "monitoring_stopped",
                    0.0,
                    {"session_id": self.current_session_id, "final_stats": final_stats},
                )

                logger.info("Stopped activity monitoring")

                # Clean up
                self._cleanup()

                return True

            except Exception as e:
                logger.error(f"Error stopping monitoring: {e}")
                return False

    def pause_monitoring(self) -> bool:
        """Pause activity monitoring"""
        if not self.is_monitoring:
            return False

        with self.activity_lock:
            self.is_paused = True

            # Log pause event
            self._log_activity_event(
                "monitoring_paused", 0.0, {"session_id": self.current_session_id}
            )

            logger.info("Paused activity monitoring")
            return True

    def resume_monitoring(self) -> bool:
        """Resume activity monitoring"""
        if not self.is_monitoring or not self.is_paused:
            return False

        with self.activity_lock:
            self.is_paused = False
            self.last_activity_time = time.time()

            # Log resume event
            self._log_activity_event(
                "monitoring_resumed", 1.0, {"session_id": self.current_session_id}
            )

            logger.info("Resumed activity monitoring")
            return True

    def is_idle(self) -> bool:
        """Check if user is currently idle"""
        time_since_activity = time.time() - self.last_activity_time
        return time_since_activity >= self.idle_threshold

    def get_current_stats(self) -> Dict[str, Any]:
        """Get current activity statistics"""
        with self.activity_lock:
            if not self.is_monitoring or not self.current_session_id:
                return {
                    "total_seconds": 0,
                    "active_seconds": 0,
                    "idle_seconds": 0,
                    "productivity": 0,
                    "currently_active": False,
                    "intensity": 0.0,
                }

            stats = self._calculate_current_stats()
            return stats

    def _start_input_listeners(self) -> bool:
        """Start keyboard and mouse listeners with robust error handling"""
        if not PYNPUT_AVAILABLE:
            logger.warning("pynput not available - monitoring disabled")
            return False

        try:
            # Wrap callbacks in try-except to handle macOS threading issues
            def on_key_press(key):
                try:
                    if not self.is_monitoring or self.is_paused:
                        return
                    self._on_keyboard_activity(key)
                except Exception as e:
                    logger.debug(f"Keyboard callback error: {e}")

            def on_mouse_move(x, y):
                try:
                    if not self.is_monitoring or self.is_paused:
                        return
                    self._on_mouse_activity(x, y, 0, 0)
                except Exception as e:
                    logger.debug(f"Mouse move callback error: {e}")

            def on_mouse_click(x, y, button, pressed):
                try:
                    if not self.is_monitoring or self.is_paused:
                        return
                    self._on_mouse_activity(x, y, 1, 1)
                except Exception as e:
                    logger.debug(f"Mouse click callback error: {e}")

            # Start keyboard listener with macOS compatibility workaround
            try:
                # Use suppress=False to avoid permission issues on macOS
                self.keyboard_listener = keyboard.Listener(
                    on_press=on_key_press, suppress=False, daemon=True
                )
                self.keyboard_listener.start()
                logger.info("Keyboard listener started")
            except Exception as e:
                logger.error(f"Failed to start keyboard listener: {e}")
                logger.warning("Continuing without keyboard monitoring")
                # Don't return False - allow fallback to mouse-only monitoring

            # Start mouse listener
            try:
                self.mouse_listener = mouse.Listener(
                    on_move=on_mouse_move,
                    on_click=on_mouse_click,
                    suppress=False,
                    daemon=True,
                )
                self.mouse_listener.start()
                logger.info("Mouse listener started")
            except Exception as e:
                logger.error(f"Failed to start mouse listener: {e}")
                logger.warning("Continuing without mouse monitoring")

            # Check if at least one listener started successfully
            if not hasattr(self, "keyboard_listener") and not hasattr(
                self, "mouse_listener"
            ):
                logger.error("No input listeners could be started")
                return False

            logger.info("Started input listeners (with fallbacks if needed)")
            return True

        except Exception as e:
            logger.error(f"Failed to start input listeners: {e}")
            return False

    def _stop_input_listeners(self):
        """Stop input listeners"""
        try:
            if hasattr(self, "keyboard_listener") and self.keyboard_listener:
                self.keyboard_listener.stop()
            if hasattr(self, "mouse_listener") and self.mouse_listener:
                self.mouse_listener.stop()
            logger.info("Stopped input listeners")
        except Exception as e:
            logger.error(f"Error stopping input listeners: {e}")

    def _on_keyboard_activity(self, key):
        """Handle keyboard activity with error handling"""
        try:
            current_time = time.time()
            self.last_activity_time = current_time

            # Record keypress for intensity calculation
            self.keypress_times.append(current_time)

            # Create activity event
            event = ActivityEvent(
                timestamp=current_time,
                activity_type=ActivityType.KEYBOARD,
                intensity=self._calculate_keyboard_intensity(),
                details={"key": self._sanitize_key(str(key))},
            )

            self._record_activity_event(event)
        except Exception as e:
            logger.debug(f"Keyboard activity error: {e}")

    def _on_mouse_activity(self, x, y, dx, dy):
        """Handle mouse activity with error handling"""
        try:
            current_time = time.time()
            self.last_activity_time = current_time

            # Track mouse position for movement patterns
            self.mouse_positions.append((x, y, current_time))

            # Calculate movement intensity
            distance = (dx**2 + dy**2) ** 0.5
            intensity = min(distance / 100.0, 1.0)  # Normalize to 0-1

            # Create activity event
            event = ActivityEvent(
                timestamp=current_time,
                activity_type=ActivityType.MOUSE,
                intensity=intensity,
                details={"position": (x, y), "movement": (dx, dy)},
            )

            self._record_activity_event(event)
        except Exception as e:
            logger.debug(f"Mouse activity error: {e}")

    def _record_activity_event(self, event: ActivityEvent):
        """Record an activity event"""
        with self.activity_lock:
            self.activity_history.append(event)

            # Update session manager
            if self.session_manager:
                self.session_manager.update_session_activity(event.to_dict())

            # Update database if we have a session
            if self.current_session_id and self.db_manager:
                self.db_manager.log_activity_event(
                    self.current_session_id,
                    event.activity_type,
                    event.intensity,
                    event.details,
                )

            # Trigger callbacks
            for callback in self.activity_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in activity callback: {e}")

    def _idle_detection_loop(self):
        """Background thread for idle detection"""
        while not self.shutdown_event.is_set():
            try:
                if self.is_monitoring and not self.is_paused:
                    current_time = time.time()
                    time_since_last_activity = current_time - self.last_activity_time

                    was_idle = self.idle_state
                    currently_idle = time_since_last_activity >= self.idle_threshold

                    # Handle idle state changes
                    if was_idle != currently_idle:
                        self.idle_state = currently_idle

                        event = ActivityEvent(
                            timestamp=current_time,
                            activity_type=ActivityType.IDLE,
                            intensity=0.0 if currently_idle else 0.1,
                            details={"idle_state": currently_idle},
                        )

                        self._record_activity_event(event)

                        # Update session manager
                        if self.session_manager:
                            self.session_manager.update_session_idle_state(
                                currently_idle, current_time
                            )

                        # Trigger idle callbacks
                        for callback in self.idle_callbacks:
                            try:
                                callback(currently_idle, current_time)
                            except Exception as e:
                                logger.error(f"Error in idle callback: {e}")

                # Sleep for check interval
                self.shutdown_event.wait(self.check_interval_ms / 1000.0)

            except Exception as e:
                logger.error(f"Error in idle detection loop: {e}")

    def _intensity_calculation_loop(self):
        """Background thread for intensity calculations"""
        while not self.shutdown_event.is_set():
            try:
                current_time = time.time()

                # Periodic cleanup
                if current_time - self.last_cleanup >= self.cleanup_interval:
                    self._perform_cleanup()
                    self.last_cleanup = current_time

                # Calculate current intensity
                intensity = self._calculate_overall_intensity()

                # Trigger callbacks
                for callback in self.activity_callbacks:
                    try:
                        callback(
                            ActivityEvent(
                                timestamp=current_time,
                                activity_type=ActivityType.SYSTEM,
                                intensity=intensity,
                                details={"type": "intensity_update"},
                            )
                        )
                    except Exception as e:
                        logger.error(f"Error in intensity callback: {e}")

                # Adaptive sleep based on activity level
                sleep_time = 0.5 if intensity > 0.5 else 1.0
                self.shutdown_event.wait(sleep_time)

            except Exception as e:
                logger.error(f"Error in intensity calculation loop: {e}")

    def _calculate_keyboard_intensity(self) -> float:
        """Calculate typing intensity"""
        if len(self.keypress_times) < 2:
            return 0.1

        current_time = time.time()
        recent_keypresses = [
            t
            for t in self.keypress_times
            if current_time - t <= 5.0  # Last 5 seconds
        ]

        if not recent_keypresses:
            return 0.1

        # Calculate typing speed
        time_span = recent_keypresses[-1] - recent_keypresses[0]
        if time_span <= 0:
            return 0.1

        keys_per_second = len(recent_keypresses) / time_span

        # Normalize to 0-1 scale (max expected: 10 keys/second)
        intensity = min(keys_per_second / 10.0, 1.0)
        return max(intensity, 0.1)

    def _calculate_overall_intensity(self) -> float:
        """Calculate overall activity intensity"""
        keyboard_intensity = self._calculate_keyboard_intensity()
        mouse_intensity = self._calculate_mouse_intensity()

        # Weight keyboard and mouse activity (keyboard is more indicative of work)
        overall_intensity = keyboard_intensity * 0.7 + mouse_intensity * 0.3

        # Apply decay based on time since last activity
        time_since_activity = time.time() - self.last_activity_time
        decay_factor = max(0, 1.0 - (time_since_activity / self.idle_threshold))

        final_intensity = overall_intensity * decay_factor
        return max(final_intensity, 0.0)

    def _calculate_mouse_intensity(self) -> float:
        """Calculate mouse activity intensity"""
        if len(self.mouse_positions) < 2:
            return 0.1

        current_time = time.time()
        recent_positions = [
            (x, y, t)
            for x, y, t in self.mouse_positions
            if current_time - t <= 2.0  # Last 2 seconds
        ]

        if len(recent_positions) < 2:
            return 0.1

        # Calculate total distance moved
        total_distance = 0
        for i in range(1, len(recent_positions)):
            x1, y1, t1 = recent_positions[i - 1]
            x2, y2, t2 = recent_positions[i]
            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            total_distance += distance

        # Calculate average velocity
        time_span = recent_positions[-1][2] - recent_positions[0][2]
        if time_span <= 0:
            return 0.1

        avg_velocity = total_distance / time_span

        # Normalize to 0-1 scale (max expected: 1000 pixels/second)
        intensity = min(avg_velocity / 1000.0, 1.0)
        return max(intensity, 0.1)

    def _calculate_current_stats(self) -> Dict[str, Any]:
        """Calculate current activity statistics"""
        current_time = time.time()

        # Use session manager start time as fallback
        session_status = self.session_manager.get_current_status()
        if session_status.get("active") and session_status.get("current_session"):
            session_start_time = session_status["current_session"].get("start_time", "")
            if session_start_time:
                try:
                    import datetime

                    dt = datetime.datetime.fromisoformat(
                        session_start_time.replace("Z", "+00:00")
                    )
                    session_start_time = dt.timestamp()
                except:
                    session_start_time = current_time
            else:
                session_start_time = current_time
        else:
            session_start_time = current_time

        total_time = current_time - session_start_time

        # Calculate active vs idle time
        if self.is_paused:
            active_time = self.total_active_time
            idle_time = total_time
        else:
            time_since_activity = current_time - self.last_activity_time

            if time_since_activity >= self.idle_threshold:
                # Currently idle
                if self.idle_start_time is None:
                    idle_time = self.total_idle_time + time_since_activity
                else:
                    idle_time = self.total_idle_time + (
                        time.time() - self.idle_start_time
                    )
                active_time = total_time - idle_time
            else:
                # Currently active
                active_time = self.total_active_time + min(time_since_activity, 1.0)
                idle_time = self.total_idle_time

        # Calculate productivity
        productivity = (active_time / total_time * 100) if total_time > 0 else 0

        return {
            "total_seconds": int(total_time),
            "active_seconds": int(active_time),
            "idle_seconds": int(idle_time),
            "productivity": round(productivity, 1),
            "currently_active": not self.is_idle() and not self.is_paused,
            "intensity": self._calculate_overall_intensity(),
        }

    def _perform_cleanup(self):
        """Perform periodic cleanup to optimize memory"""
        try:
            # Clear old activity events
            cutoff_time = time.time() - 300  # Keep last 5 minutes
            self.activity_history = deque(
                (
                    event
                    for event in self.activity_history
                    if event.timestamp > cutoff_time
                ),
                maxlen=1000,
            )

            # Clear old timing data
            cutoff_time = time.time() - 60  # Keep last minute
            self.keypress_times = deque(
                (t for t in self.keypress_times if t > cutoff_time), maxlen=10
            )

            self.mouse_positions = deque(
                (pos for pos in self.mouse_positions if pos[2] > cutoff_time), maxlen=5
            )

            # Force garbage collection
            gc.collect()

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _sanitize_key(self, key_str: str) -> str:
        """Sanitize key input for privacy"""
        # Remove sensitive information from keys
        sensitive_patterns = ["password", "passwd", "pwd", "secret", "key"]
        key_lower = key_str.lower()

        for pattern in sensitive_patterns:
            if pattern in key_lower:
                return "[REDACTED]"

        # Limit key length
        return key_str[:20]

    def _log_activity_event(
        self, event_type: str, intensity: float, details: Dict[str, Any]
    ):
        """Log activity event to database"""
        try:
            if self.current_session_id and self.db_manager:
                self.db_manager.log_activity_event(
                    self.current_session_id, event_type, intensity, details
                )
        except Exception as e:
            logger.error(f"Error logging activity event: {e}")

    def _wait_for_threads(self, timeout: float = 5.0):
        """Wait for background threads to finish"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=timeout)

        if self.intensity_thread and self.intensity_thread.is_alive():
            self.intensity_thread.join(timeout=timeout)

    def _cleanup(self):
        """Clean up resources"""
        self.current_session_id = None
        self.is_monitoring = False
        self.is_paused = False
        self.activity_history.clear()
        self.keypress_times.clear()
        self.mouse_positions.clear()

    def add_activity_callback(self, callback: Callable):
        """Add callback for activity events"""
        self.activity_callbacks.append(callback)

    def add_idle_callback(self, callback: Callable):
        """Add callback for idle state changes"""
        self.idle_callbacks.append(callback)

    def add_error_callback(self, callback: Callable):
        """Add callback for errors"""
        self.error_callbacks.append(callback)

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of activity monitor"""
        return {
            "monitoring": self.is_monitoring,
            "paused": self.is_paused,
            "permissions_ok": self.permissions_ok,
            "pynput_available": PYNPUT_AVAILABLE,
            "platform": self.platform,
            "current_session_id": self.current_session_id,
            "activity_history_size": len(self.activity_history),
            "last_activity": self.last_activity_time,
        }


# Global activity monitor instance
activity_monitor = ActivityMonitor()
