"""
Authentication utilities for Study Tracker
Handles JWT tokens, password hashing, and auth middleware
"""

import jwt
import uuid
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, jsonify, g
from database import DatabaseManager
from config import config
import logging

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a password for storing"""
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash"""
    return check_password_hash(password_hash, password)


def generate_jwt_token(user_id: str, expires_days: int = 30) -> str:
    """Generate a JWT token for a user"""
    payload = {
        "user_id": user_id,
        "token_id": str(uuid.uuid4()),
        "exp": datetime.utcnow() + timedelta(days=expires_days),
        "iat": datetime.utcnow(),
        "type": "access",
    }

    return jwt.encode(payload, config.security.secret_key, algorithm="HS256")


def decode_jwt_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, config.security.secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}


def get_auth_token_from_request() -> str:
    """Extract auth token from request headers"""
    auth_header = request.headers.get("Authorization", "")

    # Check for Bearer token
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Check for token in query params (for downloads, etc.)
    token = request.args.get("token", "")
    if token:
        return token

    return None


def require_auth(f):
    """Decorator to require authentication for a route"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_auth_token_from_request()

        if not token:
            return jsonify(
                {
                    "success": False,
                    "error": "Authentication required",
                    "message": "Please provide a valid token in the Authorization header",
                }
            ), 401

        # Decode token
        payload = decode_jwt_token(token)

        if "error" in payload:
            return jsonify(
                {
                    "success": False,
                    "error": "Invalid token",
                    "message": payload["error"],
                }
            ), 401

        # Get user from database
        db = DatabaseManager()
        user = db.get_user_by_id(payload.get("user_id"))

        if not user:
            return jsonify(
                {
                    "success": False,
                    "error": "User not found",
                    "message": "The user associated with this token no longer exists",
                }
            ), 401

        if not user.get("is_active", True):
            return jsonify(
                {
                    "success": False,
                    "error": "Account disabled",
                    "message": "This account has been disabled",
                }
            ), 403

        # Store user info in Flask's g object for use in the route
        g.current_user = user
        g.user_id = user["id"]

        return f(*args, **kwargs)

    return decorated_function


def get_current_user() -> dict:
    """Get the current authenticated user from request context"""
    return getattr(g, "current_user", None)


def get_current_user_id() -> str:
    """Get the current authenticated user ID from request context"""
    return getattr(g, "user_id", None)


def optional_auth(f):
    """Decorator for routes that can work with or without authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_auth_token_from_request()

        if token:
            payload = decode_jwt_token(token)
            if "error" not in payload:
                db = DatabaseManager()
                user = db.get_user_by_id(payload.get("user_id"))
                if user and user.get("is_active", True):
                    g.current_user = user
                    g.user_id = user["id"]

        return f(*args, **kwargs)

    return decorated_function


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password: str) -> tuple:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    return True, "Password is strong"


def sanitize_username(username: str) -> str:
    """Sanitize and validate username"""
    # Remove whitespace and convert to lowercase
    username = username.strip().lower()

    # Remove special characters, allow only alphanumeric and underscore
    import re

    username = re.sub(r"[^a-z0-9_]", "", username)

    # Limit length
    username = username[:30]

    return username


class AuthError(Exception):
    """Custom exception for authentication errors"""

    pass


# Development helper - create test user
def create_test_user(
    email: str = "test@example.com",
    password: str = "Test123!",
    username: str = "testuser",
):
    """Create a test user for development"""
    db = DatabaseManager()

    # Check if user exists
    existing = db.get_user_by_email(email)
    if existing:
        print(f"Test user already exists: {email}")
        return existing["id"]

    # Create user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)

    if db.create_user(user_id, email, password_hash, username, "Test User"):
        print(f"Created test user: {email} / {password}")
        return user_id
    else:
        print("Failed to create test user")
        return None


if __name__ == "__main__":
    # Test the auth system
    print("Testing authentication system...")

    # Create test user
    user_id = create_test_user()

    if user_id:
        # Generate token
        token = generate_jwt_token(user_id)
        print(f"Generated token: {token[:50]}...")

        # Verify token
        payload = decode_jwt_token(token)
        print(f"Token payload: {payload}")

        print("\nAuthentication system working!")
    else:
        print("Authentication test failed")
