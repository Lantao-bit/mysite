"""Tests for the data layer (db.py) and authentication (auth.py)."""

import os
import tempfile

import pytest

from portfolio.app import create_app


@pytest.fixture()
def app():
    """Create a test app with a temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({
        "TESTING": True,
        "DATABASE_PATH": db_path,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "WTF_CSRF_ENABLED": False,
    })
    yield app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()


# ── Database layer tests ──────────────────────────────────────────────


class TestDatabase:
    def test_init_db_creates_tables(self, app):
        """Schema initialisation creates users, projects, and comments tables."""
        with app.app_context():
            from sqlalchemy import inspect
            from portfolio.models import db as sa_db

            inspector = inspect(sa_db.engine)
            tables = set(inspector.get_table_names())
        assert {"users", "projects", "comments"}.issubset(tables)

    def test_create_user_returns_id(self, app):
        """create_user returns a positive integer user ID."""
        with app.app_context():
            from portfolio.db import create_user

            uid = create_user("alice", "alice@example.com", "hashed_pw")
        assert isinstance(uid, int) and uid > 0

    def test_get_user_by_username(self, app):
        """get_user_by_username retrieves the correct record."""
        with app.app_context():
            from portfolio.db import create_user, get_user_by_username

            create_user("bob", "bob@example.com", "hashed_pw")
            row = get_user_by_username("bob")
        assert row is not None
        assert row["username"] == "bob"
        assert row["email"] == "bob@example.com"

    def test_get_user_by_username_missing(self, app):
        """get_user_by_username returns None for unknown user."""
        with app.app_context():
            from portfolio.db import get_user_by_username

            assert get_user_by_username("ghost") is None

    def test_get_user_by_id(self, app):
        """get_user_by_id retrieves the correct record."""
        with app.app_context():
            from portfolio.db import create_user, get_user_by_id

            uid = create_user("carol", "carol@example.com", "hashed_pw")
            row = get_user_by_id(uid)
        assert row is not None
        assert row["username"] == "carol"

    def test_duplicate_user_raises(self, app):
        """Duplicate username raises IntegrityError."""
        import sqlite3

        with app.app_context():
            from portfolio.db import create_user

            create_user("dup", "dup@example.com", "hashed_pw")
            with pytest.raises(sqlite3.IntegrityError):
                create_user("dup", "dup2@example.com", "hashed_pw")

    def test_create_comment_and_fetch(self, app):
        """create_comment stores a comment retrievable via get_all_comments."""
        with app.app_context():
            from portfolio.db import create_comment, create_user, get_all_comments

            uid = create_user("dave", "dave@example.com", "hashed_pw")
            create_comment("dave", "Hello world", uid)
            comments = get_all_comments()
        assert len(comments) == 1
        assert comments[0]["body"] == "Hello world"
        assert comments[0]["username"] == "dave"

    def test_comments_ordered_newest_first(self, app):
        """get_all_comments returns comments newest first."""
        import time

        with app.app_context():
            from portfolio.db import create_comment, create_user, get_all_comments

            uid = create_user("eve", "eve@example.com", "hashed_pw")
            create_comment("eve", "first", uid)
            time.sleep(0.05)
            create_comment("eve", "second", uid)
            comments = get_all_comments()
        assert comments[0]["body"] == "second"
        assert comments[1]["body"] == "first"

    def test_get_all_projects_empty(self, app):
        """get_all_projects returns empty list when no projects exist."""
        with app.app_context():
            from portfolio.db import get_all_projects

            assert get_all_projects() == []

    def test_parameterized_queries(self, app):
        """SQL metacharacters in input are treated as literal data."""
        with app.app_context():
            from portfolio.db import create_user, get_user_by_username

            evil = "'; DROP TABLE users; --"
            create_user(evil, "evil@example.com", "hashed_pw")
            row = get_user_by_username(evil)
        assert row is not None
        assert row["username"] == evil


# ── Authentication tests ──────────────────────────────────────────────


class TestAuth:
    def test_register_user_success(self, app):
        """Successful registration returns a User and no error."""
        with app.app_context():
            from portfolio.auth import register_user

            user, err = register_user("frank", "frank@example.com", "password123")
        assert user is not None
        assert err is None
        assert user.username == "frank"

    def test_register_user_short_password(self, app):
        """Password shorter than 8 chars is rejected."""
        with app.app_context():
            from portfolio.auth import register_user

            user, err = register_user("gina", "gina@example.com", "short")
        assert user is None
        assert "8 characters" in err

    def test_register_user_empty_fields(self, app):
        """Empty required fields are rejected."""
        with app.app_context():
            from portfolio.auth import register_user

            user, err = register_user("", "a@b.com", "password123")
        assert user is None
        assert err is not None

    def test_register_user_duplicate(self, app):
        """Duplicate registration returns an error."""
        with app.app_context():
            from portfolio.auth import register_user

            register_user("hank", "hank@example.com", "password123")
            user, err = register_user("hank", "hank2@example.com", "password123")
        assert user is None
        assert "already exists" in err

    def test_register_password_hashed(self, app):
        """Stored password_hash differs from plaintext but verifies."""
        from werkzeug.security import check_password_hash

        with app.app_context():
            from portfolio.auth import register_user
            from portfolio.db import get_user_by_username

            register_user("iris", "iris@example.com", "password123")
            row = get_user_by_username("iris")
        assert row["password_hash"] != "password123"
        assert check_password_hash(row["password_hash"], "password123")

    def test_authenticate_user_success(self, app):
        """Correct credentials return a User."""
        with app.app_context():
            from portfolio.auth import authenticate_user, register_user

            register_user("jack", "jack@example.com", "password123")
            user, err = authenticate_user("jack", "password123")
        assert user is not None
        assert err is None
        assert user.username == "jack"

    def test_authenticate_user_wrong_password(self, app):
        """Wrong password returns an error."""
        with app.app_context():
            from portfolio.auth import authenticate_user, register_user

            register_user("kate", "kate@example.com", "password123")
            user, err = authenticate_user("kate", "wrongpassword")
        assert user is None
        assert "Invalid" in err

    def test_authenticate_user_unknown_user(self, app):
        """Unknown username returns an error."""
        with app.app_context():
            from portfolio.auth import authenticate_user

            user, err = authenticate_user("nobody", "password123")
        assert user is None
        assert "Invalid" in err
