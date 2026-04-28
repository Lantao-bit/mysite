---
inclusion: always
---

# Project Overview

This is a personal portfolio website built with Flask, SQLAlchemy, and Bootstrap 5.

## Tech Stack
- Python 3.14 / Flask 3.x
- SQLAlchemy via Flask-SQLAlchemy (models in `portfolio/models.py`)
- Flask-Migrate / Alembic for database migrations
- SQLite for persistence
- Flask-Login for authentication
- Flask-WTF + WTForms for forms and CSRF
- Werkzeug for password hashing
- Bootstrap 5 (CDN) for frontend
- Jinja2 templates

## Project Structure
- `portfolio/app.py` — Flask app factory, config, Flask-Login + Migrate setup
- `portfolio/models.py` — SQLAlchemy models: User, Project, Comment
- `portfolio/db.py` — Data access functions (wraps SQLAlchemy queries, returns dicts)
- `portfolio/auth.py` — Registration and login logic, Flask-Login User class
- `portfolio/routes.py` — All route handlers registered via `register_routes(app)`
- `portfolio/forms.py` — WTForms: RegistrationForm, LoginForm, CommentForm
- `portfolio/templates/` — Jinja2 templates extending `base.html`
- `portfolio/static/` — CSS and images
- `tests/` — pytest test suite

## Key Patterns
- `db.py` functions return `dict` (not ORM objects) to keep routes/auth decoupled from SQLAlchemy
- `create_user()` raises `sqlite3.IntegrityError` on duplicates for backward compatibility
- App factory pattern: `create_app(config=None)`
- Single-page layout with anchor-based scrolling (#professional, #portfolio, #comments)
