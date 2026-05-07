"""Unit tests for admin route protection and template rendering.

Tests cover:
- Unauthenticated access → redirect to login
- Authenticated non-admin → 403
- Admin access → 200
- Edit/delete non-existent project → 404
- Delete via GET → 405
- Nav bar shows/hides admin links based on user role

Requirements: 1.4, 2.3, 2.4, 3.2, 3.3, 3.4, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import os
import tempfile

import pytest

from portfolio.app import create_app


ADMIN_EMAIL = "admin@portfolio.test"
NON_ADMIN_EMAIL = "user@portfolio.test"


@pytest.fixture()
def app():
    """Create a test app with a temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    test_app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": db_path,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "WTF_CSRF_ENABLED": False,
            "ADMIN_EMAIL": ADMIN_EMAIL,
        }
    )
    yield test_app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_user(app):
    """Create an admin user and return their DB row."""
    with app.app_context():
        from portfolio.db import create_user, get_user_by_username

        create_user("admin", ADMIN_EMAIL, "hashedpw")
        return get_user_by_username("admin")


@pytest.fixture()
def non_admin_user(app):
    """Create a non-admin user and return their DB row."""
    with app.app_context():
        from portfolio.db import create_user, get_user_by_username

        create_user("regular", NON_ADMIN_EMAIL, "hashedpw")
        return get_user_by_username("regular")


def _login_as(client, user_row):
    """Log in as the given user by setting the session."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_row["id"])


# ── Admin routes to test ──────────────────────────────────────────────

ADMIN_GET_ROUTES = [
    "/admin/projects",
    "/admin/projects/create",
    "/admin/projects/export",
    "/admin/projects/import",
]


# ── Unauthenticated access tests ─────────────────────────────────────


class TestUnauthenticatedAccess:
    """Unauthenticated users are redirected to login (Req 8.4)."""

    @pytest.mark.parametrize("route", ADMIN_GET_ROUTES)
    def test_get_routes_redirect_to_login(self, client, route):
        resp = client.get(route)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_edit_route_redirects_to_login(self, client):
        resp = client.get("/admin/projects/1/edit")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_delete_route_redirects_to_login(self, client):
        resp = client.post("/admin/projects/1/delete")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_create_post_redirects_to_login(self, client):
        resp = client.post("/admin/projects/create", data={"title": "x", "description": "y"})
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


# ── Non-admin access tests ────────────────────────────────────────────


class TestNonAdminAccess:
    """Authenticated non-admin users get 403 (Req 8.3)."""

    @pytest.mark.parametrize("route", ADMIN_GET_ROUTES)
    def test_get_routes_return_403(self, client, non_admin_user, route):
        _login_as(client, non_admin_user)
        resp = client.get(route)
        assert resp.status_code == 403

    def test_edit_route_returns_403(self, client, non_admin_user):
        _login_as(client, non_admin_user)
        resp = client.get("/admin/projects/1/edit")
        assert resp.status_code == 403

    def test_delete_route_returns_403(self, client, non_admin_user):
        _login_as(client, non_admin_user)
        resp = client.post("/admin/projects/1/delete")
        assert resp.status_code == 403

    def test_create_post_returns_403(self, client, non_admin_user):
        _login_as(client, non_admin_user)
        resp = client.post("/admin/projects/create", data={"title": "x", "description": "y"})
        assert resp.status_code == 403


# ── Admin access tests ────────────────────────────────────────────────


class TestAdminAccess:
    """Admin users get 200 on management routes (Req 8.2)."""

    def test_projects_list_returns_200(self, client, admin_user):
        _login_as(client, admin_user)
        resp = client.get("/admin/projects")
        assert resp.status_code == 200
        assert b"Manage Portfolio" in resp.data

    def test_create_form_returns_200(self, client, admin_user):
        _login_as(client, admin_user)
        resp = client.get("/admin/projects/create")
        assert resp.status_code == 200
        assert b"Create Project" in resp.data

    def test_export_returns_200(self, client, admin_user):
        _login_as(client, admin_user)
        resp = client.get("/admin/projects/export")
        assert resp.status_code == 200
        assert resp.content_type == "application/json"

    def test_import_form_returns_200(self, client, admin_user):
        _login_as(client, admin_user)
        resp = client.get("/admin/projects/import")
        assert resp.status_code == 200
        assert b"Import Projects" in resp.data

    def test_create_project_success(self, app, client, admin_user):
        _login_as(client, admin_user)
        resp = client.post(
            "/admin/projects/create",
            data={
                "title": "Test Project",
                "description": "A test project",
                "display_order": "1",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Project created successfully" in resp.data

    def test_edit_existing_project(self, app, client, admin_user):
        _login_as(client, admin_user)
        # Create a project first
        with app.app_context():
            from portfolio.db import create_project

            project = create_project("Original", "Original desc")

        # GET edit form
        resp = client.get(f"/admin/projects/{project['id']}/edit")
        assert resp.status_code == 200
        assert b"Edit Project" in resp.data
        assert b"Original" in resp.data

        # POST update
        resp = client.post(
            f"/admin/projects/{project['id']}/edit",
            data={
                "title": "Updated",
                "description": "Updated desc",
                "display_order": "2",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Project updated successfully" in resp.data

    def test_delete_existing_project(self, app, client, admin_user):
        _login_as(client, admin_user)
        with app.app_context():
            from portfolio.db import create_project

            project = create_project("To Delete", "Will be deleted")

        resp = client.post(
            f"/admin/projects/{project['id']}/delete",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Project deleted successfully" in resp.data


# ── 404 tests for non-existent projects ──────────────────────────────


class TestNonExistentProject:
    """Edit/delete non-existent project returns 404 (Req 2.3, 3.2)."""

    def test_edit_nonexistent_returns_404(self, client, admin_user):
        _login_as(client, admin_user)
        resp = client.get("/admin/projects/99999/edit")
        assert resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client, admin_user):
        _login_as(client, admin_user)
        resp = client.post("/admin/projects/99999/delete")
        assert resp.status_code == 404


# ── Delete via GET → 405 ─────────────────────────────────────────────


class TestDeleteMethodRestriction:
    """Delete route only accepts POST (Req 3.4)."""

    def test_delete_via_get_returns_405(self, client, admin_user):
        _login_as(client, admin_user)
        resp = client.get("/admin/projects/1/delete")
        assert resp.status_code == 405


# ── Navigation bar visibility tests ──────────────────────────────────


class TestNavBarAdminLinks:
    """Nav bar shows/hides admin links based on user role (Req 8.5, 8.6)."""

    def test_admin_sees_manage_portfolio_link(self, client, admin_user):
        _login_as(client, admin_user)
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Manage Portfolio" in resp.data

    def test_non_admin_does_not_see_manage_portfolio_link(self, client, non_admin_user):
        _login_as(client, non_admin_user)
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Manage Portfolio" not in resp.data

    def test_anonymous_does_not_see_manage_portfolio_link(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Manage Portfolio" not in resp.data
