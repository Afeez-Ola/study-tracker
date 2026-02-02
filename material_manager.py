"""
Study Material Management System for Study Tracker

Handles file uploads, storage, metadata, search, and downloads.
"""

import os
import uuid
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from database import DatabaseManager

logger = logging.getLogger(__name__)

# File upload configuration
UPLOAD_FOLDER = Path(__file__).parent / "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".md",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
}


def ensure_upload_folder():
    """Ensure upload folder exists"""
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    # Create subfolders for organization
    for ext in ALLOWED_EXTENSIONS:
        (UPLOAD_FOLDER / ext[1:]).mkdir(exist_ok=True)


class MaterialManager:
    """Manage study materials (upload, download, search)"""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        ensure_upload_folder()

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        ext = Path(filename).suffix.lower()
        return ext in ALLOWED_EXTENSIONS

    def save_material(
        self,
        user_id: str,
        file: FileStorage,
        title: str,
        description: str = "",
        subject_tags: List[str] = None,
        is_public: bool = True,
    ) -> Dict[str, Any]:
        """
        Save uploaded study material

        Returns:
            Dict with material_id, file_path, and status
        """
        try:
            # Validate file
            if not file or not file.filename:
                return {"success": False, "error": "No file provided"}

            if not self.allowed_file(file.filename):
                allowed = ", ".join(ALLOWED_EXTENSIONS)
                return {
                    "success": False,
                    "error": f"File type not allowed. Allowed: {allowed}",
                }

            # Check file size
            file.seek(0, 2)  # Seek to end
            size = file.tell()
            file.seek(0)  # Reset to beginning

            if size > MAX_FILE_SIZE:
                max_mb = MAX_FILE_SIZE / (1024 * 1024)
                return {
                    "success": False,
                    "error": f"File too large. Max size: {max_mb}MB",
                }

            # Generate unique ID and filename
            material_id = str(uuid.uuid4())
            ext = Path(file.filename).suffix.lower()
            safe_filename = secure_filename(f"{material_id}{ext}")

            # Save file to disk
            subfolder = UPLOAD_FOLDER / ext[1:]
            file_path = subfolder / safe_filename
            file.save(file_path)

            # Save metadata to database
            tags_str = ",".join(subject_tags) if subject_tags else ""

            if self.db_manager.save_material(
                material_id=material_id,
                user_id=user_id,
                title=title,
                description=description,
                file_type=ext,
                file_size=size,
                file_path=str(file_path),
                subject_tags=tags_str,
                is_public=is_public,
            ):
                logger.info(f"Material saved: {material_id} by user {user_id}")

                return {
                    "success": True,
                    "material_id": material_id,
                    "title": title,
                    "file_type": ext,
                    "file_size": size,
                    "file_size_formatted": self._format_file_size(size),
                    "message": "Material uploaded successfully",
                }
            else:
                # Clean up file if DB save failed
                if file_path.exists():
                    file_path.unlink()
                return {"success": False, "error": "Failed to save material metadata"}

        except Exception as e:
            logger.error(f"Error saving material: {e}")
            return {"success": False, "error": "Upload failed"}

    def get_material(
        self, material_id: str, user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get material metadata and check access permissions"""
        try:
            material = self.db_manager.get_material_by_id(material_id)
            if not material:
                return None

            # Check permissions
            is_owner = material["user_id"] == user_id
            is_public = material.get("is_public", True)

            if not is_public and not is_owner:
                return None  # Private material, not owner

            # Increment download count
            self.db_manager.increment_download_count(material_id)

            # Add extra info
            material["is_owner"] = is_owner
            material["file_size_formatted"] = self._format_file_size(
                material["file_size"]
            )
            material["average_rating"] = self._calculate_average_rating(material)

            return material

        except Exception as e:
            logger.error(f"Error getting material: {e}")
            return None

    def search_materials(
        self,
        query: str = None,
        subject: str = None,
        tags: List[str] = None,
        user_id: str = None,
        only_public: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search for study materials"""
        try:
            materials = self.db_manager.search_materials(
                query=query,
                subject=subject,
                tags=tags,
                user_id=user_id if not only_public else None,
                only_public=only_public,
                limit=limit,
                offset=offset,
            )

            # Enrich with additional info
            for material in materials:
                material["file_size_formatted"] = self._format_file_size(
                    material["file_size"]
                )
                material["average_rating"] = self._calculate_average_rating(material)
                material["uploader_name"] = self._get_uploader_name(material["user_id"])

            return materials

        except Exception as e:
            logger.error(f"Error searching materials: {e}")
            return []

    def get_user_materials(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all materials uploaded by a user"""
        try:
            return self.db_manager.get_materials_by_user(user_id, limit, offset)
        except Exception as e:
            logger.error(f"Error getting user materials: {e}")
            return []

    def delete_material(self, material_id: str, user_id: str) -> bool:
        """Delete a material (only owner can delete)"""
        try:
            # Get material first to check ownership
            material = self.db_manager.get_material_by_id(material_id)
            if not material:
                return False

            if material["user_id"] != user_id:
                return False  # Not owner

            # Delete file from disk
            file_path = Path(material["file_path"])
            if file_path.exists():
                file_path.unlink()

            # Delete from database
            return self.db_manager.delete_material(material_id)

        except Exception as e:
            logger.error(f"Error deleting material: {e}")
            return False

    def rate_material(
        self, material_id: str, user_id: str, rating: int, comment: str = ""
    ) -> bool:
        """Rate a study material (1-5 stars)"""
        try:
            if rating < 1 or rating > 5:
                return False

            # Check if user already rated
            existing = self.db_manager.get_user_rating(material_id, user_id)

            if existing:
                # Update existing rating
                return self.db_manager.update_rating(existing["id"], rating, comment)
            else:
                # Create new rating
                return self.db_manager.create_rating(
                    material_id, user_id, rating, comment
                )

        except Exception as e:
            logger.error(f"Error rating material: {e}")
            return False

    def get_material_ratings(
        self, material_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get ratings for a material"""
        try:
            return self.db_manager.get_material_ratings(material_id, limit)
        except Exception as e:
            logger.error(f"Error getting ratings: {e}")
            return []

    def get_popular_tags(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most popular subject tags"""
        try:
            return self.db_manager.get_popular_tags(limit)
        except Exception as e:
            logger.error(f"Error getting popular tags: {e}")
            return []

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _calculate_average_rating(self, material: Dict) -> float:
        """Calculate average rating from material data"""
        rating_sum = material.get("rating_sum", 0)
        rating_count = material.get("rating_count", 0)

        if rating_count == 0:
            return 0.0

        return round(rating_sum / rating_count, 1)

    def _get_uploader_name(self, user_id: str) -> str:
        """Get uploader's display name"""
        try:
            user = self.db_manager.get_user_by_id(user_id)
            if user:
                return user.get("username") or user.get("full_name") or "Anonymous"
            return "Anonymous"
        except:
            return "Anonymous"

    def cleanup_old_files(self, days: int = 30) -> int:
        """Clean up files that have been deleted from database"""
        try:
            deleted_count = 0
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get all valid file paths from database
            valid_paths = set(self.db_manager.get_all_material_file_paths())

            # Check all files in upload folder
            for ext_folder in UPLOAD_FOLDER.iterdir():
                if ext_folder.is_dir():
                    for file_path in ext_folder.iterdir():
                        if file_path.is_file():
                            # Check if file is in database
                            if str(file_path) not in valid_paths:
                                # Check file age
                                if (
                                    datetime.fromtimestamp(file_path.stat().st_mtime)
                                    < cutoff_date
                                ):
                                    file_path.unlink()
                                    deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} orphaned files")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")
            return 0


# Convenience function
def get_material_manager():
    """Get material manager instance"""
    return MaterialManager()
