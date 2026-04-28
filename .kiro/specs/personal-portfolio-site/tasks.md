# Implementation Plan: Personal Portfolio Site

## Overview

Build a single-page personal portfolio website using Flask, Bootstrap 5, and SQLite. Implementation proceeds bottom-up: data layer and models first, then authentication, then routes and templates, and finally wiring and integration. All code uses Python with Flask, Jinja2 templates, and the built-in sqlite3 module.

## Tasks

- [x] 1. Set up project structure and dependencies
  - [x] 1.1 Create project skeleton and requirements.txt
    - Create the `portfolio/` directory structure: `app.py`, `routes.py`, `auth.py`, `db.py`, `models.py`, `forms.py`, `templates/`, `static/css/`, `static/images/`
    - Create `requirements.txt` with Flask, Flask-Login, Flask-WTF, Werkzeug, pytest, hypothesis
    - _Requirements: 8.1_

  - [x] 1.2 Implement data classes in `models.py`
    - Define `User`, `Project`, and `Comment` dataclasses as specified in the design
    - _Requirements: 2.2, 3.2, 5.2_

- [ ] 2. Implement database layer
  - [x] 2.1 Implement `db.py` with schema initialization and query functions
    - Implement `get_db()` for request-scoped connections
    - Implement `init_db()` to create `users`, `projects`, and `comments` tables if they don't exist
    - Implement `get_all_projects()`, `get_all_comments()` (newest first), `create_comment()`, `create_user()`, `get_user_by_username()`, `get_user_by_id()`
    - All queries MUST use parameterized statements
    - _Requirements: 8.1, 8.2, 8.3, 5.1, 2.1_

  - [ ]* 2.2 Write property test: SQL injection safety
    - **Property 10: SQL injection safety**
    - Test that user-supplied strings with SQL metacharacters are treated as literal data across registration, login, and comment operations
    - Use Hypothesis to generate strings with quotes, semicolons, UNION/DROP keywords
    - **Validates: Requirements 8.2**

- [ ] 3. Implement authentication
  - [x] 3.1 Implement `auth.py` with User class, registration, and login logic
    - Create `User(UserMixin)` class compatible with Flask-Login
    - Implement `register_user()`: validate input, enforce password >= 8 chars, hash with Werkzeug, call `create_user()`, handle `IntegrityError` for duplicates
    - Implement `authenticate_user()`: look up user, verify password hash, return user or error
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 4.2, 4.3_

  - [ ]* 3.2 Write property test: Registration round-trip with password hashing
    - **Property 2: Registration round-trip with password hashing**
    - For random valid inputs (username, email, password len >= 8), verify stored record matches input and password_hash verifies correctly but differs from plaintext
    - **Validates: Requirements 3.2, 3.4**

  - [ ]* 3.3 Write property test: Duplicate registration rejection
    - **Property 3: Duplicate registration rejection**
    - Register a user, then attempt to register again with same username or email; verify failure and unchanged user count
    - **Validates: Requirements 3.3**

  - [ ]* 3.4 Write property test: Short password rejection
    - **Property 4: Short password rejection**
    - For random passwords of length 0-7, verify registration fails with validation error and no user record is created
    - **Validates: Requirements 3.5**

  - [ ]* 3.5 Write property test: Valid login creates authenticated session
    - **Property 5: Valid login creates authenticated session**
    - Register a user, then login with correct credentials; verify authentication succeeds
    - **Validates: Requirements 4.2**

  - [ ]* 3.6 Write property test: Invalid login rejection
    - **Property 6: Invalid login rejection**
    - For random non-matching credential pairs, verify login fails without creating a session
    - **Validates: Requirements 4.3**

- [x] 4. Implement forms
  - [x] 4.1 Implement `forms.py` with WTForms definitions
    - Create `RegistrationForm` with username (required), email (required, email validation), password (required, min length 8)
    - Create `LoginForm` with username and password fields
    - Create `CommentForm` with body (required, non-empty)
    - All forms include CSRF protection via Flask-WTF
    - _Requirements: 3.1, 3.5, 4.1, 6.1, 6.4_

- [x] 5. Checkpoint - Ensure data layer and auth tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Flask app factory and routes
  - [x] 6.1 Implement `app.py` with Flask app factory
    - Create `create_app()` function: configure SECRET_KEY, DATABASE_PATH, initialize Flask-Login with `user_loader`, register routes, call `init_db()`
    - Register custom 404 and 500 error handlers
    - _Requirements: 8.1, 8.3_

  - [x] 6.2 Implement `routes.py` with all route handlers
    - `index()`: fetch projects and comments from DB, render `index.html`
    - `register()`: GET renders form, POST validates and creates user, handles duplicates
    - `login()`: GET renders form, POST authenticates and creates session, redirects to main page
    - `logout()`: terminates session, redirects to main page
    - `add_comment()`: POST only, `@login_required`, validates non-empty body, stores comment, handles DB errors, redirects to main page with `#comments` anchor
    - _Requirements: 1.1, 2.1, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 5.1, 5.3, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 7. Implement templates
  - [x] 7.1 Create `base.html` template
    - Include Bootstrap 5 CDN links
    - Navbar with links to `#professional`, `#portfolio`, `#comments` sections
    - Conditionally show logged-in username + logout link, or login/register links
    - Footer with copyright information
    - Flash message display area
    - _Requirements: 4.5, 7.1, 7.2, 7.3_

  - [x] 7.2 Create `index.html` template
    - Professional section (`#professional`): owner name, job title, photo, bio, skills list, contact info with social links; Bootstrap responsive layout
    - Portfolio section (`#portfolio`): Bootstrap card grid rendering all projects; each card shows title, description, optional image; external links open in new tab (`target="_blank"`)
    - Comments section (`#comments`): display comments newest-first with username and date; show comment form if authenticated, login prompt if not
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 5.1, 5.2, 5.3, 6.1, 6.2_

  - [x] 7.3 Create `login.html` and `register.html` templates
    - Login form with username and password fields, error display
    - Registration form with username, email, password fields, validation error display
    - Both extend `base.html`
    - _Requirements: 3.1, 4.1_

  - [ ]* 7.4 Write property test: Project rendering completeness
    - **Property 1: Project rendering completeness**
    - For random lists of Project dicts, verify rendered HTML contains every title and description, and includes image elements for projects with non-null image_url
    - **Validates: Requirements 2.1, 2.2**

  - [ ]* 7.5 Write property test: Comment ordering and display
    - **Property 7: Comment ordering and display**
    - For random lists of comments with distinct timestamps, verify rendered comment section displays them in descending chronological order with username and date
    - **Validates: Requirements 5.1, 5.2**

- [x] 8. Create custom styles
  - [x] 8.1 Create `static/css/style.css`
    - Add custom styles for professional section, portfolio cards, comment section
    - Ensure styles complement Bootstrap 5 defaults
    - _Requirements: 1.4, 2.4_

- [x] 9. Checkpoint - Ensure all route and template tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement comment and integration tests
  - [ ]* 10.1 Write property test: Comment storage round-trip
    - **Property 8: Comment storage round-trip**
    - For random non-empty comment strings submitted by an authenticated user, verify stored record matches submitted text, username, and has a timestamp
    - **Validates: Requirements 6.3**

  - [ ]* 10.2 Write property test: Empty comment rejection
    - **Property 9: Empty comment rejection**
    - For random whitespace-only strings, verify comment submission is rejected and no record is created
    - **Validates: Requirements 6.4**

  - [ ]* 10.3 Write integration tests for full user flow
    - Test registration → login → comment → logout flow using Flask test client
    - Test navbar section anchors and footer copyright presence
    - Test comment form visibility for authenticated vs unauthenticated visitors
    - Test DB unavailable error handling for comments
    - _Requirements: 4.4, 5.3, 6.1, 6.2, 6.5, 7.1, 7.3_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis with `@settings(max_examples=100)`
- All database operations use parameterized queries to prevent SQL injection
- Flask test client is used for HTTP-level testing (no browser automation needed)
