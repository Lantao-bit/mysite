"""Authentication logic: User class, registration, and login."""

import sqlite3
from functools import wraps

from flask import abort, current_app
from flask_login import UserMixin, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from portfolio.db import create_user, get_user_by_username


def admin_required(f):
    """Decorator that requires the user to be authenticated AND be the admin."""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        admin_email = current_app.config.get("ADMIN_EMAIL")
        if not admin_email or current_user.email != admin_email:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


class User(UserMixin):
    """Flask-Login compatible user class wrapping a DB user record."""

    def __init__(self, id: int, username: str, email: str):
        self.id = id
        self.username = username
        self.email = email

    @staticmethod
    def from_db(row: dict) -> "User":
        """Create a User instance from a database row dict."""
        return User(id=row["id"], username=row["username"], email=row["email"])


def register_user(
    username: str, email: str, password: str
) -> tuple[User | None, str | None]:
    """Validate input, hash password, create user.

    Returns (user, None) on success or (None, error_message) on failure.
    """
    if not username or not email or not password:
        return None, "All fields are required."

    if len(password) < 8:
        return None, "Password must be at least 8 characters."

    password_hash = generate_password_hash(password)

    try:
        user_id = create_user(username, email, password_hash)
    except sqlite3.IntegrityError:
        return None, "Username or email already exists."

    return User(id=user_id, username=username, email=email), None


def authenticate_user(
    username: str, password: str
) -> tuple[User | None, str | None]:
    """Check credentials.

    Returns (user, None) on success or (None, error_message) on failure.
    """
    row = get_user_by_username(username)
    if row is None or not check_password_hash(row["password_hash"], password):
        return None, "Invalid username or password."

    return User.from_db(row), None
