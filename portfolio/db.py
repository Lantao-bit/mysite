"""Database access layer using SQLAlchemy.

Preserves the same function signatures as the original raw sqlite3 version
so that auth.py, routes.py, and tests require minimal changes.
"""

import sqlite3

from portfolio.models import Comment, Project, User, db


def init_db(app):
    """Initialize SQLAlchemy and create tables if they don't exist."""
    db.init_app(app)
    with app.app_context():
        db.create_all()


def get_all_projects() -> list[dict]:
    """Fetch all project records ordered by display_order."""
    rows = Project.query.order_by(Project.display_order).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "image_url": p.image_url,
            "external_link": p.external_link,
            "display_order": p.display_order,
        }
        for p in rows
    ]


def get_all_comments() -> list[dict]:
    """Fetch all comments ordered newest first."""
    rows = Comment.query.order_by(Comment.created_at.desc(), Comment.id.desc()).all()
    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "username": c.username,
            "body": c.body,
            "created_at": c.created_at,
        }
        for c in rows
    ]


def create_comment(username: str, body: str, user_id: int) -> dict:
    """Insert a comment and return the created record."""
    comment = Comment(user_id=user_id, username=username, body=body)
    db.session.add(comment)
    db.session.commit()
    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "username": comment.username,
        "body": comment.body,
        "created_at": comment.created_at,
    }


def create_user(username: str, email: str, password_hash: str) -> int:
    """Insert a new user and return the user ID.

    Raises sqlite3.IntegrityError on duplicate to preserve backward compatibility.
    """
    from sqlalchemy.exc import IntegrityError as SAIntegrityError

    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)
    try:
        db.session.commit()
    except SAIntegrityError:
        db.session.rollback()
        raise sqlite3.IntegrityError("UNIQUE constraint failed")
    return user.id


def get_user_by_username(username: str) -> dict | None:
    """Fetch a user record by username, or None if not found."""
    user = User.query.filter_by(username=username).first()
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "password_hash": user.password_hash,
        "created_at": user.created_at,
    }


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user record by ID, or None if not found."""
    user = db.session.get(User, user_id)
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "password_hash": user.password_hash,
        "created_at": user.created_at,
    }
