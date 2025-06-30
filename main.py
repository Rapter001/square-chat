import os
from datetime import datetime, timezone
from flask import Flask, redirect, url_for, render_template, jsonify, session, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
import secrets
import string

# Load environment variables from .env file
load_dotenv()

# Fetch OAuth credentials and DB URL from environment variables
google_oauth_client_id = os.getenv("google_oauth_client_id")
google_oauth_client_secret = os.getenv("google_oauth_client_secret")
database_url = os.getenv("database_url")
secret_key = os.getenv("secret_key")

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
    invite_code = db.Column(db.String(32), unique=True)  # Store unique invite code
    created_by = db.Column(db.String(128), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator = db.relationship('User', backref='created_rooms', foreign_keys=[created_by])
    members = db.relationship('User', secondary='room_members', backref='rooms')

    def generate_invite_code(self):
        # Generate a random 8-character code
        alphabet = string.ascii_letters + string.digits
        self.invite_code = ''.join(secrets.choice(alphabet) for _ in range(8))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_private': self.is_private,
            'invite_code': self.invite_code,
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

# Create database tables if they don't exist
with app.app_context():
    try:
        # Create tables if they don't exist
        db.create_all()
        print("Database tables initialized successfully")

        # Verify tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Existing tables: {tables}")

        # Verify database setup
        def verify_database_setup():
            print("\n=== Database Verification ===")
            try:
                # Get all table names using inspector
                inspector = db.inspect(db.engine)
                tables = inspector.get_table_names()
                print("Available tables:", tables)
                print("===========================\n")

            except Exception as e:
                print(f"Error during database verification: {str(e)}")
                print("===========================\n")

        # Call this after db.create_all()
        verify_database_setup()

    except Exception as e:
        print(f"Error initializing database: {str(e)}")
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
    return db.session.get(User, user_id)

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

    # Store the next URL in the session
    next_url = request.args.get('next')
    if next_url:
        session['next_url'] = next_url

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

    # Handle profile picture with better validation
    profile_img = user_info.get('picture')
    if not profile_img or not isinstance(profile_img, str) or not profile_img.startswith('http'):
        profile_img = url_for('static', filename='img/default-profile.png')

    user = User(
        id=user_info['id'],
        name=user_info['name'],
        email=user_info['email'],
        profile_img=profile_img
    )
    User.save(user)
    login_user(user)

    # Get the stored next URL from session
    next_url = session.pop('next_url', None)

    if next_url:
        # If it's a private room invite link
        if '/join/' in next_url:
            invite_code = next_url.split('/join/')[-1]
            return redirect(url_for('join_by_invite', invite_code=invite_code))
        return redirect(next_url)

    return redirect(url_for('chat'))

@app.route('/chat')
@login_required
def chat():
    # Get room_id from query parameters, default to None (public chat)
    room_id = request.args.get('room_id')

    if room_id:
        try:
            room_id = int(room_id)
            room = db.session.get(Room, room_id)
            if not room:
                return redirect(url_for('rooms'))

            # Check if user is member of private room
            if room.is_private and current_user not in room.members:
                return redirect(url_for('rooms'))

            # Fetch messages for specific room
            messages = db.session.query(Message).filter_by(room=room_id).order_by(Message.created_at.asc()).all()
            message_dicts = [message.to_dict() for message in messages]

            # Get room data with members
            room_data = room.to_dict()
            room_data['members'] = [{
                'id': member.id,
                'name': member.name,
                'profile_img': member.profile_img
            } for member in room.members]

            return render_template('chat.html',
                                user=current_user,
                                messages=message_dicts,
                                room=room_data)
        except (ValueError, TypeError):
            return redirect(url_for('rooms'))
    else:
        # Fetch public messages (where room_id is None)
        messages = db.session.query(Message).filter_by(room=None).order_by(Message.created_at.asc()).all()
        message_dicts = [message.to_dict() for message in messages]

        return render_template('chat.html',
                            user=current_user,
                            messages=message_dicts)

@app.route('/rooms')
@login_required
def rooms():
    # Get all public rooms
    public_rooms = db.session.query(Room).filter_by(is_private=False).all()

    # Get private rooms where user is a member
    private_rooms = db.session.query(Room).filter_by(is_private=True).filter(
        Room.members.any(id=current_user.id)
    ).all()

    # For each private room, add a flag indicating if the user is a member
    for room in private_rooms:
        room.is_member = True
        room.is_creator = room.created_by == current_user.id

    return render_template('rooms.html',
                         public_rooms=public_rooms,
                         private_rooms=private_rooms,
                         user=current_user,
                         name=current_user.name,
                         profile_img=current_user.profile_img)

@app.route('/create_room', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'GET':
        return render_template('create_room.html', user=current_user)

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
            is_private=data.get('is_private', False)
        )

        # Generate invite code for private rooms
        if room.is_private:
            room.generate_invite_code()

        room.created_by = current_user.id
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

@app.route('/join/<invite_code>')
@login_required
def join_by_invite(invite_code):
    try:
        room = Room.query.filter_by(invite_code=invite_code).first()
        if not room:
            return render_template('invalid_invite.html', user=current_user)

        if not room.is_private:
            return render_template('invalid_invite.html', user=current_user)

        # Add user to room members if not already a member
        if current_user not in room.members:
            room.members.append(current_user)
            db.session.commit()

        # Redirect to the specific room's chat
        return redirect(url_for('chat', room_id=room.id))

    except Exception as e:
        print(f"Error joining room: {str(e)}")
        return render_template('invalid_invite.html', user=current_user)

# Track connected users in each room
connected_users = {}

@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        return False
    return True

@socketio.on('join')
def on_join(data):
    if not current_user.is_authenticated:
        return {'error': 'User not authenticated'}

    room_id = data.get('room_id')

    # Handle public chat (no room_id)
    if not room_id:
        join_room('public')
        if 'public' not in connected_users:
            connected_users['public'] = set()
        connected_users['public'].add(current_user.id)
        emit('member_count', {
            'room_id': 'public',
            'count': len(connected_users['public'])
        }, room='public')
        return {'success': True}

    # Handle private rooms
    try:
        room_id = int(room_id)
        room = Room.query.get(room_id)

        if not room:
            return {'error': 'Room not found'}

        if room.is_private and current_user not in room.members:
            return {'error': 'Access denied'}

        join_room(str(room_id))
        if room_id not in connected_users:
            connected_users[room_id] = set()
        connected_users[room_id].add(current_user.id)

        # Emit member count update
        emit('member_count', {
            'room_id': room_id,
            'count': len(connected_users[room_id])
        }, room=str(room_id))

        # Emit member list update
        member_list = [{
            'id': member.id,
            'name': member.name,
            'profile_img': member.profile_img
        } for member in room.members]

        emit('member_list_update', {
            'room_id': room_id,
            'members': member_list
        }, room=str(room_id))

        return {'success': True}

    except (ValueError, TypeError):
        return {'error': 'Invalid room ID'}
    except Exception as e:
        print(f"Error joining room: {str(e)}")
        return {'error': 'Server error'}

@socketio.on('leave')
def on_leave(data):
    if not current_user.is_authenticated:
        return {'error': 'User not authenticated'}

    room_id = data.get('room_id')
    if room_id:
        try:
            room_id = int(room_id)
            leave_room(str(room_id))
            if room_id in connected_users:
                connected_users[room_id].discard(current_user.id)

                # Emit member count update
                emit('member_count', {
                    'room_id': room_id,
                    'count': len(connected_users[room_id])
                }, room=str(room_id))

                # Get room and emit member list update
                room = Room.query.get(room_id)
                if room:
                    member_list = [{
                        'id': member.id,
                        'name': member.name,
                        'profile_img': member.profile_img
                    } for member in room.members]

                    emit('member_list_update', {
                        'room_id': room_id,
                        'members': member_list
                    }, room=str(room_id))

        except (ValueError, TypeError):
            pass
    else:
        leave_room('public')
        if 'public' in connected_users:
            connected_users['public'].discard(current_user.id)
            emit('member_count', {
                'room_id': 'public',
                'count': len(connected_users['public'])
            }, room='public')

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        # Remove from all rooms
        for room_id, users in connected_users.items():
            if current_user.id in users:
                users.discard(current_user.id)
                emit('member_count', {
                    'room_id': room_id,
                    'count': len(users)
                }, room=str(room_id))
        leave_room('public')
        if 'public' in connected_users:
            connected_users['public'].discard(current_user.id)
            emit('member_count', {
                'room_id': 'public',
                'count': len(connected_users['public'])
            }, room='public')

@socketio.on('message')
def handle_message(data):
    if not current_user.is_authenticated:
        return {'error': 'User not authenticated'}

    try:
        room = data.get('room')
        message_text = data.get('message')

        if not message_text:
            return {'error': 'Message is required'}

        # For public chat, room will be None
        room_id = None if room == 'null' or room is None else room

        # Ensure profile picture is valid
        profile_img = current_user.profile_img
        if not profile_img or not isinstance(profile_img, str) or not profile_img.startswith(('http', '/')):
            profile_img = url_for('static', filename='img/default-profile.png')

        # Create new message
        new_message = Message(
            user_id=current_user.id,
            room=room_id,
            name=current_user.name,
            message=message_text,
            profile_img=profile_img,
            created_at=datetime.now(timezone.utc)
        )

        # Save message to database
        db.session.add(new_message)
        db.session.flush()  # This ensures new_message.id is available
        db.session.commit()

        # Emit message to room or public chat
        emit('message', {
            'id': new_message.id,
            'user_id': current_user.id,
            'name': current_user.name,
            'message': message_text,
            'profile_img': profile_img,
            'room': room_id,
            'created_at': new_message.created_at.isoformat()
        }, room=str(room_id) if room_id else 'public')

        return {'success': True}

    except Exception as e:
        print(f"Error handling message: {str(e)}")
        db.session.rollback()
        return {'error': str(e)}

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/get_messages/<int:room_id>')
@login_required
def get_messages(room_id):
    try:
        # Verify room exists and user has access
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404

        # For private rooms, check membership
        if room.is_private and current_user not in room.members:
            return jsonify({'error': 'Access denied'}), 403

        # Get messages for the room, ordered by timestamp
        messages = Message.query.filter_by(room=room_id)\
            .order_by(Message.created_at.asc())\
            .all()

        # Format messages for JSON response
        message_list = []
        for message in messages:
            message_list.append({
                'id': message.id,
                'name': message.name,
                'message': message.message,
                'profile_img': message.profile_img,
                'room_id': room_id,
                'created_at': message.created_at.isoformat() if message.created_at else None
            })

        return jsonify(message_list)

    except Exception as e:
        print(f"Error getting messages: {str(e)}")
        return jsonify({'error': 'Failed to load messages'}), 500

@app.route('/remove_member/<int:room_id>/<string:user_id>', methods=['POST'])
@login_required
def remove_member(room_id, user_id):
    try:
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404

        # Check if current user is the room creator
        if room.created_by != current_user.id:
            return jsonify({'error': 'Only room creator can remove members'}), 403

        # Get the user to remove
        user_to_remove = User.query.get(user_id)
        if not user_to_remove:
            return jsonify({'error': 'User not found'}), 404

        # Remove user from room members
        if user_to_remove in room.members:
            room.members.remove(user_to_remove)
            db.session.commit()

            # Get updated member list
            member_list = [{
                'id': member.id,
                'name': member.name,
                'profile_img': member.profile_img
            } for member in room.members]

            # Emit updated member list to all room members
            socketio.emit('member_list_update', {
                'room_id': room_id,
                'members': member_list
            }, room=str(room_id))

            # Emit kick event to the removed user
            socketio.emit('kicked_from_room', {
                'room_id': room_id,
                'room_name': room.name
            }, room=str(user_id))

            # Update member count
            if room_id in connected_users:
                connected_users[room_id].discard(user_id)
                socketio.emit('member_count', {
                    'room_id': room_id,
                    'count': len(connected_users[room_id])
                }, room=str(room_id))

            return jsonify({'success': True})
        else:
            return jsonify({'error': 'User is not a member of this room'}), 400

    except Exception as e:
        print(f"Error removing member: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to remove member'}), 500

# Run the app with SocketIO
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port="5000", debug=True)