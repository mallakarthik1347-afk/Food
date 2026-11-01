import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from foodMenuWebsite.config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Ensure the upload directory exists
os.makedirs(os.path.join(app.root_path, 'static', 'profile_pics'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = 'info'

from foodMenuWebsite import routes
