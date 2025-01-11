import json
import os
from datetime import datetime
from flask import Flask, redirect, url_for, session, render_template
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

load_dotenv()

# App setup
app = Flask(__name__)
app.secret_key = "grgrtkyrtty547ujhd"
socketio = SocketIO(app)

# File to store user data and messages
USER_DATA_FILE = "data/users.json"
MESSAGES_FILE = "data/messages.json"

# Function to initialize the JSON files
def initialize_json_files():
    # Check and initialize users.json
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "w") as f:
            json.dump({}, f, indent=4)

    # Check and initialize messages.json
    if not os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "w") as f:
            json.dump([], f, indent=4)

# Call the initialization function at the start
initialize_json_files()

# Google OAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("google_oauth_client_id"),
    client_secret=os.getenv("google_oauth_client_secret"),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'consent',
    },
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home'

# User model
class User(UserMixin):
    def __init__(self, id_, name, email, profile_img):
        self.id = id_
        self.name = name
        self.email = email
        self.profile_img = profile_img

    @staticmethod
    def get(user_id):
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

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/authorized')
def authorized():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    session['google_token'] = token

    # Create a user object and save it to JSON
    user = User(
        id_=user_info['id'],
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
    try:
        with open(MESSAGES_FILE, "r") as file:
            messages = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        messages = []
    
    return render_template('chat.html', name=current_user.name, profile_img=current_user.profile_img, messages=messages)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@socketio.on('send_message')
def handle_message(data):
    try:
        with open(MESSAGES_FILE, "r") as file:
            messages = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        messages = []

    # Get current server time with AM/PM format
    server_time = datetime.now().strftime("%B %d, %Y %I:%M:%S %p")  # Month Day, Year Hour:Minute:Second AM/PM
    # User's local time with AM/PM format
    user_local_time = datetime.now().strftime("%B %d, %Y %I:%M:%S %p")  # Month Day, Year Hour:Minute:Second AM/PM

    message_data = {
        'name': current_user.name,
        'message': data['message'],
        'profile_img': current_user.profile_img,
        'timestamp': server_time,
        'user_local_time': user_local_time
    }
    messages.append(message_data)

    with open(MESSAGES_FILE, "w") as file:
        json.dump(messages, file, indent=4)

    emit('message', message_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port="5000", debug=False)