import os
import redis
import json
import threading
import time
from datetime import datetime, timezone
from flask import Flask, redirect, url_for, render_template, jsonify, session, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

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

class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_private = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(128), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator = db.relationship('User', backref='created_rooms', foreign_keys=[created_by])
    members = db.relationship('User', secondary='room_members', backref='rooms')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_private': self.is_private,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'creator': {
                'id': self.creator.id,
                'name': self.creator.name,
                'profile_img': self.creator.profile_img
            }
        }

class RoomMember(db.Model):
    __tablename__ = 'room_members'
    
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), primary_key=True)
    user_id = db.Column(db.String(128), db.ForeignKey('users.id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), db.ForeignKey('users.id'), nullable=False)
    room = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    name = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    profile_img = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('messages', lazy=True))
    room_rel = db.relationship('Room', backref=db.backref('messages', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'message': self.message,
            'profile_img': self.profile_img,
            'room_id': self.room,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class RoomJoinRequest(db.Model):
    __tablename__ = 'room_join_requests'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    user_id = db.Column(db.String(128), db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    room = db.relationship('Room', backref=db.backref('join_requests', lazy=True))
    user = db.relationship('User', backref=db.backref('join_requests', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.strftime("%B %d, %Y %I:%M:%S %p"),
            'user_name': self.user.name,
            'user_profile_img': self.user.profile_img
        }

# Create database tables if they don't exist
with app.app_context():
    # Drop all tables to ensure clean slate
    try:
        db.drop_all()
        print("Dropped all tables")
    except Exception as e:
        print(f"Error dropping tables: {str(e)}")
    
    # Create all tables
    try:
        db.create_all()
        print("Created all tables successfully")
        
        # Verify tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Existing tables: {tables}")
        
        # Verify columns in rooms table
        if 'rooms' in tables:
            columns = [col['name'] for col in inspector.get_columns('rooms')]
            print(f"Columns in rooms table: {columns}")
            
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        raise e

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
    return render_template('index.html', user=current_user)

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
    # Get room_id from query parameters, default to None (public chat)
    room_id = request.args.get('room_id')
    
    if room_id:
        room = Room.query.get(room_id)
        if not room:
            return redirect(url_for('rooms'))
        
        # Check if user is member of private room
        if room.is_private:
            # If user is not a member, redirect to password prompt
            if current_user not in room.members:
                return redirect(url_for('password_prompt', room_id=room_id))
        
        # Fetch messages for specific room
        messages = Message.query.filter_by(room=room_id).order_by(Message.id.desc()).limit(20).all()
        message_dicts = [message.to_dict() for message in messages]
        
        return render_template('chat.html', 
                             user=current_user,
                             messages=message_dicts,
                             room=room.to_dict())
    else:
        # Fetch public messages (where room_id is None)
        messages = Message.query.filter_by(room=None).order_by(Message.id.desc()).limit(20).all()
        message_dicts = [message.to_dict() for message in messages]
        
        return render_template('chat.html', 
                             user=current_user,
                             messages=message_dicts)

@app.route('/rooms')
@login_required
def rooms():
    # Get all public rooms
    public_rooms = Room.query.filter_by(is_private=False).all()
    
    # Get private rooms where user is a member
    private_rooms = Room.query.filter_by(is_private=True).join(
        Room.members
    ).filter(
        User.id == current_user.id
    ).all()

    return render_template('rooms.html', 
                         public_rooms=public_rooms, 
                         private_rooms=private_rooms,
                         user=current_user,
                         name=current_user.name,
                         profile_img=current_user.profile_img)

@app.route('/create_room', methods=['POST'])
@login_required
def create_room():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Room name is required'}), 400

        room = Room(
            name=data.get('name'),
            description=data.get('description', ''),
            is_private=data.get('is_private', False),
            created_by=current_user.id
        )
        
        db.session.add(room)
        db.session.flush()  # This ensures room.id is available
        
        # Add creator as member
        room.members.append(current_user)
        db.session.commit()

        # Return room data with creator info
        room_data = room.to_dict()
        room_data['is_member'] = True  # Add this flag to indicate creator is a member
        return jsonify(room_data)
        
    except Exception as e:
        print(f"Error creating room: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create room'}), 500

@app.route('/verify_room_password/<int:room_id>', methods=['POST'])
@login_required
def verify_room_password(room_id):
    try:
        data = request.get_json()
        password = data.get('password')
        
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        if room.password == password:  # Simple comparison for now
            # Add user to room members
            if current_user not in room.members:
                room.members.append(current_user)
                db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Incorrect password'}), 401
            
    except Exception as e:
        print(f"Error verifying password: {str(e)}")
        return jsonify({'error': 'Failed to verify password'}), 500

@app.route('/join_room/<int:room_id>', methods=['POST'])
@login_required
def join_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    if current_user not in room.members:
        room.members.append(current_user)
        db.session.commit()
    
    return jsonify({'success': True})

@socketio.on('join')
def on_join(data):
    room_id = data.get('room_id')
    if room_id:
        room = Room.query.get(room_id)
        if room and (not room.is_private or current_user in room.members):
            join_room(str(room_id))
            emit('status', {'msg': f'{current_user.name} has joined the room.'}, room=str(room_id))
            # Send recent messages to the user
            messages = Message.query.filter_by(room=room_id).order_by(Message.id.desc()).limit(20).all()
            for message in reversed(messages):
                emit('message', {
                    'id': message.id,
                    'name': message.name,
                    'message': message.message,
                    'profile_img': message.profile_img,
                    'room_id': room_id,
                    'created_at': message.created_at.isoformat() if message.created_at else None
                }, room=request.sid)  # Send only to the joining user

@socketio.on('leave')
def on_leave(data):
    room_id = data.get('room_id')
    if room_id:
        leave_room(str(room_id))
        emit('status', {'msg': f'{current_user.name} has left the room.'}, room=str(room_id))

@socketio.on('send_message')
def handle_message(data):
    try:
        room_id = data.get('room_id')
        message_text = data.get('message')
        
        if not message_text:
            return
        
        # Check if room exists and user has access
        if room_id:
            room = Room.query.get(room_id)
            if not room or (room.is_private and current_user not in room.members):
                return
            room_value = room_id
        else:
            room_value = None
        
        # Create message in database first
        new_message = Message(
            user_id=current_user.id,
            room=room_value,
            name=current_user.name,
            message=message_text,
            profile_img=current_user.profile_img,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(new_message)
        db.session.commit()
        
        # Prepare message data for broadcast
        message_data = {
            'id': new_message.id,
            'name': current_user.name,
            'message': message_text,
            'profile_img': current_user.profile_img,
            'room_id': room_id,
            'created_at': new_message.created_at.isoformat()
        }
        
        # Broadcast message to room or all users
        if room_id:
            emit('message', message_data, room=str(room_id))
        else:
            emit('message', message_data, broadcast=True)
        
    except Exception as e:
        print(f"Error handling message: {str(e)}")
        emit('error', {'message': 'Failed to send message'})

def flush_messages_to_db():
    with app.app_context():
        while True:
            try:
                # Process messages for each room
                rooms = Room.query.all()
                room_ids = [str(room.id) for room in rooms] + [None]
                
                for room_id in room_ids:
                    redis_key = f'chat_messages:{room_id}' if room_id else 'chat_messages'
                    for _ in range(100):
                        raw_message = redis_client.lpop(redis_key)
                        if raw_message is None:
                            break
                        message_data = json.loads(raw_message)
                        
                        # Check if message already exists
                        existing_message = Message.query.filter_by(
                            user_id=message_data['user_id'],
                            room=message_data['room'],
                            message=message_data['message'],
                            created_at=datetime.fromisoformat(message_data['created_at'])
                        ).first()
                        
                        if not existing_message:
                            new_message = Message(
                                user_id=message_data['user_id'],
                                room=message_data['room'],
                                name=message_data['name'],
                                message=message_data['message'],
                                profile_img=message_data['profile_img'],
                                created_at=datetime.fromisoformat(message_data['created_at'])
                            )
                            db.session.add(new_message)
                db.session.commit()
            except Exception as e:
                print(f"Error in flush_messages_to_db: {str(e)}")
                db.session.rollback()
            time.sleep(1)

@app.route('/password_prompt/<int:room_id>')
@login_required
def password_prompt(room_id):
    room = Room.query.get(room_id)
    if not room or not room.is_private:
        return redirect(url_for('rooms'))
    return render_template('password_prompt.html', room=room.to_dict())

@app.route('/request_join_room/<int:room_id>', methods=['POST'])
@login_required
def request_join_room(room_id):
    try:
        data = request.get_json()
        message = data.get('message')
        
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        if not room.is_private:
            return jsonify({'error': 'Cannot request to join public room'}), 400
        
        if current_user in room.members:
            return jsonify({'error': 'You are already a member of this room'}), 400
        
        # Check if user already has a pending request
        existing_request = RoomJoinRequest.query.filter_by(
            room_id=room_id,
            user_id=current_user.id,
            status='pending'
        ).first()
        
        if existing_request:
            return jsonify({'error': 'You already have a pending request for this room'}), 400
        
        # Create new join request
        join_request = RoomJoinRequest(
            room_id=room_id,
            user_id=current_user.id,
            message=message
        )
        
        db.session.add(join_request)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error creating join request: {str(e)}")
        return jsonify({'error': 'Failed to create join request'}), 500

@app.route('/get_join_requests')
@login_required
def get_join_requests():
    try:
        # Get rooms where current user is the creator
        rooms = Room.query.filter_by(created_by=current_user.id).all()
        room_ids = [room.id for room in rooms]
        
        # Get pending join requests for these rooms
        join_requests = RoomJoinRequest.query.filter(
            RoomJoinRequest.room_id.in_(room_ids),
            RoomJoinRequest.status == 'pending'
        ).all()
        
        return jsonify({
            'requests': [request.to_dict() for request in join_requests]
        })
        
    except Exception as e:
        print(f"Error getting join requests: {str(e)}")
        return jsonify({'error': 'Failed to get join requests'}), 500

@app.route('/handle_join_request/<int:request_id>', methods=['POST'])
@login_required
def handle_join_request(request_id):
    try:
        data = request.get_json()
        action = data.get('action')  # 'approve' or 'reject'
        
        join_request = RoomJoinRequest.query.get(request_id)
        if not join_request:
            return jsonify({'error': 'Join request not found'}), 404
        
        # Check if current user is the room creator
        room = Room.query.get(join_request.room_id)
        if room.created_by != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if action == 'approve':
            # Add user to room members
            user = User.query.get(join_request.user_id)
            if user not in room.members:
                room.members.append(user)
            join_request.status = 'approved'
        elif action == 'reject':
            join_request.status = 'rejected'
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error handling join request: {str(e)}")
        return jsonify({'error': 'Failed to handle join request'}), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Run the app with SocketIO
if __name__ == '__main__':
    # Start background thread for flushing messages
    threading.Thread(target=flush_messages_to_db, daemon=True).start()
    # Start the Flask-SocketIO server
    socketio.run(app, host="0.0.0.0", port="5000", debug=True)