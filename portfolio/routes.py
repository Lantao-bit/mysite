"""Route handlers for the portfolio site."""

import sqlite3

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from portfolio.auth import authenticate_user, register_user
from portfolio.db import create_comment, get_all_comments, get_all_projects
from portfolio.forms import CommentForm, LoginForm, RegistrationForm


def register_routes(app):
    """Register all route handlers on the Flask app."""

    @app.route("/")
    def index():
        projects = get_all_projects()
        comments = get_all_comments()
        form = CommentForm()
        return render_template(
            "index.html", projects=projects, comments=comments, form=form
        )

    @app.route("/register", methods=["GET", "POST"])
    def register():
        form = RegistrationForm()
        if form.validate_on_submit():
            user, error = register_user(
                form.username.data, form.email.data, form.password.data
            )
            if error:
                flash(error, "error")
                return render_template("register.html", form=form)
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user, error = authenticate_user(
                form.username.data, form.password.data
            )
            if error:
                flash(error, "error")
                return render_template("login.html", form=form)
            login_user(user)
            return redirect(url_for("index"))
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))

    @app.route("/comment", methods=["POST"])
    @login_required
    def add_comment():
        form = CommentForm()
        if form.validate_on_submit():
            body = form.body.data
            if not body or not body.strip():
                flash("Comment cannot be empty.", "error")
                return redirect(url_for("index") + "#comments")
            try:
                create_comment(
                    username=current_user.username,
                    body=body.strip(),
                    user_id=current_user.id,
                )
            except sqlite3.OperationalError:
                flash(
                    "Could not save your comment. Please try again later.",
                    "error",
                )
                return redirect(url_for("index") + "#comments")
            return redirect(url_for("index") + "#comments")
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("index") + "#comments")
