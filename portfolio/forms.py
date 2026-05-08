from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, URL, ValidationError


def url_or_relative_path(form, field):
    """Accept absolute URLs or relative paths starting with /."""
    if not field.data:
        return
    value = field.data.strip()
    if value.startswith("/"):
        return  # Allow relative paths like /static/images/photo.png
    # Fall back to standard URL validation for absolute URLs
    url_validator = URL()
    url_validator(form, field)


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters.")]
    )


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class CommentForm(FlaskForm):
    body = TextAreaField("Comment", validators=[DataRequired(message="Comment cannot be empty.")])


class ProjectForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])
    image_url = StringField("Image URL", validators=[Optional(), url_or_relative_path])
    external_link = StringField("External Link", validators=[Optional(), url_or_relative_path])
    display_order = IntegerField("Display Order", default=0, validators=[Optional()])
