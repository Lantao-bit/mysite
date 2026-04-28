# Personal Portfolio Site

A single-page personal portfolio website built with Flask, SQLAlchemy, and Bootstrap 5. Showcases professional information, project portfolio, and a visitor comment system with user authentication.

## Features

- Professional profile section with bio, skills, and contact links
- Project portfolio displayed as a Bootstrap card grid
- User registration and login with secure password hashing
- Authenticated visitors can leave comments
- Comments displayed newest-first in a sidebar layout
- SQLite database with Flask-Migrate for schema versioning

## Tech Stack

- **Backend:** Python 3.14, Flask 3.x, SQLAlchemy, Flask-Login, Flask-WTF
- **Frontend:** Bootstrap 5 (CDN), Jinja2 templates
- **Database:** SQLite with Flask-Migrate / Alembic
- **Testing:** pytest, Hypothesis

## Quick Start

```bash
# Clone the repo
git clone <your-repo-url>
cd mysite

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r portfolio/requirements.txt

# Run the app
flask --app portfolio.app run --debug
```

Open http://127.0.0.1:5000 in your browser.

## Database Migrations

```bash
# Initialize (first time only)
export FLASK_APP=portfolio.app
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

For subsequent schema changes:

```bash
flask db migrate -m "describe your change"
flask db upgrade
```

## Running Tests

```bash
python3 -m pytest tests/ -v
```

## Project Structure

```
portfolio/
├── app.py              # Flask app factory
├── models.py           # SQLAlchemy models (User, Project, Comment)
├── db.py               # Data access layer
├── auth.py             # Authentication logic
├── routes.py           # Route handlers
├── forms.py            # WTForms definitions
├── templates/          # Jinja2 templates
├── static/             # CSS and images
└── requirements.txt    # Python dependencies
tests/
└── test_db_and_auth.py # Test suite
```

## Deployment (PythonAnywhere)

1. Upload the `portfolio/` directory to `~/mysite/`
2. Create a virtualenv and install dependencies
3. Configure the WSGI file to import `create_app()` from `portfolio.app`
4. Set `SECRET_KEY` and `DATABASE_PATH` environment variables
5. Map `/static` to `~/mysite/portfolio/static`
6. Reload the web app

## License

MIT
