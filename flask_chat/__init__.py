from flask import Flask

from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import os


csrf = CSRFProtect()

# Configure app
app  = Flask(__name__)
app.config['SECRET_KEY'] = 'Thisisasecret!'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' \
                            + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = False

csrf.init_app(app)

db = SQLAlchemy(app)

socketio = SocketIO(app, manage_session=False)

from flask_chat import routes