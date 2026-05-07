"""Flask app factory and configuration."""

import os

from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from portfolio.db import get_user_by_id, init_db
from portfolio.models import db as sa_db


migrate = Migrate()
csrf = CSRFProtect()


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # SQLAlchemy database URI
    db_path = os.environ.get("DATABASE_PATH", "portfolio.db")
    if config and "DATABASE_PATH" in config:
        db_path = config["DATABASE_PATH"]
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.abspath(db_path)}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Keep legacy key for any code that still references it
    app.config["DATABASE_PATH"] = db_path

    # Admin user identification
    app.config["ADMIN_EMAIL"] = os.environ.get("ADMIN_EMAIL", "lantao.yang@outlook.com")

    if config:
        app.config.update(config)

    # Initialize SQLAlchemy + Migrate
    init_db(app)
    migrate.init_app(app, sa_db)
    csrf.init_app(app)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        from portfolio.auth import User as AuthUser

        row = get_user_by_id(int(user_id))
        if row is None:
            return None
        return AuthUser.from_db(row)

    # Register route handlers
    from portfolio.routes import register_routes

    register_routes(app)

    # Custom error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500

    return app
