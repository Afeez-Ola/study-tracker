import sqlite3
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.database.path
        self.max_sessions = config.database.max_sessions
        self.init_database()

    def init_database(self):
        """Initialize database with required tables"""
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS study_sessions (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    description TEXT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    active_seconds INTEGER DEFAULT 0,
                    idle_seconds INTEGER DEFAULT 0,
                    total_seconds INTEGER DEFAULT 0,
                    productivity REAL DEFAULT 0.0,
                    success BOOLEAN DEFAULT TRUE,
                    completion_notes TEXT,
                    state_history TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)

            # Activity events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    intensity REAL DEFAULT 0.0,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES study_sessions (id) ON DELETE CASCADE
                )
            """)

            # Database metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS db_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_date ON study_sessions(date(start_time))"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_topic ON study_sessions(topic)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_session ON activity_events(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_events(timestamp)"
            )

            # Initialize metadata
            self._set_metadata(conn, "storage_version", "1.0")
            self._set_metadata(conn, "created_at", datetime.utcnow().isoformat())

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _set_metadata(self, conn, key: str, value: str):
        """Set metadata value"""
        conn.execute(
            """
            INSERT OR REPLACE INTO db_metadata (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """,
            (key, value),
        )

    def get_metadata(self, key: str, default: str = None) -> Optional[str]:
        """Get metadata value"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT value FROM db_metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def create_session(
        self, topic: str, description: str = "", metadata: Dict[str, Any] = None
    ) -> str:
        """Create a new study session"""
        import uuid

        session_id = str(uuid.uuid4())

        with self.get_connection() as conn:
            # Check if we've exceeded max sessions
            cursor = conn.execute(
                "SELECT COUNT(*) FROM study_sessions WHERE success = TRUE"
            )
            session_count = cursor.fetchone()[0]

            if session_count >= self.max_sessions:
                # Archive oldest session
                conn.execute("""
                    DELETE FROM study_sessions 
                    WHERE id IN (
                        SELECT id FROM study_sessions 
                        WHERE success = TRUE 
                        ORDER BY start_time ASC 
                        LIMIT 1
                    )
                """)

            conn.execute(
                """
                INSERT INTO study_sessions 
                (id, topic, description, start_time, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    topic,
                    description,
                    datetime.utcnow().isoformat(),
                    json.dumps(metadata or {}),
                ),
            )

            conn.commit()
            logger.info(f"Created session {session_id}: {topic}")
            return session_id

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data"""
        try:
            with self.get_connection() as conn:
                # Build dynamic update query
                set_clauses = []
                values = []

                for key, value in data.items():
                    if key in [
                        "end_time",
                        "active_seconds",
                        "idle_seconds",
                        "total_seconds",
                        "productivity",
                        "success",
                        "completion_notes",
                        "state_history",
                    ]:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)

                if not set_clauses:
                    return False

                values.append(session_id)

                conn.execute(
                    f"""
                    UPDATE study_sessions 
                    SET {", ".join(set_clauses)}
                    WHERE id = ?
                """,
                    values,
                )

                conn.commit()
                logger.debug(f"Updated session {session_id}")
                return True

        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a single session"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()

            if row:
                session = dict(row)
                # Parse JSON fields
                if session["metadata"]:
                    session["metadata"] = json.loads(session["metadata"])
                if session["state_history"]:
                    session["state_history"] = json.loads(session["state_history"])
                return session

            return None

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        """Get currently active session (one without end_time)"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM study_sessions 
                WHERE end_time IS NULL 
                ORDER BY start_time DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()

            if row:
                session = dict(row)
                if session["metadata"]:
                    session["metadata"] = json.loads(session["metadata"])
                if session["state_history"]:
                    session["state_history"] = json.loads(session["state_history"])
                return session

            return None

    def get_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        date_from: str = None,
        date_to: str = None,
    ) -> List[Dict[str, Any]]:
        """Get sessions with pagination and filtering"""
        with self.get_connection() as conn:
            query = "SELECT * FROM study_sessions WHERE success = TRUE"
            params = []

            if date_from:
                query += " AND date(start_time) >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date(start_time) <= ?"
                params.append(date_to)

            query += " ORDER BY start_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            sessions = []

            for row in cursor.fetchall():
                session = dict(row)
                if session["metadata"]:
                    session["metadata"] = json.loads(session["metadata"])
                if session["state_history"]:
                    session["state_history"] = json.loads(session["state_history"])
                sessions.append(session)

            return sessions

    def log_activity_event(
        self,
        session_id: str,
        event_type: str,
        intensity: float = 0.0,
        details: Dict[str, Any] = None,
    ):
        """Log an activity event"""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO activity_events 
                (session_id, event_type, timestamp, intensity, details)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    event_type,
                    datetime.utcnow().isoformat(),
                    intensity,
                    json.dumps(details or {}),
                ),
            )

            conn.commit()

    def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        """Get activity events for a session"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM activity_events 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
            """,
                (session_id,),
            )

            events = []
            for row in cursor.fetchall():
                event = dict(row)
                if event["details"]:
                    event["details"] = json.loads(event["details"])
                events.append(event)

            return events

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        with self.get_connection() as conn:
            # Basic session stats
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(active_seconds) as total_active_seconds,
                    SUM(idle_seconds) as total_idle_seconds,
                    AVG(productivity) as avg_productivity,
                    MIN(start_time) as first_session,
                    MAX(start_time) as last_session
                FROM study_sessions 
                WHERE success = TRUE
            """)
            basic_stats = dict(cursor.fetchone() or {})

            # Convert to minutes for readability
            basic_stats["total_active_minutes"] = (
                basic_stats.get("total_active_seconds", 0) or 0
            ) // 60
            basic_stats["total_idle_minutes"] = (
                basic_stats.get("total_idle_seconds", 0) or 0
            ) // 60

            # Daily streak calculation
            cursor = conn.execute("""
                SELECT DISTINCT date(start_time) as study_date
                FROM study_sessions 
                WHERE success = TRUE AND start_time >= date('now', '-30 days')
                ORDER BY study_date DESC
            """)
            study_dates = [row[0] for row in cursor.fetchall()]

            streak = self._calculate_streak(study_dates)

            # Top topics
            cursor = conn.execute("""
                SELECT topic, COUNT(*) as session_count, SUM(active_seconds) as total_time
                FROM study_sessions 
                WHERE success = TRUE
                GROUP BY topic
                ORDER BY session_count DESC
                LIMIT 10
            """)
            top_topics = [dict(row) for row in cursor.fetchall()]

            # Productivity distribution
            cursor = conn.execute("""
                SELECT 
                    CASE 
                        WHEN productivity >= 90 THEN 'excellent'
                        WHEN productivity >= 75 THEN 'good'
                        WHEN productivity >= 60 THEN 'moderate'
                        WHEN productivity >= 40 THEN 'poor'
                        ELSE 'very_poor'
                    END as level,
                    COUNT(*) as count
                FROM study_sessions 
                WHERE success = TRUE
                GROUP BY level
                ORDER BY count DESC
            """)
            productivity_levels = dict(cursor.fetchall())

            return {
                "total_sessions": basic_stats.get("total_sessions", 0),
                "total_active_minutes": basic_stats.get("total_active_minutes", 0),
                "total_idle_minutes": basic_stats.get("total_idle_minutes", 0),
                "avg_productivity": round(
                    basic_stats.get("avg_productivity", 0) or 0, 1
                ),
                "streak": streak,
                "first_session": basic_stats.get("first_session"),
                "last_session": basic_stats.get("last_session"),
                "top_topics": top_topics,
                "productivity_levels": productivity_levels,
            }

    def _calculate_streak(self, study_dates: List[str]) -> int:
        """Calculate consecutive day streak"""
        if not study_dates:
            return 0

        today = datetime.now().date()
        streak = 0

        for i in range(365):  # Check up to a year
            check_date = today - timedelta(days=i)
            date_str = check_date.isoformat()

            if date_str in study_dates:
                streak += 1
            elif i == 0:
                # If no session today, check yesterday
                continue
            else:
                break

        return streak

    def export_sessions_csv(self) -> str:
        """Export sessions as CSV"""
        import io
        import csv

        sessions = self.get_sessions(limit=10000)  # Large limit for export

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "ID",
                "Topic",
                "Description",
                "Start Time",
                "End Time",
                "Active Minutes",
                "Idle Minutes",
                "Total Minutes",
                "Productivity",
                "Success",
                "Created At",
            ]
        )

        # Data rows
        for session in sessions:
            writer.writerow(
                [
                    session["id"],
                    session["topic"],
                    session.get("description", ""),
                    session["start_time"],
                    session.get("end_time", ""),
                    (session["active_seconds"] or 0) // 60,
                    (session["idle_seconds"] or 0) // 60,
                    (session["total_seconds"] or 0) // 60,
                    f"{session.get('productivity', 0):.1f}%",
                    session.get("success", True),
                    session["created_at"],
                ]
            )

        return output.getvalue()

    def import_sessions_csv(self, csv_content: str) -> Tuple[int, List[str]]:
        """Import sessions from CSV content"""
        import io
        import csv
        import uuid

        sessions = []
        errors = []

        try:
            csv_reader = csv.reader(io.StringIO(csv_content))

            # Skip header if present
            header = next(csv_reader, None)
            if header and "topic" in str(header).lower():
                pass  # Skip header
            else:
                # Reset reader if no header
                csv_reader = csv.reader(io.StringIO(csv_content))

            row_count = 0
            for row in csv_reader:
                row_count += 1
                if len(row) < 2:
                    errors.append(f"Row {row_count}: Too few columns")
                    continue

                try:
                    # Parse row (Topic, Start Time, Duration format)
                    topic = row[0].strip()
                    if not topic:
                        errors.append(f"Row {row_count}: Empty topic")
                        continue

                    # Parse duration (assumed to be in column 2)
                    duration_minutes = 0
                    if len(row) > 2 and row[2]:
                        try:
                            duration_minutes = int(float(row[2]))
                        except ValueError:
                            duration_minutes = 0

                    # Create session data
                    session = {
                        "id": str(uuid.uuid4()),
                        "topic": topic,
                        "description": row[1].strip() if len(row) > 1 else "",
                        "start_time": datetime.utcnow().isoformat(),
                        "end_time": datetime.utcnow().isoformat(),
                        "active_seconds": duration_minutes * 60,
                        "idle_seconds": 0,
                        "total_seconds": duration_minutes * 60,
                        "productivity": 100.0 if duration_minutes > 0 else 0.0,
                        "success": True,
                    }

                    sessions.append(session)

                except Exception as e:
                    errors.append(f"Row {row_count}: {str(e)}")
                    continue

            # Import sessions to database
            imported_count = 0
            for session in sessions:
                try:
                    if self.create_session(
                        session["topic"], session.get("description", "")
                    ):
                        self.update_session(
                            session["id"],
                            {
                                k: v
                                for k, v in session.items()
                                if k not in ["id", "topic", "description"]
                            },
                        )
                        imported_count += 1
                except Exception as e:
                    errors.append(f"Error importing session: {str(e)}")

            return imported_count, errors

        except Exception as e:
            return 0, [f"CSV parsing error: {str(e)}"]

    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            with self.get_connection() as conn:
                # Test basic operations
                cursor = conn.execute("SELECT COUNT(*) FROM study_sessions")
                session_count = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM activity_events")
                event_count = cursor.fetchone()[0]

                # Check database file size
                db_size = (
                    os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                )

                return {
                    "status": "healthy",
                    "session_count": session_count,
                    "event_count": event_count,
                    "db_size_bytes": db_size,
                    "db_path": self.db_path,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old activity events"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM activity_events 
                WHERE timestamp < ? AND session_id NOT IN (
                    SELECT id FROM study_sessions WHERE end_time IS NULL
                )
            """,
                (cutoff_date.isoformat(),),
            )

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Cleaned up {deleted_count} old activity events")
            return deleted_count


# Global database instance
db_manager = DatabaseManager()
