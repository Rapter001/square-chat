# Import necessary modules for the application
import os
from datetime import datetime
from flask import Flask, redirect, url_for, render_template, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

# Load environment variables from .env file (for local development)
load_dotenv()

# Fetch OAuth credentials from environment variables (from Docker or .env)
google_oauth_client_id = os.getenv("google_oauth_client_id")
google_oauth_client_secret = os.getenv("google_oauth_client_secret")
database_url = os.getenv("database_url")

# App setup
app = Flask(__name__)
# Secret key used by Flask for session management and security (ensure it's kept private)
app.secret_key = "%*pSoa%E33CjxbOOq2"

# PostgreSQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize SocketIO for real-time communication
socketio = SocketIO(app)

# Define database models
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.String(128), primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    profile_img = db.Column(db.String(256))
    
    @staticmethod
    def get(user_id):
        return User.query.get(user_id)
    
    @staticmethod
    def save(user):
        existing_user = User.query.get(user.id)
        if existing_user:
            existing_user.name = user.name
            existing_user.email = user.email
            existing_user.profile_img = user.profile_img
        else:
            db.session.add(user)
        db.session.commit()

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    profile_img = db.Column(db.String(256))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    
    user = db.relationship('User', backref=db.backref('messages', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'message': self.message,
            'profile_img': self.profile_img,
            'timestamp': self.timestamp.strftime("%B %d, %Y %I:%M:%S %p"),
            'user_local_time': self.timestamp.strftime("%B %d, %Y %I:%M:%S %p")
        }

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Google OAuth Setup (using environment variables for credentials)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("google_oauth_client_id"),  # Get client ID from environment variable
    client_secret=os.getenv("google_oauth_client_secret"),  # Get client secret from environment variable
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={
        'scope': 'openid email profile',  # Request specific OAuth scopes
        'prompt': 'consent',  # Always prompt for consent
    },
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

# Flask-Login setup to handle user sessions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home'  # Redirect to home if not logged in

# Login manager user loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Routes for different app views
@app.route('/')
def home():
    # If the user is authenticated, redirect to the chat page
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('index.html')  # Render the index page for unauthenticated users

@app.route('/login')
def login():
    # Initiate OAuth login process
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/authorized')
def authorized():
    try:
        google.authorize_access_token()
    except Exception as e:
        # Could log e here for debug
        return jsonify({'error': 'Login cancelled or failed', 'message': str(e)}), 400

    user_info = google.get('userinfo').json()

    if not user_info or 'id' not in user_info:
        return jsonify({'error': 'Login cancelled or invalid response'}), 400

    user = User(
        id=user_info['id'],
        name=user_info['name'],
        email=user_info['email'],
        profile_img=user_info['picture']
    )
    User.save(user)
    login_user(user)

    return redirect(url_for('chat'))

@app.route('/chat')
@login_required
def chat():
    # Load and display chat messages from the database
    messages = Message.query.order_by(Message.timestamp).all()
    message_dicts = [message.to_dict() for message in messages]
    
    return render_template('chat.html', name=current_user.name, profile_img=current_user.profile_img, messages=message_dicts)

@app.route('/logout')
@login_required
def logout():
    # Log the user out and redirect to the home page
    logout_user()
    return redirect(url_for('home'))

# SocketIO event for handling incoming chat messages
@socketio.on('send_message')
def handle_message(data):
    # Create and save new message to the database
    new_message = Message(
        user_id=current_user.id,
        name=current_user.name,
        message=data['message'],
        profile_img=current_user.profile_img,
        timestamp=datetime.now()
    )
    db.session.add(new_message)
    db.session.commit()

    # Prepare the message data with timestamp information
    message_data = new_message.to_dict()

    # Emit the new message to all connected clients
    emit('message', message_data, broadcast=True)

# Run the app with SocketIO support
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port="5000", debug=False, allow_unsafe_werkzeug=True)