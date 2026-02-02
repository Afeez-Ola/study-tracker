#!/usr/bin/env python3
"""
Update Notifier for Study Tracker

This module checks for updates and notifies users when new versions are available.
Can be integrated into the Flask app to show update notifications in the UI.
"""

import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path


class UpdateNotifier:
    def __init__(self, check_interval_hours=24):
        self.check_interval = timedelta(hours=check_interval_hours)
        self.last_check_file = Path(__file__).parent / ".last_update_check"
        self.project_dir = Path(__file__).parent.absolute()

    def should_check(self):
        """Check if it's time to check for updates"""
        if not self.last_check_file.exists():
            return True

        try:
            last_check = datetime.fromisoformat(
                self.last_check_file.read_text().strip()
            )
            return datetime.now() - last_check > self.check_interval
        except:
            return True

    def mark_checked(self):
        """Mark that we've checked for updates"""
        self.last_check_file.write_text(datetime.now().isoformat())

    def check_for_updates(self):
        """Check if updates are available"""
        try:
            # Fetch from remote
            subprocess.run(
                ["git", "fetch", "origin", "main"],
                cwd=self.project_dir,
                capture_output=True,
                check=True,
                timeout=10,
            )

            # Get current and remote versions
            current = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()[:7]

            remote = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()[:7]

            self.mark_checked()

            if current != remote:
                # Get changelog
                try:
                    log = subprocess.run(
                        ["git", "log", f"{current}..{remote}", "--oneline"],
                        cwd=self.project_dir,
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout.strip()

                    return {
                        "has_update": True,
                        "current_version": current,
                        "latest_version": remote,
                        "changelog": log.split("\n")[:3] if log else [],
                        "update_command": "python update.py",
                    }
                except:
                    return {
                        "has_update": True,
                        "current_version": current,
                        "latest_version": remote,
                        "changelog": [],
                        "update_command": "python update.py",
                    }

            return {"has_update": False}

        except subprocess.CalledProcessError:
            return {"has_update": False, "error": "Failed to check updates"}
        except FileNotFoundError:
            return {"has_update": False, "error": "Git not available"}
        except subprocess.TimeoutExpired:
            return {"has_update": False, "error": "Check timed out"}

    def get_update_info(self):
        """Get update info (with caching)"""
        if self.should_check():
            return self.check_for_updates()

        # Return cached result
        return {"has_update": False, "cached": True}


# Flask integration function
def get_update_status():
    """Get update status for Flask app"""
    notifier = UpdateNotifier()
    return notifier.get_update_info()


if __name__ == "__main__":
    notifier = UpdateNotifier()
    result = notifier.check_for_updates()
    print(json.dumps(result, indent=2))
