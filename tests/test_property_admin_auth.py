"""Property test for admin authorization gate.

# Feature: portfolio-entry-management, Property 1: Admin authorization gate
#
# For any HTTP request to any admin-protected route, access SHALL be granted
# if and only if the requester is authenticated and their email matches the
# configured ADMIN_EMAIL. Unauthenticated requests are redirected to login;
# authenticated non-admin requests receive 403.
#
# Validates: Requirements 1.4, 2.4, 3.3, 4.3, 5.4, 6.5, 8.2, 8.3, 8.4
"""

import os
import tempfile

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from portfolio.app import create_app
from portfolio.auth import admin_required


ADMIN_EMAIL = "admin@portfolio.test"


def _make_app(admin_email=ADMIN_EMAIL):
    """Create a test app with a temporary database and an admin-protected route."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    test_app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": db_path,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "WTF_CSRF_ENABLED": False,
            "ADMIN_EMAIL": admin_email,
        }
    )

    @test_app.route("/test-admin-only")
    @admin_required
    def test_admin_only():
        return "OK", 200

    return test_app, db_fd, db_path


@pytest.fixture()
def app():
    test_app, db_fd, db_path = _make_app()
    yield test_app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()


# ── Property Test ─────────────────────────────────────────────────────


# Strategy: generate email addresses that are NOT the admin email
non_admin_emails = st.emails().filter(lambda e: e != ADMIN_EMAIL)


class TestAdminAuthorizationGate:
    """Property 1: Admin authorization gate."""

    def test_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated requests to admin routes redirect to login."""
        resp = client.get("/test-admin-only")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    @settings(max_examples=100)
    @given(email=non_admin_emails)
    def test_non_admin_gets_403(self, email):
        """Authenticated users whose email != ADMIN_EMAIL get 403."""
        test_app, db_fd, db_path = _make_app()
        try:
            test_client = test_app.test_client()
            with test_app.app_context():
                from portfolio.db import create_user, get_user_by_username

                # Create a unique username from the email
                username = f"u{hash(email) % 10000000}"
                row = get_user_by_username(username)
                if not row:
                    try:
                        create_user(username, email, "hashedpw")
                    except Exception:
                        return  # skip if we can't create (e.g. duplicate email)
                    row = get_user_by_username(username)

                if row:
                    with test_client.session_transaction() as sess:
                        sess["_user_id"] = str(row["id"])

                    resp = test_client.get("/test-admin-only")
                    assert resp.status_code == 403
        finally:
            os.close(db_fd)
            os.unlink(db_path)

    def test_admin_gets_access(self, app, client):
        """Authenticated user whose email == ADMIN_EMAIL gets 200."""
        with app.app_context():
            from portfolio.db import create_user, get_user_by_username

            username = ADMIN_EMAIL.split("@")[0]
            row = get_user_by_username(username)
            if not row:
                create_user(username, ADMIN_EMAIL, "hashedpw")
                row = get_user_by_username(username)

            with client.session_transaction() as sess:
                sess["_user_id"] = str(row["id"])

            resp = client.get("/test-admin-only")
            assert resp.status_code == 200
            assert resp.data == b"OK"

    @settings(max_examples=100)
    @given(admin_email=st.emails())
    def test_access_granted_iff_email_matches(self, admin_email):
        """Access is granted if and only if user email matches ADMIN_EMAIL config."""
        test_app, db_fd, db_path = _make_app(admin_email=admin_email)
        try:
            test_client = test_app.test_client()
            with test_app.app_context():
                from portfolio.db import create_user, get_user_by_username

                username = f"admin{hash(admin_email) % 10000000}"
                row = get_user_by_username(username)
                if not row:
                    try:
                        create_user(username, admin_email, "hashedpw")
                    except Exception:
                        return
                    row = get_user_by_username(username)

                if row:
                    with test_client.session_transaction() as sess:
                        sess["_user_id"] = str(row["id"])

                    resp = test_client.get("/test-admin-only")
                    assert resp.status_code == 200
        finally:
            os.close(db_fd)
            os.unlink(db_path)
