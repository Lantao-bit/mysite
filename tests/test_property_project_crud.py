"""Property tests for project CRUD database functions.

# Feature: portfolio-entry-management, Properties 2-5
#
# Property 2: Create project preserves data
# Property 3: Update project preserves data
# Property 4: Delete project removes record
# Property 5: Project listing is ordered by display_order
"""

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


@pytest.fixture()
def app():
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
    yield test_app
    os.close(db_fd)
    os.unlink(db_path)


# ── Property 2: Create project preserves data ─────────────────────────


class TestCreateProjectPreservesData:
    """Property 2: Create project preserves data.

    **Validates: Requirements 1.1**
    """

    @settings(max_examples=100)
    @given(
        title=non_empty_text,
        description=non_empty_text,
        image_url=optional_url,
        external_link=optional_url,
        display_order=display_order_st,
    )
    def test_create_project_preserves_all_fields(
        self, title, description, image_url, external_link, display_order
    ):
        """For any valid project data, create_project returns a dict with matching field values."""
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
        try:
            with test_app.app_context():
                from portfolio.db import create_project

                result = create_project(
                    title=title,
                    description=description,
                    image_url=image_url,
                    external_link=external_link,
                    display_order=display_order,
                )

                assert result["title"] == title
                assert result["description"] == description
                assert result["image_url"] == image_url
                assert result["external_link"] == external_link
                assert result["display_order"] == display_order
                assert "id" in result
                assert isinstance(result["id"], int)
        finally:
            os.close(db_fd)
            os.unlink(db_path)


# ── Property 3: Update project preserves data ─────────────────────────


class TestUpdateProjectPreservesData:
    """Property 3: Update project preserves data.

    **Validates: Requirements 2.1**
    """

    @settings(max_examples=100)
    @given(
        title=non_empty_text,
        description=non_empty_text,
        image_url=optional_url,
        external_link=optional_url,
        display_order=display_order_st,
        new_title=non_empty_text,
        new_description=non_empty_text,
        new_image_url=optional_url,
        new_external_link=optional_url,
        new_display_order=display_order_st,
    )
    def test_update_project_preserves_all_fields(
        self,
        title,
        description,
        image_url,
        external_link,
        display_order,
        new_title,
        new_description,
        new_image_url,
        new_external_link,
        new_display_order,
    ):
        """For any existing project and valid updated fields, update_project returns matching values."""
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
        try:
            with test_app.app_context():
                from portfolio.db import create_project, update_project

                created = create_project(
                    title=title,
                    description=description,
                    image_url=image_url,
                    external_link=external_link,
                    display_order=display_order,
                )

                result = update_project(
                    project_id=created["id"],
                    title=new_title,
                    description=new_description,
                    image_url=new_image_url,
                    external_link=new_external_link,
                    display_order=new_display_order,
                )

                assert result is not None
                assert result["id"] == created["id"]
                assert result["title"] == new_title
                assert result["description"] == new_description
                assert result["image_url"] == new_image_url
                assert result["external_link"] == new_external_link
                assert result["display_order"] == new_display_order
        finally:
            os.close(db_fd)
            os.unlink(db_path)


# ── Property 4: Delete project removes record ─────────────────────────


class TestDeleteProjectRemovesRecord:
    """Property 4: Delete project removes record.

    **Validates: Requirements 3.1**
    """

    @settings(max_examples=100)
    @given(
        title=non_empty_text,
        description=non_empty_text,
        image_url=optional_url,
        external_link=optional_url,
        display_order=display_order_st,
    )
    def test_delete_project_makes_it_unfindable(
        self, title, description, image_url, external_link, display_order
    ):
        """For any created project, delete_project causes get_project_by_id to return None."""
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
        try:
            with test_app.app_context():
                from portfolio.db import create_project, delete_project, get_project_by_id

                created = create_project(
                    title=title,
                    description=description,
                    image_url=image_url,
                    external_link=external_link,
                    display_order=display_order,
                )

                result = delete_project(created["id"])
                assert result is True

                fetched = get_project_by_id(created["id"])
                assert fetched is None
        finally:
            os.close(db_fd)
            os.unlink(db_path)


# ── Property 5: Project listing is ordered by display_order ───────────


class TestProjectListingOrder:
    """Property 5: Project listing is ordered by display_order.

    **Validates: Requirements 4.1**
    """

    @settings(max_examples=100)
    @given(
        orders=st.lists(display_order_st, min_size=1, max_size=20),
    )
    def test_get_all_projects_returns_sorted_by_display_order(self, orders):
        """For any set of projects with random display_order, get_all_projects returns them sorted."""
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
        try:
            with test_app.app_context():
                from portfolio.db import create_project, get_all_projects

                for i, order in enumerate(orders):
                    create_project(
                        title=f"Project {i}",
                        description=f"Description {i}",
                        display_order=order,
                    )

                projects = get_all_projects()
                display_orders = [p["display_order"] for p in projects]

                # Verify non-decreasing order
                for i in range(len(display_orders) - 1):
                    assert display_orders[i] <= display_orders[i + 1]
        finally:
            os.close(db_fd)
            os.unlink(db_path)
