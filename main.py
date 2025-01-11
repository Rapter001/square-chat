import os
from utils import save_profile_pic
from models import db, User, Message
from flask_sqlalchemy import SQLAlchemy
from forms import LoginForm, SignupForm, UpdateAccountForm
from flask_socketio import SocketIO, join_room, leave_room, send
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app = Flask(__name__)

# Generate a random secret key for session management
app.secret_key = os.urandom(24)

# Set up database configuration for SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///square-chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure the folder to upload profile pictures
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'

# Initialize the database with the Flask app
db.init_app(app)

# Initialize SocketIO for real-time communication
socketio = SocketIO(app)

# Initialize login manager to handle user sessions
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Dictionary to keep track of active users
users = {}

# Dictionary to keep track of active chat rooms
rooms = {}

# Create the database tables within the app context
with app.app_context():
    db.create_all()

# Load a user by their ID for session management
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route for the signup page (register new user)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        # Check if the username or email already exists
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing_user:
            flash('Username or Email already exists.', 'danger')
        else:
            # Hash the password and optionally save profile picture
            hashed_password = generate_password_hash(form.password.data)
            profile_pic = None
            if form.profile_pic.data:
                profile_pic = save_profile_pic(form.profile_pic.data)
            # Create a new user and add to the database
            user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password, profile_pic=profile_pic)
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html', form=form)

# Route for the login page (authenticate users)
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Check if user exists by username or email and validate password
        user = User.query.filter((User.username == form.username.data) | (User.email == form.username.data)).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            # Redirect user to the chat room if they have selected one
            room = session.get('room', '')
            if room:
                return redirect(url_for('chat'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username/email and password', 'danger')
    return render_template('login.html', form=form)

# Route to log out the user
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# Route for the index page (main entry to select or create a chat room)
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # Create or join a room
        room = request.form['room']
        session['room'] = room
        if room not in rooms:
            rooms[room] = []
        return redirect(url_for('chat'))

    room = request.args.get('room')
    if room:
        session['room'] = room
        if room not in rooms:
            rooms[room] = []
        return redirect(url_for('chat'))
        
    return render_template('index.html')

# Route for the chat room
@app.route('/chat')
@login_required
def chat():
    room = session.get('room', '')
    if room == '':
        return redirect(url_for('index'))
    return render_template('chat.html', username=current_user.username, room=room, profile_pic=current_user.profile_pic)

# Route to update user profile (username, email, and profile picture)
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        # Check if the new username or email is already taken by another user
        if form.username.data != current_user.username:
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash('Username already exists.', 'danger')
                return redirect(url_for('profile'))

        if form.email.data != current_user.email:
            existing_email = User.query.filter_by(email=form.email.data).first()
            if existing_email:
                flash('Email already exists.', 'danger')
                return redirect(url_for('profile'))

        # Update user's username, email, and optionally profile picture and password
        current_user.username = form.username.data
        current_user.email = form.email.data

        if form.profile_pic.data:
            profile_pic = save_profile_pic(form.profile_pic.data)
            current_user.profile_pic = profile_pic

        if form.password.data:
            current_user.password_hash = generate_password_hash(form.password.data)

        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('profile'))

    profile_pic = url_for('static', filename='profile_pics/' + current_user.profile_pic) if current_user.profile_pic else None
    form.username.data = current_user.username
    form.email.data = current_user.email
    return render_template('profile.html', form=form, profile_pic=profile_pic)

# Route to get chat messages for a specific room
@app.route('/messages/<room>')
@login_required
def get_messages(room):
    # Retrieve all messages for the given room, ordered by timestamp
    messages = Message.query.filter_by(room=room).order_by(Message.timestamp).all()
    return jsonify([{'username': msg.username, 'content': msg.content, 'timestamp': msg.timestamp, 'profile_pic': User.query.filter_by(username=msg.username).first().profile_pic} for msg in messages])

# Handle receiving a new chat message via SocketIO
@socketio.on('message')
def handle_message(data):
    room = session.get('room')
    username = current_user.username
    content = data['msg']
    # Save the message to the database
    message = Message(username=username, room=room, content=content)
    db.session.add(message)
    db.session.commit()
    # Send the message to all users in the room
    send({'msg': content, 'username': username, 'profile_pic': current_user.profile_pic}, room=room)

# Handle a user joining a chat room via SocketIO
@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)

# Handle a user leaving a chat room via SocketIO
@socketio.on('leave')
def handle_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)

# Run the Flask app with SocketIO for real-time functionality
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port="5000", debug=False)