# Import necessary modules for the application
import json
import os
from datetime import datetime
from flask import Flask, redirect, url_for, session, render_template
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# App setup
app = Flask(__name__)
# Secret key used by Flask for session management and security (ensure it's kept private)
app.secret_key = "%*pSoa%E33CjxbOOq2^2StP886NeKINI$mRpMgTtTVJkz#@u6vioSp8iWV#j5e5A35k3GL20cG^cgDpl@SR$81XWQ1MjFBN*AJj6nwKF9KF7hy2YuagNNbHV2ku2Tja1"
# Initialize SocketIO for real-time communication
socketio = SocketIO(app)

# Fetch OAuth credentials from environment variables (from Docker or .env)
google_oauth_client_id = os.getenv("google_oauth_client_id")
google_oauth_client_secret = os.getenv("google_oauth_client_secret")

# File paths for storing user data and messages (stored as JSON)
USER_DATA_FILE = "data/users.json"
MESSAGES_FILE = "data/messages.json"

# Function to initialize the data folder and JSON files for users and messages
def initialize_json_files():
    # Check and create the data folder if it doesn't exist
    if not os.path.exists("data"):
        os.makedirs("data")

    # Initialize users.json if it doesn't exist
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "w") as f:
            json.dump({}, f, indent=4)

    # Initialize messages.json if it doesn't exist
    if not os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "w") as f:
            json.dump([], f, indent=4)

# Call the initialization function to ensure the files exist
initialize_json_files()

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

# User model class to represent user data and handle loading/saving to JSON
class User(UserMixin):
    def __init__(self, id_, name, email, profile_img):
        self.id = id_
        self.name = name
        self.email = email
        self.profile_img = profile_img

    @staticmethod
    def get(user_id):
        # Fetch user data from users.json by user ID
        with open(USER_DATA_FILE, "r") as f:
            users = json.load(f)
        user_data = users.get(user_id)
        if user_data:
            return User(
                id_=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
                profile_img=user_data["profile_img"]
            )
        return None

    @staticmethod
    def save(user):
        # Save user data to users.json
        with open(USER_DATA_FILE, "r") as f:
            users = json.load(f)
        users[user.id] = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "profile_img": user.profile_img
        }
        with open(USER_DATA_FILE, "w") as f:
            json.dump(users, f, indent=4)

# Login manager user loader function
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

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
    # Once Google returns the token, fetch user information
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    session['google_token'] = token  # Store the token in the session

    # Create a new user object from the retrieved data and save it
    user = User(
        id_=user_info['id'],
        name=user_info['name'],
        email=user_info['email'],
        profile_img=user_info['picture']
    )
    User.save(user)  # Save user data to JSON
    login_user(user)  # Log the user in

    return redirect(url_for('chat'))  # Redirect to the chat page

@app.route('/chat')
@login_required
def chat():
    # Load and display chat messages from the JSON file
    try:
        with open(MESSAGES_FILE, "r") as file:
            messages = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        messages = []  # If the file doesn't exist or is empty, use an empty list

    return render_template('chat.html', name=current_user.name, profile_img=current_user.profile_img, messages=messages)

@app.route('/logout')
@login_required
def logout():
    # Log the user out and redirect to the home page
    logout_user()
    return redirect(url_for('home'))

# SocketIO event for handling incoming chat messages
@socketio.on('send_message')
def handle_message(data):
    # Load current chat messages
    try:
        with open(MESSAGES_FILE, "r") as file:
            messages = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        messages = []

    # Get current server time in a human-readable format
    server_time = datetime.now().strftime("%B %d, %Y %I:%M:%S %p")
    # Get the user's local time in a similar format (can be adjusted based on user timezone)
    user_local_time = datetime.now().strftime("%B %d, %Y %I:%M:%S %p")

    # Prepare the message data with timestamp information
    message_data = {
        'name': current_user.name,
        'message': data['message'],
        'profile_img': current_user.profile_img,
        'timestamp': server_time,
        'user_local_time': user_local_time
    }
    messages.append(message_data)

    # Save the updated messages list back to the JSON file
    with open(MESSAGES_FILE, "w") as file:
        json.dump(messages, file, indent=4)

    # Emit the new message to all connected clients
    emit('message', message_data, broadcast=True)

# Run the app with SocketIO support
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port="5000", debug=True, allow_unsafe_werkzeug=True)