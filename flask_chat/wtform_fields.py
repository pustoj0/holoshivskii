from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError

from passlib.hash import pbkdf2_sha256
from flask_chat.models import User


def invalid_credentials(form, field):
    """ Username and password checker """

    password = field.data
    username = form.username.data

    # Check username is invalid
    user_data = User.query.filter_by(username=username).first()
    if user_data is None:
        raise ValidationError("Username or password is incorrect")

    # Check password in invalid
    elif not pbkdf2_sha256.verify(password, user_data.hashed_pswd):
        raise ValidationError("Username or password is incorrect")


class RegistrationForm(FlaskForm):
    """ Registration form"""

    username = StringField('username', validators=[InputRequired(message="Username required"), Length(min=4, max=25, message="Username must be between 4 and 25 characters")])
    password = PasswordField('password', validators=[InputRequired(message="Password required"), Length(min=4, max=25, message="Password must be between 4 and 25 characters")])
    confirm_pswd = PasswordField('confirm_pswd', validators=[InputRequired(message="Password required"), EqualTo('password', message="Passwords must match")])

    def validate_username(self, username):
        return
        user_object = User.query.filter_by(username=username.data).first()
        if user_object:
            raise ValidationError("Username already exists. Select a different username.")

class RoomForm(FlaskForm):
    """ Room form """

    roomname = StringField('roomname', validators=[InputRequired(message="Room name required"), Length(max=25, message="Room name must be less than 25 characters")])

class AddFriendForm(FlaskForm):
    """ Room form """

    friend = StringField('friendname', validators=[InputRequired(message="Friend name required")])

class LoginForm(FlaskForm):
    """ Login form """

    username = StringField('username', validators=[InputRequired(message="Username required")])
    password = PasswordField('password', validators=[InputRequired(message="Password required"), invalid_credentials])

class AdminUserCreateForm(FlaskForm):

    username = StringField('username', validators=[InputRequired(message="Username required"), Length(min=4, max=25,                                                                                                  message="Username must be between 4 and 25 characters")])
    password = PasswordField('password', validators=[InputRequired(message="Password required"), Length(min=4, max=25,                                                                                                    message="Password must be between 4 and 25 characters")])
    role = SelectField(u'Role',  choices=[('admin', 'Admin'), ('user', 'User')])

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Choose a different one, please.')



class AdminUserUpdateForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(message="Username required"), Length(min=4, max=25,                                                                                       message="Username must be between 4 and 25 characters")])
    role = SelectField(u'Role', choices=[('admin', 'Admin'), ('user', 'User')])