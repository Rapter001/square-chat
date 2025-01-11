from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the database object
db = SQLAlchemy()

# User model representing a user in the application
class User(UserMixin, db.Model):
    # Unique identifier for the user (primary key)
    id = db.Column(db.Integer, primary_key=True)
    
    # Username field, must be unique and cannot be null
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    
    # Email field, must be unique and cannot be null
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    
    # Password hash stored in the database for user authentication
    password_hash = db.Column(db.String(128))
    
    # Optional field for storing the profile picture's filename (default is 'default.png')
    profile_pic = db.Column(db.String(128), default='default.png')

    # String representation of the user object, useful for debugging
    def __repr__(self):
        return '<User {}>'.format(self.username)

    # Method to set the password hash using the provided plaintext password
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Method to check if a given plaintext password matches the stored password hash
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Message model representing chat messages in a room
class Message(db.Model):
    __tablename__ = 'message'  # Name of the table in the database
    
    # Unique identifier for each message (primary key)
    id = db.Column(db.Integer, primary_key=True)
    
    # Username of the user who sent the message
    username = db.Column(db.String(80), nullable=False)
    
    # Room where the message was sent
    room = db.Column(db.String(80), nullable=False)
    
    # The content of the message
    content = db.Column(db.String(500), nullable=False)
    
    # Timestamp when the message was sent, with the current time as the default
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
