"""Route handlers for the portfolio site."""

import json
import sqlite3

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from portfolio.auth import admin_required, authenticate_user, register_user
from portfolio.db import (
    create_comment,
    create_project,
    delete_project,
    get_all_comments,
    get_all_projects,
    get_project_by_id,
    update_project,
)
from portfolio.forms import CommentForm, LoginForm, ProjectForm, RegistrationForm


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

    # ── Admin Portfolio Management Routes ─────────────────────────────

    @app.route("/admin/projects")
    @admin_required
    def admin_projects():
        projects = get_all_projects()
        return render_template("admin_projects.html", projects=projects)

    @app.route("/admin/projects/create", methods=["GET", "POST"])
    @admin_required
    def admin_create_project():
        form = ProjectForm()
        if form.validate_on_submit():
            create_project(
                title=form.title.data,
                description=form.description.data,
                image_url=form.image_url.data or None,
                external_link=form.external_link.data or None,
                display_order=form.display_order.data or 0,
            )
            flash("Project created successfully.", "success")
            return redirect(url_for("admin_projects"))
        return render_template("admin_project_form.html", form=form, editing=False)

    @app.route("/admin/projects/<int:id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit_project(id):
        project = get_project_by_id(id)
        if project is None:
            abort(404)
        form = ProjectForm()
        if form.validate_on_submit():
            result = update_project(
                project_id=id,
                title=form.title.data,
                description=form.description.data,
                image_url=form.image_url.data or None,
                external_link=form.external_link.data or None,
                display_order=form.display_order.data or 0,
            )
            if result is None:
                abort(404)
            flash("Project updated successfully.", "success")
            return redirect(url_for("admin_projects"))
        elif request.method == "GET":
            form.title.data = project["title"]
            form.description.data = project["description"]
            form.image_url.data = project["image_url"]
            form.external_link.data = project["external_link"]
            form.display_order.data = project["display_order"]
        return render_template("admin_project_form.html", form=form, editing=True)

    @app.route("/admin/projects/<int:id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_project(id):
        result = delete_project(id)
        if not result:
            abort(404)
        flash("Project deleted successfully.", "success")
        return redirect(url_for("admin_projects"))

    @app.route("/admin/projects/export")
    @admin_required
    def admin_export_projects():
        projects = get_all_projects()
        export_data = [
            {
                "title": p["title"],
                "description": p["description"],
                "image_url": p["image_url"],
                "external_link": p["external_link"],
                "display_order": p["display_order"],
            }
            for p in projects
        ]
        json_str = json.dumps(export_data, indent=2)
        return app.response_class(
            json_str,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=projects.json"},
        )

    @app.route("/admin/projects/import", methods=["GET", "POST"])
    @admin_required
    def admin_import_projects():
        if request.method == "POST":
            file = request.files.get("file")
            if not file or file.filename == "":
                flash("No file selected.", "error")
                return redirect(url_for("admin_import_projects"))

            try:
                data = json.loads(file.read().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                flash("Invalid JSON file.", "error")
                return redirect(url_for("admin_import_projects"))

            if not isinstance(data, list):
                flash("Invalid JSON file.", "error")
                return redirect(url_for("admin_import_projects"))

            # Validate all entries before creating any
            invalid_entries = []
            for i, entry in enumerate(data):
                if not isinstance(entry, dict):
                    invalid_entries.append(i)
                    continue
                title = entry.get("title")
                description = entry.get("description")
                if not title or not isinstance(title, str) or not title.strip():
                    invalid_entries.append(i)
                elif not description or not isinstance(description, str) or not description.strip():
                    invalid_entries.append(i)

            if invalid_entries:
                flash(
                    f"Invalid entries at positions: {', '.join(str(i) for i in invalid_entries)}. "
                    "Each entry must have a non-empty title and description.",
                    "error",
                )
                return redirect(url_for("admin_import_projects"))

            # All valid — create projects
            for entry in data:
                create_project(
                    title=entry["title"],
                    description=entry["description"],
                    image_url=entry.get("image_url"),
                    external_link=entry.get("external_link"),
                    display_order=entry.get("display_order", 0),
                )

            flash(f"Successfully imported {len(data)} project(s).", "success")
            return redirect(url_for("admin_projects"))

        return render_template("admin_import.html")
