from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, URL


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
    image_url = StringField("Image URL", validators=[Optional(), URL()])
    external_link = StringField("External Link", validators=[Optional(), URL()])
    display_order = IntegerField("Display Order", default=0, validators=[Optional()])
