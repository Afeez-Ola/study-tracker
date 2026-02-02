"""
Study Buddy System - Location-based user discovery and collaboration

Helps users find nearby study partners based on location and study compatibility.
"""

import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from database import DatabaseManager

logger = logging.getLogger(__name__)


class StudyBuddySystem:
    """Manage study buddy discovery, requests, and compatibility"""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()

    def update_user_location(
        self,
        user_id: str,
        lat: float,
        lon: float,
        city: str = None,
        country: str = None,
    ) -> bool:
        """Update user's location for nearby discovery"""
        try:
            return self.db_manager.update_user_profile(
                user_id,
                {
                    "location_lat": lat,
                    "location_lon": lon,
                    "location_city": city,
                    "location_country": country,
                },
            )
        except Exception as e:
            logger.error(f"Error updating location: {e}")
            return False

    def find_nearby_users(
        self,
        user_id: str,
        radius_km: float = 10.0,
        limit: int = 20,
        min_compatibility: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Find nearby users with study compatibility scores

        Args:
            user_id: Current user's ID
            radius_km: Search radius in kilometers
            limit: Maximum results
            min_compatibility: Minimum compatibility score (0-100)

        Returns:
            List of nearby users with compatibility info
        """
        try:
            # Get current user
            current_user = self.db_manager.get_user_by_id(user_id)
            if not current_user:
                logger.error(f"User not found: {user_id}")
                return []

            # Check if user has location set
            if not current_user.get("location_lat") or not current_user.get(
                "location_lon"
            ):
                logger.warning(f"User {user_id} has no location set")
                return []

            # Get current user's study preferences
            current_prefs = self._get_user_study_preferences(user_id)

            # Find nearby users from database
            nearby_users = self.db_manager.find_users_nearby(
                lat=current_user["location_lat"],
                lon=current_user["location_lon"],
                radius_km=radius_km,
                exclude_user_id=user_id,
                limit=limit * 2,  # Get more to filter by compatibility
            )

            # Calculate compatibility and filter
            results = []
            for user in nearby_users:
                # Get user's study preferences
                user_prefs = self._get_user_study_preferences(user["id"])

                # Calculate compatibility
                compatibility = self._calculate_compatibility(current_prefs, user_prefs)

                if compatibility["score"] >= min_compatibility:
                    # Check if already buddies
                    existing_status = self._get_buddy_status(user_id, user["id"])

                    results.append(
                        {
                            "user_id": user["id"],
                            "username": user.get("username"),
                            "full_name": user.get("full_name"),
                            "bio": user.get("bio"),
                            "avatar_url": user.get("avatar_url"),
                            "location_city": user.get("location_city"),
                            "location_country": user.get("location_country"),
                            "distance_km": round(user.get("distance", 0), 1),
                            "study_streak": user.get("study_streak", 0),
                            "total_study_minutes": user.get("total_study_minutes", 0),
                            "compatibility": compatibility,
                            "buddy_status": existing_status,
                            "common_subjects": compatibility["common_subjects"],
                            "study_time_overlap": compatibility["time_overlap"],
                        }
                    )

            # Sort by compatibility score (highest first)
            results.sort(key=lambda x: x["compatibility"]["score"], reverse=True)

            return results[:limit]

        except Exception as e:
            logger.error(f"Error finding nearby users: {e}")
            return []

    def _get_user_study_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's study preferences from sessions and materials"""
        try:
            # Get recent study sessions to determine subjects
            sessions = self.db_manager.get_sessions(limit=50)
            user_sessions = [s for s in sessions if s.get("user_id") == user_id]

            # Extract subjects from session topics
            subjects = set()
            for session in user_sessions:
                topic = session.get("topic", "").lower()
                # Simple keyword extraction (in production, use NLP)
                keywords = [
                    "math",
                    "physics",
                    "chemistry",
                    "biology",
                    "programming",
                    "history",
                    "english",
                    "economics",
                    "medicine",
                    "law",
                    "engineering",
                    "design",
                    "art",
                    "music",
                    "language",
                ]
                for keyword in keywords:
                    if keyword in topic:
                        subjects.add(keyword)

            # Get study materials subjects
            materials = self.db_manager.get_materials_by_user(user_id, limit=20)
            for material in materials:
                tags = material.get("subject_tags", "").split(",")
                subjects.update([t.strip().lower() for t in tags if t.strip()])

            # Calculate study patterns
            study_times = []
            total_sessions = len(user_sessions)
            total_minutes = sum(s.get("active_minutes", 0) or 0 for s in user_sessions)

            for session in user_sessions:
                if session.get("start_time"):
                    try:
                        hour = datetime.fromisoformat(
                            session["start_time"].replace("Z", "+00:00")
                        ).hour
                        study_times.append(hour)
                    except:
                        pass

            # Determine preferred study times
            preferred_times = []
            if study_times:
                avg_hour = sum(study_times) / len(study_times)
                if 5 <= avg_hour < 12:
                    preferred_times.append("morning")
                elif 12 <= avg_hour < 17:
                    preferred_times.append("afternoon")
                elif 17 <= avg_hour < 22:
                    preferred_times.append("evening")
                else:
                    preferred_times.append("night")

            # Calculate productivity level
            avg_productivity = 0
            if user_sessions:
                avg_productivity = sum(
                    s.get("productivity", 0) or 0 for s in user_sessions
                ) / len(user_sessions)

            return {
                "subjects": list(subjects),
                "total_sessions": total_sessions,
                "total_minutes": total_minutes,
                "preferred_times": preferred_times,
                "avg_productivity": avg_productivity,
                "study_times": study_times,
            }

        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {
                "subjects": [],
                "total_sessions": 0,
                "total_minutes": 0,
                "preferred_times": [],
                "avg_productivity": 0,
                "study_times": [],
            }

    def _calculate_compatibility(
        self, prefs1: Dict[str, Any], prefs2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate study compatibility between two users

        Returns score 0-100 with breakdown
        """
        scores = {}

        # 1. Common subjects (40% weight)
        subjects1 = set(prefs1.get("subjects", []))
        subjects2 = set(prefs2.get("subjects", []))
        common_subjects = subjects1 & subjects2
        total_subjects = subjects1 | subjects2

        if total_subjects:
            subject_score = (len(common_subjects) / len(total_subjects)) * 40
        else:
            subject_score = 0

        scores["subjects"] = round(subject_score, 1)

        # 2. Study time overlap (30% weight)
        times1 = set(prefs1.get("preferred_times", []))
        times2 = set(prefs2.get("preferred_times", []))
        common_times = times1 & times2

        if times1 and times2:
            time_score = (len(common_times) / max(len(times1), len(times2))) * 30
        else:
            time_score = 15  # Neutral if no data

        scores["time"] = round(time_score, 1)

        # 3. Study intensity similarity (20% weight)
        sessions1 = prefs1.get("total_sessions", 0)
        sessions2 = prefs2.get("total_sessions", 0)

        if sessions1 > 0 and sessions2 > 0:
            # Compare study frequency
            ratio = min(sessions1, sessions2) / max(sessions1, sessions2)
            intensity_score = ratio * 20
        else:
            intensity_score = 10  # Neutral if no data

        scores["intensity"] = round(intensity_score, 1)

        # 4. Productivity compatibility (10% weight)
        prod1 = prefs1.get("avg_productivity", 0)
        prod2 = prefs2.get("avg_productivity", 0)

        if prod1 > 0 and prod2 > 0:
            # Closer productivity = better compatibility
            diff = abs(prod1 - prod2)
            productivity_score = max(0, 10 - (diff / 10))  # Max 10 points
        else:
            productivity_score = 5  # Neutral

        scores["productivity"] = round(productivity_score, 1)

        # Total score
        total_score = sum(scores.values())

        return {
            "score": round(total_score, 1),
            "breakdown": scores,
            "common_subjects": list(common_subjects),
            "time_overlap": list(common_times),
            "level": self._get_compatibility_level(total_score),
        }

    def _get_compatibility_level(self, score: float) -> str:
        """Get compatibility level description"""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Moderate"
        elif score >= 20:
            return "Low"
        else:
            return "Poor"

    def _get_buddy_status(self, user1_id: str, user2_id: str) -> str:
        """Check existing buddy relationship status"""
        try:
            buddy_record = self.db_manager.get_study_buddy_record(user1_id, user2_id)
            if buddy_record:
                return buddy_record["status"]
            return "none"
        except:
            return "none"

    def send_buddy_request(
        self, requester_id: str, recipient_id: str, message: str = ""
    ) -> Dict[str, Any]:
        """Send a study buddy request"""
        try:
            # Check if already buddies or has pending request
            existing = self.db_manager.get_study_buddy_record(
                requester_id, recipient_id
            )
            if existing:
                return {
                    "success": False,
                    "error": f"Already have a {existing['status']} request with this user",
                }

            # Calculate compatibility for the request
            prefs1 = self._get_user_study_preferences(requester_id)
            prefs2 = self._get_user_study_preferences(recipient_id)
            compatibility = self._calculate_compatibility(prefs1, prefs2)

            # Create buddy request
            if self.db_manager.create_study_buddy_request(
                requester_id, recipient_id, message, compatibility["score"]
            ):
                return {
                    "success": True,
                    "message": "Buddy request sent",
                    "compatibility": compatibility,
                }
            else:
                return {"success": False, "error": "Failed to send request"}

        except Exception as e:
            logger.error(f"Error sending buddy request: {e}")
            return {"success": False, "error": "Request failed"}

    def respond_to_buddy_request(
        self, user_id: str, requester_id: str, accept: bool
    ) -> bool:
        """Accept or reject a buddy request"""
        try:
            status = "accepted" if accept else "rejected"
            return self.db_manager.update_study_buddy_status(
                requester_id, user_id, status
            )
        except Exception as e:
            logger.error(f"Error responding to buddy request: {e}")
            return False

    def get_buddy_requests(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending buddy requests for a user"""
        try:
            return self.db_manager.get_pending_buddy_requests(user_id)
        except Exception as e:
            logger.error(f"Error getting buddy requests: {e}")
            return []

    def get_my_buddies(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of confirmed study buddies"""
        try:
            buddies = self.db_manager.get_accepted_buddies(user_id)

            # Enrich with additional info
            for buddy in buddies:
                buddy_user = self.db_manager.get_user_by_id(buddy["buddy_id"])
                if buddy_user:
                    buddy["username"] = buddy_user.get("username")
                    buddy["full_name"] = buddy_user.get("full_name")
                    buddy["bio"] = buddy_user.get("bio")
                    buddy["avatar_url"] = buddy_user.get("avatar_url")
                    buddy["study_streak"] = buddy_user.get("study_streak", 0)

            return buddies
        except Exception as e:
            logger.error(f"Error getting buddies: {e}")
            return []

    def remove_buddy(self, user_id: str, buddy_id: str) -> bool:
        """Remove a study buddy"""
        try:
            return self.db_manager.delete_study_buddy_relationship(user_id, buddy_id)
        except Exception as e:
            logger.error(f"Error removing buddy: {e}")
            return False

    def block_user(self, user_id: str, blocked_id: str) -> bool:
        """Block a user from sending requests"""
        try:
            return self.db_manager.block_study_buddy(user_id, blocked_id)
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            return False


# Haversine formula for distance calculation
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in kilometers
    r = 6371

    return c * r


# Helper function
def get_study_buddy_system():
    """Get study buddy system instance"""
    return StudyBuddySystem()
