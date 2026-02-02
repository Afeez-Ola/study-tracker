"""
GitHub-style contribution map (heatmap) generator for Study Tracker

Generates a 365-day activity heatmap similar to GitHub's contribution graph.
Shows study activity intensity with color-coded cells.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from database import DatabaseManager

logger = logging.getLogger(__name__)


class ContributionMap:
    """Generate GitHub-style contribution heatmaps for study activity"""

    # Color levels (matching GitHub's green theme)
    COLOR_LEVELS = {
        0: "#ebedf0",  # No activity (light gray)
        1: "#9be9a8",  # Light activity
        2: "#40c463",  # Moderate activity
        3: "#30a14e",  # High activity
        4: "#216e39",  # Very high activity
    }

    # Activity thresholds (in minutes)
    LEVEL_THRESHOLDS = {
        1: 30,  # 30+ minutes = Level 1
        2: 60,  # 60+ minutes = Level 2
        3: 120,  # 2+ hours = Level 3
        4: 240,  # 4+ hours = Level 4
    }

    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()

    def generate_heatmap_data(
        self, user_id: str = None, days: int = 365, end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Generate heatmap data for the last N days

        Args:
            user_id: Filter by user (None for all sessions)
            days: Number of days to include (default 365)
            end_date: End date for the range (default today)

        Returns:
            Dict with heatmap data, statistics, and metadata
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - timedelta(days=days - 1)

        # Get sessions from database
        sessions = self._get_sessions_in_range(user_id, start_date, end_date)

        # Aggregate by date
        daily_minutes = self._aggregate_by_date(sessions)

        # Generate heatmap grid
        heatmap_grid = self._generate_grid(start_date, end_date, daily_minutes)

        # Calculate statistics
        stats = self._calculate_statistics(daily_minutes)

        # Calculate streaks
        streaks = self._calculate_streaks(daily_minutes, end_date)

        return {
            "heatmap": heatmap_grid,
            "statistics": stats,
            "streaks": streaks,
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "days": days,
            },
            "color_levels": self.COLOR_LEVELS,
            "thresholds": self.LEVEL_THRESHOLDS,
        }

    def _get_sessions_in_range(
        self, user_id: str, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get study sessions within date range"""
        try:
            date_from = start_date.strftime("%Y-%m-%d")
            date_to = end_date.strftime("%Y-%m-%d")

            # Get sessions from database
            sessions = self.db_manager.get_sessions(
                limit=10000,  # High limit to get all sessions
                date_from=date_from,
                date_to=date_to,
            )

            # Filter by user if specified
            if user_id:
                sessions = [s for s in sessions if s.get("user_id") == user_id]

            return sessions

        except Exception as e:
            logger.error(f"Error fetching sessions for heatmap: {e}")
            return []

    def _aggregate_by_date(self, sessions: List[Dict]) -> Dict[str, int]:
        """Aggregate study minutes by date"""
        daily_minutes = defaultdict(int)

        for session in sessions:
            # Get date from session
            date_str = session.get("date") or session.get("start_time", "")[:10]

            if not date_str:
                continue

            # Get minutes studied
            active_minutes = session.get("active_minutes", 0) or 0
            total_minutes = session.get("total_minutes", 0) or active_minutes

            # Add to daily total
            daily_minutes[date_str] += total_minutes

        return dict(daily_minutes)

    def _generate_grid(
        self, start_date: datetime, end_date: datetime, daily_minutes: Dict[str, int]
    ) -> List[Dict]:
        """Generate heatmap grid data"""
        grid = []
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            minutes = daily_minutes.get(date_str, 0)
            level = self._get_activity_level(minutes)

            grid.append(
                {
                    "date": date_str,
                    "minutes": minutes,
                    "level": level,
                    "color": self.COLOR_LEVELS[level],
                    "weekday": current_date.weekday(),  # 0=Monday, 6=Sunday
                    "week": self._get_week_number(current_date),
                }
            )

            current_date += timedelta(days=1)

        return grid

    def _get_activity_level(self, minutes: int) -> int:
        """Determine activity level based on minutes studied"""
        if minutes == 0:
            return 0
        elif minutes >= self.LEVEL_THRESHOLDS[4]:
            return 4
        elif minutes >= self.LEVEL_THRESHOLDS[3]:
            return 3
        elif minutes >= self.LEVEL_THRESHOLDS[2]:
            return 2
        elif minutes >= self.LEVEL_THRESHOLDS[1]:
            return 1
        else:
            return 1  # Any activity counts as level 1

    def _get_week_number(self, date: datetime) -> int:
        """Get week number for grid positioning"""
        # Return ISO week number
        return date.isocalendar()[1]

    def _calculate_statistics(self, daily_minutes: Dict[str, int]) -> Dict[str, Any]:
        """Calculate overall statistics"""
        if not daily_minutes:
            return {
                "total_days": 0,
                "active_days": 0,
                "total_minutes": 0,
                "total_hours": 0,
                "average_minutes_per_day": 0,
                "average_minutes_per_active_day": 0,
                "max_minutes_in_day": 0,
                "longest_session_minutes": 0,
            }

        total_days = len(daily_minutes)
        active_days = sum(1 for minutes in daily_minutes.values() if minutes > 0)
        total_minutes = sum(daily_minutes.values())
        total_hours = round(total_minutes / 60, 1)

        avg_per_day = round(total_minutes / total_days, 1) if total_days > 0 else 0
        avg_per_active_day = (
            round(total_minutes / active_days, 1) if active_days > 0 else 0
        )

        max_minutes = max(daily_minutes.values()) if daily_minutes else 0

        return {
            "total_days": total_days,
            "active_days": active_days,
            "inactive_days": total_days - active_days,
            "total_minutes": total_minutes,
            "total_hours": total_hours,
            "average_minutes_per_day": avg_per_day,
            "average_minutes_per_active_day": avg_per_active_day,
            "max_minutes_in_day": max_minutes,
            "max_hours_in_day": round(max_minutes / 60, 1),
            "activity_rate": round((active_days / total_days) * 100, 1)
            if total_days > 0
            else 0,
        }

    def _calculate_streaks(
        self, daily_minutes: Dict[str, int], end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate current and longest streaks"""
        if not daily_minutes:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "current_streak_start": None,
                "longest_streak_start": None,
                "longest_streak_end": None,
            }

        # Sort dates
        sorted_dates = sorted(daily_minutes.keys(), reverse=True)

        # Calculate current streak
        current_streak = 0
        current_date = end_date

        while True:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in daily_minutes and daily_minutes[date_str] > 0:
                current_streak += 1
                current_date -= timedelta(days=1)
            else:
                break

        # Calculate longest streak
        longest_streak = 0
        longest_start = None
        longest_end = None

        current_streak_count = 0
        current_streak_start = None

        # Sort dates chronologically for longest streak calculation
        sorted_dates_asc = sorted(daily_minutes.keys())

        for i, date_str in enumerate(sorted_dates_asc):
            if daily_minutes[date_str] > 0:
                if current_streak_count == 0:
                    current_streak_start = date_str
                current_streak_count += 1

                if current_streak_count > longest_streak:
                    longest_streak = current_streak_count
                    longest_start = current_streak_start
                    longest_end = date_str
            else:
                current_streak_count = 0
                current_streak_start = None

        # Get current streak start date
        current_streak_start = None
        if current_streak > 0:
            current_streak_start = (
                end_date - timedelta(days=current_streak - 1)
            ).strftime("%Y-%m-%d")

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "current_streak_start": current_streak_start,
            "longest_streak_start": longest_start,
            "longest_streak_end": longest_end,
        }

    def get_month_labels(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get month labels for heatmap header"""
        labels = []
        current_date = start_date

        while current_date <= end_date:
            # Add month label at the start of each month
            if current_date.day <= 7:  # First week of month
                labels.append(
                    {
                        "month": current_date.strftime("%b"),  # Short month name
                        "date": current_date.strftime("%Y-%m-%d"),
                        "week": self._get_week_number(current_date),
                    }
                )

            current_date += timedelta(days=1)

        return labels

    def export_svg(
        self,
        user_id: str = None,
        days: int = 365,
        cell_size: int = 11,
        cell_padding: int = 2,
    ) -> str:
        """
        Generate SVG representation of heatmap for sharing

        Returns:
            SVG string that can be saved as .svg file or embedded
        """
        data = self.generate_heatmap_data(user_id, days)
        heatmap = data["heatmap"]
        stats = data["statistics"]

        if not heatmap:
            return ""

        # Calculate dimensions
        weeks = (days + 6) // 7  # Round up to full weeks
        width = weeks * (cell_size + cell_padding) + 50  # Extra space for labels
        height = 7 * (cell_size + cell_padding) + 100  # Extra space for header/stats

        # Build SVG
        svg_parts = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'<rect width="100%" height="100%" fill="white"/>',
            f'<text x="20" y="30" font-family="Arial" font-size="16" font-weight="bold">Study Activity</text>',
            f'<text x="20" y="50" font-family="Arial" font-size="12" fill="#666">{stats["active_days"]} days studied · {stats["total_hours"]} hours</text>',
        ]

        # Add heatmap cells
        for cell in heatmap:
            week = cell["week"]
            weekday = cell["weekday"]
            color = cell["color"]

            x = 30 + week * (cell_size + cell_padding)
            y = 70 + weekday * (cell_size + cell_padding)

            # Add tooltip title
            date_label = datetime.strptime(cell["date"], "%Y-%m-%d").strftime(
                "%b %d, %Y"
            )
            minutes_label = (
                f"{cell['minutes']} min" if cell["minutes"] > 0 else "No activity"
            )

            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
                f'fill="{color}" rx="2">'
                f"<title>{date_label}: {minutes_label}</title>"
                f"</rect>"
            )

        # Add legend
        legend_y = height - 30
        svg_parts.append(
            f'<text x="20" y="{legend_y}" font-family="Arial" font-size="10" fill="#666">Less</text>'
        )

        for i, (level, color) in enumerate(self.COLOR_LEVELS.items()):
            x = 60 + i * (cell_size + cell_padding)
            svg_parts.append(
                f'<rect x="{x}" y="{legend_y - 8}" width="{cell_size}" height="{cell_size}" '
                f'fill="{color}" rx="2"/>'
            )

        svg_parts.append(
            f'<text x="{x + 20}" y="{legend_y}" font-family="Arial" font-size="10" fill="#666">More</text>'
        )

        svg_parts.append("</svg>")

        return "\n".join(svg_parts)

    def get_share_text(self, user_id: str = None) -> str:
        """Generate shareable text for social media"""
        data = self.generate_heatmap_data(user_id, days=365)
        stats = data["statistics"]
        streaks = data["streaks"]

        text = f"📚 My Study Tracker Stats:\n\n"
        text += f"🔥 Current Streak: {streaks['current_streak']} days\n"
        text += f"📅 Active Days: {stats['active_days']}\n"
        text += f"⏱️ Total Study Time: {stats['total_hours']} hours\n"
        text += f"📊 Activity Rate: {stats['activity_rate']}%\n\n"
        text += f"Track your studies with Study Tracker! 🚀"

        return text


# Helper function for easy access
def get_contribution_map(user_id: str = None, days: int = 365) -> Dict[str, Any]:
    """Quick access to generate contribution map"""
    generator = ContributionMap()
    return generator.generate_heatmap_data(user_id, days)


if __name__ == "__main__":
    # Test the contribution map generator
    print("Testing Contribution Map Generator...\n")

    generator = ContributionMap()
    data = generator.generate_heatmap_data(days=30)

    print("Statistics:")
    for key, value in data["statistics"].items():
        print(f"  {key}: {value}")

    print("\nStreaks:")
    for key, value in data["streaks"].items():
        print(f"  {key}: {value}")

    print("\nSample Heatmap Data (first 7 days):")
    for day in data["heatmap"][:7]:
        print(f"  {day['date']}: {day['minutes']} min (Level {day['level']})")

    print("\nContribution map generator working!")
