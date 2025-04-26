import os
import redis
import json
import threading
import time
from datetime import datetime
from flask import Flask, redirect, url_for, render_template, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

# Load environment variables from .env file
load_dotenv()

# Fetch OAuth credentials and DB URL from environment variables
google_oauth_client_id = os.getenv("google_oauth_client_id")
google_oauth_client_secret = os.getenv("google_oauth_client_secret")
database_url = os.getenv("database_url")
secret_key = os.urandom(24)
redis_url = os.getenv("redis_url")
redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

# App setup
app = Flask(__name__)

# Ensure a secret key is set from environment variables for production
app.secret_key = secret_key if secret_key else os.urandom(24)

# PostgreSQL database configuration with connection health checks
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,        # Check if connection is alive before using it
    'pool_recycle': 280,          # Recycle connections after 280 seconds
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy and SocketIO
db = SQLAlchemy(app)
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

# Google OAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=google_oauth_client_id,
    client_secret=google_oauth_client_secret,
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

# Flask-Login setup to handle user sessions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/authorized')
def authorized():
    try:
        token = google.authorize_access_token()
        user_info = google.get('userinfo').json()

        if not user_info or 'id' not in user_info:
            user_info = google.parse_id_token(token)

    except Exception as e:
        return jsonify({'error': 'Login failed or cancelled', 'message': str(e)}), 400

    if not user_info or 'id' not in user_info:
        return jsonify({'error': 'Invalid user data received from Google'}), 400

    session['user_info'] = user_info
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
    # Fetch latest 20 messages from Redis (limit to avoid overwhelming the UI)
    redis_messages = redis_client.lrange('chat_messages', 0, 19)

    # Convert the Redis messages to a list of dictionaries
    message_dicts = [json.loads(message) for message in redis_messages]

    # If Redis doesn't have enough messages, fetch the remaining ones from the DB
    if len(message_dicts) < 20:
        db_messages = Message.query.order_by(Message.timestamp.desc()).limit(20 - len(message_dicts)).all()
        db_message_dicts = [message.to_dict() for message in db_messages]
        # Prepend database messages to the front (since we fetched in reverse order)
        message_dicts = db_message_dicts + message_dicts

    return render_template('chat.html', name=current_user.name, profile_img=current_user.profile_img, messages=message_dicts)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@socketio.on('send_message')
def handle_message(data):
    # Prepare message data
    message_data = {
        'user_id': current_user.id,
        'name': current_user.name,
        'message': data['message'],
        'profile_img': current_user.profile_img,
        'timestamp': datetime.now().isoformat()
    }

    # Push message to Redis (fast, live)
    redis_client.rpush('chat_messages', json.dumps(message_data))

    # Broadcast message to all users live
    emit('message', {
        'name': current_user.name,
        'message': data['message'],
        'profile_img': current_user.profile_img,
        'timestamp': datetime.now().strftime("%B %d, %Y %I:%M:%S %p"),
        'user_local_time': datetime.now().strftime("%B %d, %Y %I:%M:%S %p")
    }, broadcast=True)

def flush_messages_to_db():
    with app.app_context():
        while True:
            # Pop up to 100 messages from Redis
            for _ in range(100):
                raw_message = redis_client.lpop('chat_messages')
                if raw_message is None:
                    break
                message_data = json.loads(raw_message)

                # Check if message already exists in DB (based on timestamp or other identifiers)
                # Assuming that if the message is older than 5 minutes, it's safe to flush
                existing_message = Message.query.filter_by(timestamp=message_data['timestamp']).first()
                if not existing_message:
                    # Store the message in the DB if it's new
                    new_message = Message(
                        user_id=message_data['user_id'],
                        name=message_data['name'],
                        message=message_data['message'],
                        profile_img=message_data['profile_img'],
                        timestamp=datetime.fromisoformat(message_data['timestamp'])
                    )
                    db.session.add(new_message)
            db.session.commit()
            time.sleep(1)

# Run the app with SocketIO
if __name__ == '__main__':
    # Start background thread for flushing messages
    threading.Thread(target=flush_messages_to_db, daemon=True).start()
    # Start the Flask-SocketIO server
    socketio.run(app, host="0.0.0.0", port="5000", debug=False)