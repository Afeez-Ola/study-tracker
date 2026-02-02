import time
import re
import html
import csv
import io
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_productivity(productivity: float) -> str:
    """Format productivity with level indicator"""
    if productivity >= 90:
        return f"{productivity:.1f}% (Excellent)"
    elif productivity >= 75:
        return f"{productivity:.1f}% (Good)"
    elif productivity >= 60:
        return f"{productivity:.1f}% (Moderate)"
    elif productivity >= 40:
        return f"{productivity:.1f}% (Poor)"
    else:
        return f"{productivity:.1f}% (Very Poor)"


def format_datetime(dt_string: str, format_type: str = "date") -> str:
    """Format datetime string for display"""
    if not dt_string:
        return ""

    try:
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))

        if format_type == "date":
            return dt.strftime("%Y-%m-%d")
        elif format_type == "time":
            return dt.strftime("%I:%M %p")
        elif format_type == "datetime":
            return dt.strftime("%Y-%m-%d %I:%M %p")
        elif format_type == "relative":
            now = datetime.now()
            diff = now - dt

            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
        else:
            return dt_string
    except Exception as e:
        logger.warning(f"Error formatting datetime: {e}")
        return dt_string


def sanitize_string(text: str, max_length: int = 200) -> str:
    """Sanitize string for safe display"""
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Escape HTML entities
    text = html.unescape(text)

    # Remove special characters but keep basic punctuation
    text = re.sub(r"[^\w\s\-\.,!?():@#]", "", text)

    # Strip whitespace and limit length
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length].rstrip()

    return text


def validate_csv_content(content: str) -> tuple:
    """Validate CSV content and return (is_valid, errors)"""
    if not content or not content.strip():
        return False, ["CSV content is empty"]

    try:
        # Try to parse as CSV
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)

        if len(rows) < 2:
            return False, ["CSV must have at least a header and one data row"]

        # Check if rows have consistent columns
        if rows:
            expected_cols = len(rows[0])
            for i, row in enumerate(rows[1:], 1):
                if len(row) != expected_cols:
                    return False, [
                        f"Row {i} has {len(row)} columns, expected {expected_cols}"
                    ]

        return True, []

    except Exception as e:
        return False, [f"CSV parsing error: {str(e)}"]


def calculate_time_periods(start_time: str, end_time: str = None) -> Dict[str, int]:
    """Calculate time periods from start/end times"""
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        else:
            end_dt = datetime.utcnow()

        duration = end_dt - start_dt

        return {
            "total_seconds": int(duration.total_seconds()),
            "minutes": int(duration.total_seconds() // 60),
            "hours": int(duration.total_seconds() // 3600),
            "days": int(duration.total_seconds() // 86400),
        }

    except Exception as e:
        logger.error(f"Error calculating time periods: {e}")
        return {"total_seconds": 0, "minutes": 0, "hours": 0, "days": 0}


def generate_filename(base_name: str, extension: str = ".csv") -> str:
    """Generate filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = re.sub(r"[^\w\s-]", "", base_name).strip()
    return f"{clean_name}_{timestamp}{extension}"


def get_time_ranges() -> List[Dict[str, str]]:
    """Get predefined time ranges for filtering"""
    now = datetime.now()

    return [
        {
            "label": "Today",
            "date_from": now.strftime("%Y-%m-%d"),
            "date_to": now.strftime("%Y-%m-%d"),
        },
        {
            "label": "Yesterday",
            "date_from": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
            "date_to": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        {
            "label": "Last 7 Days",
            "date_from": (now - timedelta(days=6)).strftime("%Y-%m-%d"),
            "date_to": now.strftime("%Y-%m-%d"),
        },
        {
            "label": "Last 30 Days",
            "date_from": (now - timedelta(days=29)).strftime("%Y-%m-%d"),
            "date_to": now.strftime("%Y-%m-%d"),
        },
        {
            "label": "This Month",
            "date_from": now.replace(day=1).strftime("%Y-%m-%d"),
            "date_to": now.strftime("%Y-%m-%d"),
        },
        {
            "label": "Last Month",
            "date_from": (now.replace(day=1) - timedelta(days=1))
            .replace(day=1)
            .strftime("%Y-%m-%d"),
            "date_to": (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        {
            "label": "This Year",
            "date_from": now.replace(month=1, day=1).strftime("%Y-%m-%d"),
            "date_to": now.strftime("%Y-%m-%d"),
        },
    ]


def calculate_percentile(values: List[float], percentile: int) -> float:
    """Calculate percentile value from a list of numbers"""
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = (percentile / 100) * (len(sorted_values) - 1)

    if index.is_integer():
        return sorted_values[int(index)]
    else:
        lower = sorted_values[int(index)]
        upper = sorted_values[int(index) + 1]
        return lower + (upper - lower) * (index - int(index))


def create_pie_chart_data(data: Dict[str, int]) -> List[Dict[str, Any]]:
    """Create pie chart data from categorical data"""
    total = sum(data.values())

    chart_data = []
    for label, value in data.items():
        chart_data.append(
            {
                "label": label,
                "value": value,
                "percentage": round((value / total * 100), 1) if total > 0 else 0,
            }
        )

    # Sort by value descending
    chart_data.sort(key=lambda x: x["value"], reverse=True)

    return chart_data


def create_line_chart_data(
    data_points: List[Dict[str, Any]], x_key: str = "date", y_key: str = "value"
) -> Dict[str, List]:
    """Create line chart data from data points"""
    labels = []
    values = []

    for point in data_points:
        if x_key in point and y_key in point:
            labels.append(point[x_key])
            values.append(point[y_key])

    return {"labels": labels, "values": values}


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))


def is_valid_email(email: str) -> bool:
    """Basic email validation"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def generate_color_palette(size: int) -> List[str]:
    """Generate a color palette for charts"""
    base_colors = [
        "#3498db",
        "#e74c3c",
        "#2ecc71",
        "#f39c12",
        "#9b59b6",
        "#1abc9c",
        "#34495e",
        "#e67e22",
        "#95a5a6",
        "#d35400",
        "#c0392b",
        "#16a085",
        "#27ae60",
        "#2980b9",
        "#8e44ad",
    ]

    if size <= len(base_colors):
        return base_colors[:size]

    # Generate additional colors if needed
    colors = base_colors.copy()
    for i in range(size - len(base_colors)):
        # Generate random-ish colors
        hue = (i * 137.5) % 360  # Golden angle
        colors.append(f"hsl({hue}, 70%, 60%)")

    return colors


def create_summary_stats(numbers: List[float]) -> Dict[str, float]:
    """Create summary statistics for a list of numbers"""
    if not numbers:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "min": 0.0,
            "max": 0.0,
            "std": 0.0,
        }

    sorted_numbers = sorted(numbers)
    count = len(numbers)
    mean = sum(numbers) / count

    # Calculate median
    if count % 2 == 0:
        median = (sorted_numbers[count // 2 - 1] + sorted_numbers[count // 2]) / 2
    else:
        median = sorted_numbers[count // 2]

    # Calculate standard deviation
    variance = sum((x - mean) ** 2 for x in numbers) / count
    std = variance**0.5

    return {
        "count": count,
        "mean": round(mean, 2),
        "median": round(median, 2),
        "min": round(min(sorted_numbers), 2),
        "max": round(max(sorted_numbers), 2),
        "std": round(std, 2),
    }
