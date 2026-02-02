import os
import json
import logging
from datetime import datetime
from flask import (
    Flask,
    request,
    jsonify,
    Response,
    send_from_directory,
    render_template,
)
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
from werkzeug.datastructures import FileStorage

# Import components
from database import DatabaseManager
from session_manager import SessionManager
from activity_monitor import ActivityMonitor
from config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")

# Configure app
app.config.update(
    {
        "DEBUG": config.debug,
        "SECRET_KEY": config.security.secret_key,
        "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB max file size
    }
)

# Initialize components
db_manager = DatabaseManager()
session_manager = SessionManager(db_manager)
activity_monitor = ActivityMonitor(session_manager, db_manager)


# Setup CORS manually (simpler approach for now)
@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    origin = request.headers.get("Origin")
    allowed_origins = config.security.cors_origins

    if origin in allowed_origins or "*" in allowed_origins:
        response.headers.add("Access-Control-Allow-Origin", origin or "*")

    response.headers.add(
        "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
    )
    response.headers.add(
        "Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With"
    )
    response.headers.add("Access-Control-Max-Age", "86400")

    return response


@app.before_request
def handle_options():
    """Handle OPTIONS requests for CORS"""
    if request.method == "OPTIONS":
        response = Response()
        response.headers.add(
            "Access-Control-Allow-Origin", request.headers.get("Origin", "*")
        )
        response.headers.add(
            "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers.add(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Requested-With",
        )
        return response, 200


def validate_json_request(required_fields: list = None) -> dict:
    """Validate JSON request and return data"""
    if not request.is_json:
        raise BadRequest("Request must be JSON")

    data = request.get_json()
    if not data:
        raise BadRequest("Invalid JSON data")

    if required_fields:
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise BadRequest(f"Missing required fields: {', '.join(missing)}")

    return data


def validate_topic(topic: str) -> str:
    """Validate and sanitize topic input"""
    if not topic or not isinstance(topic, str):
        raise BadRequest("Topic is required and must be a string")

    topic = topic.strip()
    if len(topic) < 1:
        raise BadRequest("Topic cannot be empty")

    if len(topic) > 200:
        raise BadRequest("Topic too long (max 200 characters)")

    # Check for malicious content
    dangerous_chars = ["<", ">", '"', "'", "&", "javascript:", "data:"]
    if any(char in topic.lower() for char in dangerous_chars):
        raise BadRequest("Topic contains invalid characters")

    return topic


def create_success_response(data: dict = None, message: str = "Success") -> dict:
    """Create standardized success response"""
    response = {"success": True, "message": message}
    if data:
        response.update(data)
    return response


def create_error_response(
    message: str, status_code: int = 400, details: dict = None
) -> tuple:
    """Create standardized error response"""
    response = {"success": False, "error": message}
    if details:
        response.update(details)
    return jsonify(response), status_code


# Main web route
@app.route("/")
def index():
    """Serve the main web interface"""
    try:
        db_path = db_manager.db_path
        return render_template("index.html", db_path=db_path)
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return "Error loading page", 500


# API Routes
@app.route("/start_session", methods=["POST"])
def start_session():
    """Start a new study session"""
    try:
        data = validate_json_request(["topic"])
        topic = validate_topic(data["topic"])
        description = data.get("description", "").strip()
        metadata = data.get("metadata", {})

        # Validate session operation
        validation = session_manager.validate_session_operation("start", topic=topic)
        if not validation["valid"]:
            return create_error_response(
                f"Cannot start session: {'; '.join(validation['errors'])}", 400
            )

        # Start session
        session_id = session_manager.start_session(topic, description, metadata)

        # Start activity monitoring
        if not activity_monitor.start_monitoring(session_id):
            logger.warning("Activity monitoring failed to start, continuing without it")

        logger.info(f"Started session: {session_id} with topic: {topic}")
        return jsonify(
            create_success_response(
                {"session_id": session_id}, "Session started successfully"
            )
        )

    except BadRequest as e:
        return create_error_response(str(e), 400)
    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        return create_error_response("Internal server error", 500)


@app.route("/pause_session", methods=["POST"])
def pause_session():
    """Pause or resume current session"""
    try:
        # Check if session exists
        status = session_manager.get_current_status()
        if not status["active"]:
            return create_error_response("No active session to pause/resume", 404)

        # Toggle pause state
        if status["state"] == "active":
            # Pause session
            stats = session_manager.pause_session("manual_pause")
            activity_monitor.pause_monitoring()
            message = "Session paused"
            is_paused = True
        elif status["state"] == "paused":
            # Resume session
            stats = session_manager.resume_session()
            activity_monitor.resume_monitoring()
            message = "Session resumed"
            is_paused = False
        else:
            return create_error_response(
                "Cannot pause/resume session in current state", 400
            )

        return jsonify(
            create_success_response({"paused": is_paused, "stats": stats}, message)
        )

    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error pausing/resuming session: {e}")
        return create_error_response("Internal server error", 500)


@app.route("/stop_session", methods=["POST"])
def stop_session():
    """End current session and save to database"""
    try:
        # Handle both JSON and empty request
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = {}

        success = data.get("success", True)
        completion_notes = data.get("completion_notes", "").strip()

        # Check if session exists
        status = session_manager.get_current_status()
        if not status["active"]:
            return create_error_response("No active session to stop", 404)

        # Stop session
        session_summary = session_manager.stop_session(success, completion_notes)

        # Stop activity monitoring
        activity_monitor.stop_monitoring()

        logger.info(f"Stopped session: {session_summary.get('session_id')}")
        return jsonify(
            create_success_response(session_summary, "Session completed successfully")
        )

    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        return create_error_response("Internal server error", 500)


@app.route("/get_status", methods=["GET"])
def get_status():
    """Get real-time session status and activity"""
    try:
        # Get session status from session manager
        session_status = session_manager.get_current_status()

        if not session_status["active"]:
            return jsonify(
                create_success_response(
                    {
                        "total_seconds": 0,
                        "active_seconds": 0,
                        "idle_seconds": 0,
                        "productivity": 0,
                        "currently_active": False,
                        "state": "idle",
                    }
                )
            )

        # Get activity stats if monitoring is active
        activity_stats = activity_monitor.get_current_stats()

        # Combine data
        combined_stats = {
            "total_seconds": activity_stats.get(
                "total_seconds", session_status.get("total_seconds", 0)
            ),
            "active_seconds": activity_stats.get(
                "active_seconds", session_status.get("active_seconds", 0)
            ),
            "idle_seconds": activity_stats.get(
                "idle_seconds", session_status.get("idle_seconds", 0)
            ),
            "productivity": activity_stats.get(
                "productivity", session_status.get("productivity", 0)
            ),
            "currently_active": activity_stats.get("currently_active", False),
            "state": session_status.get("state", "unknown"),
            "intensity": activity_stats.get("intensity", 0.0),
            "current_session": session_status.get("current_session"),
        }

        return jsonify(create_success_response(combined_stats))

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return create_error_response("Internal server error", 500)


@app.route("/get_sessions", methods=["GET"])
def get_sessions():
    """Retrieve session history"""
    try:
        # Parse pagination parameters
        limit = min(request.args.get("limit", 50, type=int), 1000)
        offset = max(request.args.get("offset", 0, type=int), 0)

        # Parse date filters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        # Get sessions from database
        sessions = db_manager.get_sessions(
            limit=limit, offset=offset, date_from=date_from, date_to=date_to
        )

        # Format response
        formatted_sessions = []
        for session in sessions:
            formatted_sessions.append(
                {
                    "id": session["id"],
                    "topic": session["topic"],
                    "description": session.get("description", ""),
                    "date": session["start_time"][:10] if session["start_time"] else "",
                    "start_time": session["start_time"],
                    "end_time": session.get("end_time", ""),
                    "active_minutes": (session.get("active_seconds", 0) or 0) // 60,
                    "idle_minutes": (session.get("idle_seconds", 0) or 0) // 60,
                    "total_minutes": (session.get("total_seconds", 0) or 0) // 60,
                    "productivity": round(session.get("productivity", 0) or 0, 1),
                    "success": session.get("success", True),
                    "completion_notes": session.get("completion_notes", ""),
                    "created_at": session["created_at"],
                }
            )

        return jsonify(
            create_success_response(
                {
                    "sessions": formatted_sessions,
                    "limit": limit,
                    "offset": offset,
                    "total": len(formatted_sessions),
                }
            )
        )

    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return create_error_response("Internal server error", 500)


@app.route("/get_stats", methods=["GET"])
def get_stats():
    """Get aggregated statistics"""
    try:
        stats = db_manager.get_statistics()
        return jsonify(
            create_success_response(stats, "Statistics retrieved successfully")
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return create_error_response("Internal server error", 500)


@app.route("/export_csv", methods=["GET"])
def export_csv():
    """Export sessions as CSV file"""
    try:
        csv_data = db_manager.export_sessions_csv()

        response = Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=study_sessions.csv",
                "Content-Type": "text/csv; charset=utf-8",
            },
        )

        logger.info("Exported sessions to CSV")
        return response

    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return create_error_response("Export failed", 500)


@app.route("/import_csv", methods=["POST"])
def import_csv():
    """Import sessions from CSV file"""
    try:
        if "file" not in request.files:
            return create_error_response("No file provided", 400)

        file = request.files["file"]
        if file.filename == "":
            return create_error_response("No file selected", 400)

        # Validate file
        if not file.filename.lower().endswith(".csv"):
            return create_error_response("File must be a CSV file", 400)

        # Check file size (max 10MB)
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Seek back to beginning

        if size > 10 * 1024 * 1024:
            return create_error_response("File too large (max 10MB)", 413)

        # Read CSV content
        try:
            csv_content = file.read().decode("utf-8")
        except UnicodeDecodeError:
            try:
                # Try with different encoding
                file.seek(0)
                csv_content = file.read().decode("latin-1")
            except:
                return create_error_response("Unable to read file content", 400)

        # Import sessions
        imported_count, errors = db_manager.import_sessions_csv(csv_content)

        message = f"Successfully imported {imported_count} sessions"
        if errors:
            message += f" with {len(errors)} errors"

        logger.info(f"Imported {imported_count} sessions from CSV")

        response_data = {
            "imported_count": imported_count,
            "total_errors": len(errors),
            "errors": errors[:10],  # Limit error details in response
        }

        return jsonify(create_success_response(response_data, message))

    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        return create_error_response("Import failed", 500)


# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        db_health = db_manager.health_check()
        activity_health = activity_monitor.get_health_status()

        overall_status = "healthy"
        if db_health.get("status") != "healthy" or not activity_health.get(
            "permissions_ok", False
        ):
            overall_status = "degraded"

        return jsonify(
            create_success_response(
                {
                    "status": overall_status,
                    "timestamp": datetime.utcnow().isoformat(),
                    "database": db_health,
                    "activity_monitor": activity_health,
                    "version": "1.0.0",
                }
            )
        )

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify(
            {
                "success": False,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        ), 500


# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return create_error_response(
        "Bad request", 400, {"details": str(error.description)}
    )


@app.errorhandler(404)
def not_found(error):
    return create_error_response("Not found", 404)


@app.errorhandler(405)
def method_not_allowed(error):
    return create_error_response("Method not allowed", 405)


@app.errorhandler(413)
def payload_too_large(error):
    return create_error_response("File too large", 413)


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return create_error_response("Internal server error", 500)


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    logger.error(f"Unexpected error: {type(error).__name__}: {error}")
    if config.debug:
        return create_error_response(f"Unexpected error: {error}", 500)
    else:
        return create_error_response("Internal server error", 500)


# Shutdown endpoint for development
@app.route("/shutdown", methods=["POST"])
def shutdown():
    """Shutdown the Flask server (development only)"""
    if not config.debug:
        return create_error_response("Not available in production", 403)

    # Stop activity monitoring
    activity_monitor.stop_monitoring()

    # Shutdown Flask
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()

    return "Server shutting down..."


if __name__ == "__main__":
    logger.info(f"Starting Study Tracker server on {config.host}:{config.port}")
    logger.info(f"Debug mode: {config.debug}")
    logger.info(f"Database: {db_manager.db_path}")

    # Start server
    app.run(host=config.host, port=config.port, debug=config.debug, threaded=True)
