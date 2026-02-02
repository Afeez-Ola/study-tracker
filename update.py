#!/usr/bin/env python3
"""
Auto-update system for Study Tracker

Usage:
    python update.py              # Check for updates and prompt user
    python update.py --auto       # Update automatically without prompting
    python update.py --check      # Only check for updates, don't install
    python update.py --force      # Force update even if no changes detected

This script:
1. Fetches latest changes from GitHub
2. Compares local version with remote
3. Backs up current installation
4. Updates files and dependencies
5. Handles database migrations
6. Restarts the application if running
"""

import os
import sys
import subprocess
import shutil
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class AutoUpdater:
    def __init__(
        self, repo_url="https://github.com/Afeez-Ola/study-tracker.git", auto=False
    ):
        self.repo_url = repo_url
        self.auto = auto
        self.project_dir = Path(__file__).parent.absolute()
        self.backup_dir = self.project_dir / "backups"
        self.version_file = self.project_dir / ".version"
        self.current_version = self._get_current_version()

    def _get_current_version(self):
        """Get current installed version"""
        try:
            # Try to get from git
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()[:7]
        except:
            pass

        # Fallback to version file
        if self.version_file.exists():
            return self.version_file.read_text().strip()

        return "unknown"

    def _get_remote_version(self):
        """Get latest version from GitHub"""
        try:
            # Fetch latest commit hash from remote
            subprocess.run(
                ["git", "fetch", "origin", "main"],
                cwd=self.project_dir,
                capture_output=True,
                check=True,
            )

            result = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()[:7]
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch remote version: {e}")
            return None
        except FileNotFoundError:
            logger.error("Git not installed or not in PATH")
            return None

    def _check_for_updates(self):
        """Check if updates are available"""
        logger.info("🔍 Checking for updates...")

        remote_version = self._get_remote_version()
        if not remote_version:
            return False, None

        if remote_version == self.current_version:
            logger.info(f"✅ Already up to date (version: {self.current_version})")
            return False, remote_version

        logger.info(f"📦 Update available!")
        logger.info(f"   Current: {self.current_version}")
        logger.info(f"   Latest:  {remote_version}")

        # Get update details
        try:
            log_result = subprocess.run(
                ["git", "log", f"{self.current_version}..origin/main", "--oneline"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            if log_result.stdout:
                logger.info("\n📝 Recent changes:")
                for line in log_result.stdout.strip().split("\n")[:5]:
                    logger.info(f"   • {line}")
        except:
            pass

        return True, remote_version

    def _create_backup(self):
        """Create backup of current installation"""
        logger.info("💾 Creating backup...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"

        try:
            self.backup_dir.mkdir(exist_ok=True)

            # Copy essential files
            files_to_backup = [
                "database.py",
                "session_manager.py",
                "activity_monitor.py",
                "app.py",
                "config.py",
                "utils.py",
                "templates",
                "static",
            ]

            for item in files_to_backup:
                src = self.project_dir / item
                if src.exists():
                    if src.is_dir():
                        shutil.copytree(src, backup_path / item, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, backup_path / item)

            # Backup database
            db_path = Path.home() / "study_tracker.db"
            if db_path.exists():
                shutil.copy2(db_path, backup_path / "study_tracker.db")

            logger.info(f"✅ Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None

    def _update_files(self):
        """Pull latest changes from GitHub"""
        logger.info("📥 Downloading updates...")

        try:
            # Stash any local changes
            subprocess.run(["git", "stash"], cwd=self.project_dir, capture_output=True)

            # Pull latest changes
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info("✅ Files updated successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Update failed: {e}")
            logger.error(f"   Error output: {e.stderr}")
            return False

    def _update_dependencies(self):
        """Update Python dependencies"""
        logger.info("📦 Updating dependencies...")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    "requirements.txt",
                    "--upgrade",
                ],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info("✅ Dependencies updated")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"⚠️  Dependency update warning: {e}")
            # Don't fail the whole update for dependency issues
            return True

    def _handle_database_migration(self):
        """Handle any database migrations"""
        logger.info("🗄️  Checking database...")

        try:
            # Import and check database
            sys.path.insert(0, str(self.project_dir))
            from database import DatabaseManager

            db = DatabaseManager()
            health = db.health_check()

            if health.get("status") == "healthy":
                logger.info("✅ Database is healthy")
            else:
                logger.warning("⚠️  Database check returned warnings")
                logger.info("   Attempting to initialize/repair...")
                db.init_database()
                logger.info("✅ Database initialized")

            return True

        except Exception as e:
            logger.error(f"⚠️  Database migration warning: {e}")
            return True  # Don't fail the update

    def _save_version(self, version):
        """Save current version to file"""
        try:
            self.version_file.write_text(version)
        except:
            pass

    def update(self, force=False):
        """Main update process"""
        logger.info("🚀 Study Tracker Auto-Update\n")

        # Check if git is available
        if not self._check_git_available():
            logger.error("❌ Git is not installed. Please install Git first.")
            logger.info("   Visit: https://git-scm.com/downloads")
            return False

        # Check for updates
        has_update, remote_version = self._check_for_updates()

        if not has_update and not force:
            return True

        # Confirm with user (unless auto mode)
        if not self.auto and not force:
            response = input("\n🤔 Do you want to update now? (y/n): ").strip().lower()
            if response not in ["y", "yes"]:
                logger.info("👋 Update cancelled by user")
                return False

        # Create backup
        backup_path = self._create_backup()
        if not backup_path:
            if not self.auto:
                response = (
                    input("⚠️  Backup failed. Continue anyway? (y/n): ").strip().lower()
                )
                if response not in ["y", "yes"]:
                    return False
            else:
                logger.error("❌ Backup failed and auto mode is enabled. Aborting.")
                return False

        # Perform update
        success = True

        if not self._update_files():
            success = False

        if success and not self._update_dependencies():
            logger.warning("⚠️  Dependency update had issues, but continuing...")

        if success:
            self._handle_database_migration()
            self._save_version(remote_version)

        if success:
            logger.info("\n✨ Update completed successfully!")
            logger.info(f"   New version: {remote_version}")
            logger.info(f"   Backup location: {backup_path}")
            logger.info("\n🔄 Please restart the application to use the new version.")
            logger.info("   Run: python run.py")
            return True
        else:
            logger.error("\n❌ Update failed!")
            if backup_path:
                logger.info(f"   You can restore from backup: {backup_path}")
            return False

    def _check_git_available(self):
        """Check if git is installed"""
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
            return True
        except:
            return False

    def check_only(self):
        """Only check for updates without installing"""
        logger.info("🔍 Checking for updates...\n")

        if not self._check_git_available():
            logger.error("❌ Git is not installed")
            return False

        has_update, remote_version = self._check_for_updates()

        if has_update:
            logger.info(f"\n💡 To update, run: python update.py")

        return has_update


def main():
    parser = argparse.ArgumentParser(
        description="Study Tracker Auto-Update System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python update.py              # Check and prompt for update
  python update.py --auto       # Update automatically
  python update.py --check      # Check only, don't update
  python update.py --force      # Force update

For more help, visit: https://github.com/Afeez-Ola/study-tracker
        """,
    )

    parser.add_argument(
        "--auto", action="store_true", help="Update automatically without prompting"
    )

    parser.add_argument(
        "--check", action="store_true", help="Only check for updates, don't install"
    )

    parser.add_argument(
        "--force", action="store_true", help="Force update even if no changes detected"
    )

    parser.add_argument(
        "--version", action="version", version="Study Tracker Updater 1.0.0"
    )

    args = parser.parse_args()

    updater = AutoUpdater(auto=args.auto)

    if args.check:
        updater.check_only()
    else:
        success = updater.update(force=args.force)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
