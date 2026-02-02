#!/usr/bin/env python3
"""
Production runner for Study Tracker
Run with: python run.py
"""

import os
import sys
import logging
from app import app, db_manager, activity_monitor


def setup_production_logging():
    """Setup production logging"""
    log_dir = os.path.expanduser("~/study_tracker_logs")
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "study_tracker.log")),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main():
    """Main production runner"""
    try:
        setup_production_logging()
        logger = logging.getLogger(__name__)

        # Print startup info
        logger.info("=== Study Tracker Production Server ===")
        logger.info(f"Database: {db_manager.db_path}")
        logger.info(f"Platform: {activity_monitor.platform}")
        logger.info(f"Permissions OK: {activity_monitor.permissions_ok}")

        # Check database health
        health = db_manager.health_check()
        if health["status"] != "healthy":
            logger.error(f"Database health check failed: {health}")
            sys.exit(1)

        logger.info("Database health: OK")

        # Set production environment
        os.environ["FLASK_ENV"] = "production"

        # Get configuration from environment
        host = os.getenv("FLASK_HOST", "127.0.0.1")
        port = int(os.getenv("FLASK_PORT", 5000))

        logger.info(f"Starting production server on {host}:{port}")

        # Start Flask server
        app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")

        # Stop activity monitoring
        try:
            activity_monitor.stop_monitoring()
        except:
            pass

        logger.info("Server stopped")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
