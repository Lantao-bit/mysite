"""Property tests for project export/import functionality.

# Feature: portfolio-entry-management, Properties 6-8
#
# Property 6: Export produces correct field set
# Property 7: Import rejects invalid entries without side effects
# Property 8: JSON export/import round-trip
"""

import io
import json
import os
import tempfile

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from portfolio.app import create_app


# ── Strategies ────────────────────────────────────────────────────────

# Non-empty text for required fields (title, description)
non_empty_text = st.text(min_size=1, max_size=200).filter(lambda s: s.strip())

# Optional URL-like strings (or None)
optional_url = st.one_of(st.none(), st.text(min_size=1, max_size=200).filter(lambda s: s.strip()))

# Integer display_order values
display_order_st = st.integers(min_value=-1000, max_value=1000)

# Strategy for a valid project dict (as would appear in JSON)
valid_project_st = st.fixed_dictionaries(
    {
        "title": non_empty_text,
        "description": non_empty_text,
    },
    optional={
        "image_url": optional_url,
        "external_link": optional_url,
        "display_order": display_order_st,
    },
)


def _create_app():
    """Create a test app with a fresh temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    test_app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": db_path,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "WTF_CSRF_ENABLED": False,
            "ADMIN_EMAIL": "admin@test.com",
        }
    )
    return test_app, db_fd, db_path


def _login_admin(client):
    """Register and login as admin user."""
    from portfolio.db import create_user

    from werkzeug.security import generate_password_hash

    create_user("admin", "admin@test.com", generate_password_hash("password123"))
    client.post(
        "/login",
        data={"username": "admin", "password": "password123"},
        follow_redirects=True,
    )


# ── Property 6: Export produces correct field set ─────────────────────


class TestExportCorrectFieldSet:
    """Property 6: Export produces correct field set.

    **Validates: Requirements 5.2, 5.3**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        projects=st.lists(
            st.fixed_dictionaries(
                {
                    "title": non_empty_text,
                    "description": non_empty_text,
                    "image_url": optional_url,
                    "external_link": optional_url,
                    "display_order": display_order_st,
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    def test_export_contains_exactly_correct_keys(self, projects):
        """For any projects, export JSON contains exactly the expected keys and excludes id."""
        test_app, db_fd, db_path = _create_app()
        try:
            with test_app.app_context():
                from portfolio.db import create_project

                for p in projects:
                    create_project(
                        title=p["title"],
                        description=p["description"],
                        image_url=p["image_url"],
                        external_link=p["external_link"],
                        display_order=p["display_order"],
                    )

            with test_app.test_client() as client:
                with test_app.app_context():
                    _login_admin(client)
                    response = client.get("/admin/projects/export")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    expected_keys = {"title", "description", "image_url", "external_link", "display_order"}

                    for item in data:
                        assert set(item.keys()) == expected_keys
                        assert "id" not in item
        finally:
            os.close(db_fd)
            os.unlink(db_path)


# ── Property 7: Import rejects invalid entries without side effects ───


class TestImportRejectsInvalidEntries:
    """Property 7: Import rejects invalid entries without side effects.

    **Validates: Requirements 6.3**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        valid_entries=st.lists(
            st.fixed_dictionaries(
                {
                    "title": non_empty_text,
                    "description": non_empty_text,
                }
            ),
            min_size=0,
            max_size=5,
        ),
        invalid_type=st.sampled_from(["missing_title", "missing_description", "empty_title", "empty_description"]),
    )
    def test_import_with_invalid_entry_creates_zero_records(self, valid_entries, invalid_type):
        """For any JSON array with at least one invalid entry, import creates zero records."""
        test_app, db_fd, db_path = _create_app()
        try:
            # Build an invalid entry based on the type
            if invalid_type == "missing_title":
                invalid_entry = {"description": "Some description"}
            elif invalid_type == "missing_description":
                invalid_entry = {"title": "Some title"}
            elif invalid_type == "empty_title":
                invalid_entry = {"title": "", "description": "Some description"}
            else:  # empty_description
                invalid_entry = {"title": "Some title", "description": ""}

            # Insert the invalid entry at a random position
            entries = list(valid_entries) + [invalid_entry]

            with test_app.test_client() as client:
                with test_app.app_context():
                    _login_admin(client)

                    json_data = json.dumps(entries).encode("utf-8")
                    data = {
                        "file": (io.BytesIO(json_data), "projects.json"),
                    }
                    response = client.post(
                        "/admin/projects/import",
                        data=data,
                        content_type="multipart/form-data",
                        follow_redirects=True,
                    )

                    # Verify zero projects were created
                    from portfolio.db import get_all_projects

                    projects = get_all_projects()
                    assert len(projects) == 0
        finally:
            os.close(db_fd)
            os.unlink(db_path)


# ── Property 8: JSON export/import round-trip ─────────────────────────


class TestJsonRoundTrip:
    """Property 8: JSON export/import round-trip.

    **Validates: Requirements 7.1, 7.2**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        projects=st.lists(
            st.fixed_dictionaries(
                {
                    "title": non_empty_text,
                    "description": non_empty_text,
                    "image_url": optional_url,
                    "external_link": optional_url,
                    "display_order": display_order_st,
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    def test_export_then_import_preserves_data(self, projects):
        """For any valid projects, export then import produces equivalent records."""
        test_app, db_fd, db_path = _create_app()
        try:
            with test_app.app_context():
                from portfolio.db import create_project

                for p in projects:
                    create_project(
                        title=p["title"],
                        description=p["description"],
                        image_url=p["image_url"],
                        external_link=p["external_link"],
                        display_order=p["display_order"],
                    )

            with test_app.test_client() as client:
                with test_app.app_context():
                    _login_admin(client)

                    # Export
                    export_response = client.get("/admin/projects/export")
                    assert export_response.status_code == 200
                    exported_json = export_response.data

            # Create a fresh app/db for import
            test_app2, db_fd2, db_path2 = _create_app()
            try:
                with test_app2.test_client() as client2:
                    with test_app2.app_context():
                        _login_admin(client2)

                        # Import the exported data
                        data = {
                            "file": (io.BytesIO(exported_json), "projects.json"),
                        }
                        import_response = client2.post(
                            "/admin/projects/import",
                            data=data,
                            content_type="multipart/form-data",
                            follow_redirects=True,
                        )
                        assert import_response.status_code == 200

                        # Verify imported records match originals
                        from portfolio.db import get_all_projects

                        imported_projects = get_all_projects()
                        assert len(imported_projects) == len(projects)

                        # Sort both by title+description for comparison
                        original_sorted = sorted(projects, key=lambda p: (p["display_order"], p["title"]))
                        imported_sorted = sorted(
                            imported_projects, key=lambda p: (p["display_order"], p["title"])
                        )

                        for orig, imp in zip(original_sorted, imported_sorted):
                            assert imp["title"] == orig["title"]
                            assert imp["description"] == orig["description"]
                            assert imp["image_url"] == orig["image_url"]
                            assert imp["external_link"] == orig["external_link"]
                            assert imp["display_order"] == orig["display_order"]
            finally:
                os.close(db_fd2)
                os.unlink(db_path2)
        finally:
            os.close(db_fd)
            os.unlink(db_path)
