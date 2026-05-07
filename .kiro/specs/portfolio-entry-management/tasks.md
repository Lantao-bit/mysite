# Implementation Plan: Portfolio Entry Management

## Overview

This plan implements admin-only CRUD operations for portfolio entries, plus JSON export/import, building on the existing Flask app factory pattern, db.py data-access layer, and Flask-Login authentication. Tasks are ordered so each step builds on the previous one, starting with the authorization layer, then data access, forms, routes, templates, and finally integration.

## Tasks

- [x] 1. Add ADMIN_EMAIL configuration and admin_required decorator
  - [x] 1.1 Add ADMIN_EMAIL config to app factory
    - In `portfolio/app.py`, add `app.config["ADMIN_EMAIL"] = os.environ.get("ADMIN_EMAIL", "")` before the `if config:` block so it can be overridden by test config
    - _Requirements: 8.1_

  - [x] 1.2 Implement admin_required decorator in portfolio/auth.py
    - Add `admin_required` decorator that wraps `login_required` and checks `current_user.email == current_app.config.get('ADMIN_EMAIL')`
    - Unauthenticated users redirect to login; authenticated non-admin users get 403
    - _Requirements: 8.2, 8.3, 8.4_

  - [x] 1.3 Write property test for admin authorization gate
    - **Property 1: Admin authorization gate**
    - Generate random user emails with Hypothesis, test against an admin-protected route, verify access granted iff email matches ADMIN_EMAIL, unauthenticated → redirect, non-admin → 403
    - **Validates: Requirements 1.4, 2.4, 3.3, 4.3, 5.4, 6.5, 8.2, 8.3, 8.4**

- [x] 2. Implement database functions for project CRUD
  - [x] 2.1 Add get_project_by_id function to portfolio/db.py
    - Accepts `project_id: int`, returns project dict or None
    - Follow existing pattern of returning plain dicts
    - _Requirements: 2.2, 2.3, 3.1, 3.2_

  - [x] 2.2 Add create_project function to portfolio/db.py
    - Accepts `title, description, image_url=None, external_link=None, display_order=0`
    - Returns created project dict with all fields including id
    - _Requirements: 1.1_

  - [x] 2.3 Add update_project function to portfolio/db.py
    - Accepts `project_id, title, description, image_url=None, external_link=None, display_order=0`
    - Returns updated project dict or None if not found
    - _Requirements: 2.1_

  - [x] 2.4 Add delete_project function to portfolio/db.py
    - Accepts `project_id: int`, returns True if deleted, False if not found
    - _Requirements: 3.1, 3.2_

  - [x] 2.5 Write property test for create_project preserves data
    - **Property 2: Create project preserves data**
    - Generate random valid project fields (non-empty title, non-empty description, optional image_url, optional external_link, integer display_order), call `create_project`, verify returned dict field values match inputs
    - **Validates: Requirements 1.1**

  - [x] 2.6 Write property test for update_project preserves data
    - **Property 3: Update project preserves data**
    - Create a project, generate random valid updated fields, call `update_project`, verify returned dict matches new inputs
    - **Validates: Requirements 2.1**

  - [x] 2.7 Write property test for delete_project removes record
    - **Property 4: Delete project removes record**
    - Create a random project, call `delete_project`, verify `get_project_by_id` returns None
    - **Validates: Requirements 3.1**

  - [x] 2.8 Write property test for project listing order
    - **Property 5: Project listing is ordered by display_order**
    - Create multiple projects with random display_order values, call `get_all_projects()`, verify results are in non-decreasing order of display_order
    - **Validates: Requirements 4.1**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Add ProjectForm and implement management routes
  - [x] 4.1 Add ProjectForm to portfolio/forms.py
    - Add `ProjectForm` with fields: title (DataRequired), description (DataRequired), image_url (Optional, URL), external_link (Optional, URL), display_order (IntegerField, Optional, default=0)
    - Import `Optional`, `URL`, `IntegerField` from wtforms
    - _Requirements: 1.3_

  - [x] 4.2 Implement admin project list route
    - Add `GET /admin/projects` route decorated with `@admin_required`
    - Fetch all projects via `get_all_projects()` and render `admin_projects.html`
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 4.3 Implement create project route
    - Add `GET, POST /admin/projects/create` route decorated with `@admin_required`
    - GET: render `admin_project_form.html` with empty `ProjectForm`
    - POST: validate form, call `create_project`, flash success, redirect to admin_projects
    - On validation failure, re-render form with errors
    - _Requirements: 1.1, 1.2, 1.4_

  - [x] 4.4 Implement edit project route
    - Add `GET, POST /admin/projects/<int:id>/edit` route decorated with `@admin_required`
    - GET: fetch project by id (404 if not found), pre-populate `ProjectForm` with current values
    - POST: validate form, call `update_project`, flash success, redirect to admin_projects
    - On validation failure, re-render form with errors
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 4.5 Implement delete project route
    - Add `POST /admin/projects/<int:id>/delete` route decorated with `@admin_required`
    - Call `delete_project`, return 404 if not found, flash success and redirect on success
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 4.6 Implement export projects route
    - Add `GET /admin/projects/export` route decorated with `@admin_required`
    - Serialize all projects to JSON (excluding `id` field), return as downloadable file with `Content-Disposition: attachment; filename=projects.json`
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 4.7 Implement import projects route
    - Add `GET, POST /admin/projects/import` route decorated with `@admin_required`
    - GET: render `admin_import.html` with file upload form
    - POST: parse uploaded JSON file, validate each entry has title and description, create all projects if valid, flash success with count
    - On invalid JSON: flash error about format
    - On missing required fields: flash error identifying invalid entries, create zero records
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 4.8 Write property test for export correct field set
    - **Property 6: Export produces correct field set**
    - Create random projects, call the export logic, verify each JSON object contains exactly keys: title, description, image_url, external_link, display_order — and does NOT contain id
    - **Validates: Requirements 5.2, 5.3**

  - [x] 4.9 Write property test for import rejects invalid entries
    - **Property 7: Import rejects invalid entries without side effects**
    - Generate JSON arrays where at least one entry is missing title or description, attempt import, verify zero project records created and error returned
    - **Validates: Requirements 6.3**

  - [x] 4.10 Write property test for JSON round-trip
    - **Property 8: JSON export/import round-trip**
    - Create random valid projects, export them, import the resulting JSON, verify imported records have equivalent field values (title, description, image_url, external_link, display_order)
    - **Validates: Requirements 7.1, 7.2**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create templates and update navigation
  - [x] 6.1 Create admin_projects.html template
    - Extend `base.html`, display all projects in a Bootstrap table with columns: Title, Description (truncated), Display Order, Actions (Edit, Delete links)
    - Include links to create, export, and import pages
    - Delete action uses a POST form with CSRF token
    - _Requirements: 4.1, 4.2_

  - [x] 6.2 Create admin_project_form.html template
    - Extend `base.html`, render `ProjectForm` fields with Bootstrap styling
    - Display field-specific validation errors
    - Support both create and edit modes (dynamic heading and submit button text)
    - _Requirements: 1.2, 1.3, 2.2_

  - [x] 6.3 Create admin_import.html template
    - Extend `base.html`, provide a file upload form for JSON import with CSRF token
    - Include instructions about expected JSON format
    - _Requirements: 6.1, 6.4_

  - [x] 6.4 Update base.html navigation bar with conditional admin links
    - Add "Manage Portfolio" nav link visible only when `current_user.is_authenticated` and `current_user.email == config.ADMIN_EMAIL`
    - _Requirements: 8.5, 8.6_

  - [x] 6.5 Write unit tests for route protection and template rendering
    - Test unauthenticated access → redirect to login
    - Test authenticated non-admin → 403
    - Test admin access → 200
    - Test edit/delete non-existent project → 404
    - Test delete via GET → 405
    - Test nav bar shows/hides admin links based on user role
    - _Requirements: 1.4, 2.3, 2.4, 3.2, 3.3, 3.4, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- All code uses Python with the existing Flask/SQLAlchemy/pytest stack
