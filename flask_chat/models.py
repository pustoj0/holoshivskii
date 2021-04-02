from flask_login import UserMixin
from datetime import datetime
from flask_chat import db


class User(UserMixin, db.Model):
    """ User model """

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    hashed_pswd = db.Column(db.String(), nullable=False)
    comments = db.relationship('Comment', backref='author', lazy=True)
    role = db.Column(db.String, default='user')

    def is_admin(self):
        return self.role

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    room = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"Comment('{self.body}', '{self.timestamp}')"

class Room(db.Model):
    __tablename__ = "rooms"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), unique=True, nullable=False)
    admin_id = db.Column(db.Integer,  db.ForeignKey('users.id'), nullable=False)


class RoomUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer,  db.ForeignKey('rooms.id'), nullable=False)
    user_id = db.Column(db.Integer,  db.ForeignKey('users.id'), nullable=False)
