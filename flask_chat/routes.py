from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_socketio import join_room, leave_room, send
from sqlalchemy import asc, desc

from flask_chat.wtform_fields import *
from flask_chat.models import *
from flask_chat import app, db, socketio

from functools import wraps

# Initialize login manager
login = LoginManager(app)
login.init_app(app)


def restricted(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.role == 'admin':
                abort(403)
            return func(*args, **kwargs)

        return wrapper

    return decorator


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


# Predefined rooms for chat
# ROOMS = ["lounge", "news", "games", "coding", "lol"]
ROOMS = []


@app.route("/", methods=['GET', 'POST'])
def index():
    reg_form = RegistrationForm()

    # Update database if validation success
    if reg_form.validate_on_submit():
        username = reg_form.username.data
        password = reg_form.password.data

        # Hash password
        hashed_pswd = pbkdf2_sha256.hash(password)

        # Add username & hashed password to DB
        user = User(username=username, hashed_pswd=hashed_pswd)
        db.session.add(user)
        db.session.commit()

        flash('Registered successfully. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template("index.html", form=reg_form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    login_form = LoginForm()

    # Allow login if validation success
    if login_form.validate_on_submit():
        user_object = User.query.filter_by(username=login_form.username.data).first()
        login_user(user_object)
        return redirect(url_for('chat'))

    return render_template("login.html", form=login_form)


@app.route("/logout", methods=['GET'])
def logout():
    # Logout user
    logout_user()
    flash('You have logged out successfully', 'success')
    return redirect(url_for('login'))


@app.route("/create_room", methods=['GET', 'POST'])
def create_room():
    room_form = RoomForm()

    if room_form.validate_on_submit():
        room_name = room_form.roomname.data.lower()

        room_check = Room.query.filter_by(title=room_name).first()

        if room_check is not None:
            flash("Room with similar name already exist ", room_check.title)
            return redirect(url_for('create_room'))

        room = Room(title=room_name, admin_id=current_user.id)

        db.session.add(room)
        db.session.commit()

        room = Room.query.order_by(desc(Room.id)).first()
        room_user = RoomUser(room_id=room.id, user_id=current_user.id)

        db.session.add(room_user)
        db.session.commit()

        flash('Room was successfully created. Add friends to the room.', 'success')
        return redirect(url_for('create_room'))

    return render_template("create-room.html", form=room_form)


@app.route("/delete_room", methods=['GET', 'POST'])
def delete_room():
    form = FlaskForm()
    rooms = Room.query.filter_by(admin_id=current_user.id).all()
    if form.validate_on_submit():
        room_id = request.form.get("room_id")
        room = Room.query.filter_by(id=room_id).first()
        room_users = RoomUser.query.filter_by(room_id=room_id).all()
        room_comments = Comment.query.filter_by(room=room.title).all()

        for room_user in room_users:
            current_db_sessions = db.session.object_session(room_user)
            current_db_sessions.delete(room_user)
            current_db_sessions.commit()

        for room_comment in room_comments:
            current_db_sessions = db.session.object_session(room_comment)
            current_db_sessions.delete(room_comment)
            current_db_sessions.commit()

        current_db_sessions = db.session.object_session(room)
        current_db_sessions.delete(room)
        current_db_sessions.commit()

        flash('Room was successfully deleted', 'success')
        return redirect(url_for('delete_room'))

    return render_template("delete-room.html", form=form, rooms=rooms)


@app.route("/leave_room", methods=['GET', 'POST'])
def leave_room_per():
    form = FlaskForm()
    rooms_u = RoomUser.query.filter_by(user_id=current_user.id).all()
    rooms = Room.query.filter_by(admin_id=current_user.id).all()
    rooms_u_id = set()
    rooms_id = set()
    for r_u in rooms_u:
        rooms_u_id.add(r_u.room_id)
    for r in rooms:
        rooms_id.add(r.id)

    rooms_set_id = rooms_u_id - rooms_id

    rooms = []

    for id in rooms_set_id:
        rooms.append(Room.query.filter_by(id=id).first())

    if form.validate_on_submit():
        room_select_id = request.form.get('room_id')
        room_user = RoomUser.query.filter_by(room_id=room_select_id, user_id=current_user.id).first()

        current_db_sessions = db.session.object_session(room_user)
        current_db_sessions.delete(room_user)
        current_db_sessions.commit()

        flash('You have successfully left the room', 'success')
        return redirect(url_for('leave_room'))

    return render_template("leave-room.html", form=form, rooms=rooms)


@app.route("/add_friend", methods=['GET', 'POST'])
def add_friend():
    addFriend_form = AddFriendForm()

    rooms = Room.query.filter_by(admin_id=current_user.id).all()

    if addFriend_form.validate_on_submit():

        room_select_id = request.form.get('room_id')
        friend_name = addFriend_form.friend.data

        friend = User.query.filter_by(username=friend_name).first()
        if friend is None:
            flash("User with this name doesn't exist", "error")
            return redirect(url_for('add_friend'))

        room_user = RoomUser.query.filter_by(room_id=room_select_id, user_id=friend.id).first()
        if room_user is not None:
            flash("User already belong to this group", "error")
            return redirect(url_for('add_friend'))

        room_user = RoomUser(room_id=room_select_id, user_id=friend.id)

        db.session.add(room_user)
        db.session.commit()

        flash('Friend was successfully invited.', 'success')
        return redirect(url_for('chat'))
    return render_template("add-friend.html", form=addFriend_form, rooms=rooms)


@app.route("/chat", methods=['GET', 'POST'])
def chat():
    if not current_user.is_authenticated:
        flash('Please login', 'danger')
        return redirect(url_for('login'))
    ROOMS = ['lounge']
    RoomUsers = RoomUser.query.filter_by \
        (user_id=current_user.id).all()
    for i in RoomUsers:
        RoomHere = Room.query.filter_by(id=i.room_id).first()
        ROOMS.append(RoomHere.title)
    return render_template("chat.html",
                           username=current_user.username,
                           rooms=ROOMS, role=current_user.role)


@app.route('/comments', methods=['GET'])
def get_all_comments_api():
    comments = Comment.query.all()
    output = []
    for comment in comments:
        comment_data = {}
        comment_data['id'] = comment.id
        comment_data['content'] = comment.body
        comment_data['room'] = comment.room
        comment_data['user_id'] = comment.user_id
        output.append(comment_data)

    return jsonify({'comments': output})


@app.route('/comments/<id>', methods=['GET'])
def get_one_comment_api(id):
    comment = Comment.query.filter_by(id=id).first()
    if not comment:
        return jsonify({'message': 'No comment was found!'})
    comment_data = {}
    comment_data['id'] = comment.id
    comment_data['content'] = comment.body
    comment_data['room'] = comment.room
    comment_data['user_id'] = comment.user_id

    return jsonify({'user': comment_data})


@app.route('/comment', methods=['POST'])
def create_comment_api():
    data = request.get_json()
    new_comment = Comment(body=data['content'],
                          room=data['room'],
                          user_id=data['user_id'])
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({'message': 'New comment was created!'})


@app.route('/comments/<id>', methods=['PUT'])
def update_comment_api(id):
    data = request.get_json()
    comment = Comment.query.filter_by(id=id).first()
    if not comment:
        return jsonify({'message': 'No comment was found!'})
    comment.body = data['content']
    db.session.commit()
    return jsonify({'message': 'The comment has been updated!'})


@app.route('/comments/<id>', methods=['DELETE'])
def delete_comment_api(id):
    comment = Comment.query.filter_by(id=id).first()
    if not comment:
        return jsonify({'message': 'No comment was found!'})
    current_db_sessions = db.session.object_session(comment)
    current_db_sessions.delete(comment)
    current_db_sessions.commit()

    return jsonify({'message': 'The comment has been deleted!'})


@app.route('/admin-page')
@login_required
@restricted(role="admin")
def home_admin():
    return render_template('admin-home.html')


@app.route('/admin-page/users-list')
@login_required
@restricted(role="admin")
def users_list_admin():
    users = User.query.all()
    return render_template('users-list-admin.html', users=users)


@app.route('/admin-page/create-user', methods=['GET', 'POST'])
@login_required
@restricted(role="admin")
def user_create_admin():
    form = AdminUserCreateForm()
    if form.validate_on_submit():
        hashed_password = pbkdf2_sha256.hash(form.password.data)
        user = User(username=form.username.data,
                    hashed_pswd=hashed_password)
        user.role = form.role.data
        db.session.add(user)
        db.session.commit()
        flash('User has been created!', 'success')
        return redirect(url_for('users_list_admin'))
    if form.errors:
        flash(form.errors, 'danger')
    return render_template('user-create-admin.html',
                           title='Create User', form=form)


@app.route('/admin-page/update-user/<id>', methods=['GET', 'POST'])
@login_required
@restricted(role="admin")
def user_update_admin(id):
    user = User.query.get(id)
    form = AdminUserUpdateForm()
    form.username.data = user.username
    if form.validate_on_submit():
        user.username = form.username.data
        user.role = form.role.data
        db.session.commit()
        flash('User account has been updated!', 'success')
        return redirect(url_for('users_list_admin'))
    if form.errors:
        flash(form.errors, 'danger')
    return render_template('user-update-admin.html', title='Edit User', form=form)


@app.route('/admin-page/delete-user/<id>')
@login_required
@restricted(role="admin")
def user_delete_admin(id):
    user = User.query.get(id)
    rooms = Room.query.filter_by(admin_id=id).all()
    for room in rooms:
        current_db_sessions = db.session.object_session(room)
        comments = Comment.query.filter_by(room=room.title.capitalize()).all()
        room_users = RoomUser.query.filter_by(room_id=room.id).all()

        for comment in comments:
            current_db_sessions = db.session.object_session(comment)
            current_db_sessions.delete(comment)
            current_db_sessions.commit()

        for room_user in room_users:
            current_db_sessions = db.session.object_session(room_user)
            current_db_sessions.delete(room_user)
            current_db_sessions.commit()

        current_db_sessions.delete(room)
        current_db_sessions.commit()
    current_db_sessions = db.session.object_session(user)
    current_db_sessions.delete(user)
    current_db_sessions.commit()

    flash('User account has been deleted!', 'success')
    return redirect(url_for('users_list_admin'))


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404


@socketio.on('incoming-msg')
def on_message(data):
    """Broadcast messages"""
    msg = data["msg"]
    username = data["username"]
    room = data["room"]
    # Set timestamp
    time_stamp = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")
    send({"username": username, "msg": msg, "time_stamp": time_stamp}, room=room)
    # Add comment to DB
    new_comment = Comment(body=msg, user_id=current_user.id, room=room, timestamp=datetime.now())
    db.session.add(new_comment)
    db.session.commit()


@socketio.on('join')
def on_join(data):
    """User joins a room"""
    username = data["username"]
    room = data["room"]
    join_room(room)

    # Broadcast that new user has joined
    send({"msg": username + " has joined the " + room + " room."}, room=room)
    # send some old  comments from this room
    comments = Comment.query.filter_by(room=data["room"]).order_by(Comment.timestamp.desc()).limit(
        10).from_self().order_by(Comment.timestamp)

    for comment in comments:
        msg = comment.body
        username = comment.author.username
        room = comment.room
        # Set timestamp
        time_stamp = comment.timestamp.strftime("%d.%m.%Y, %H:%M:%S")
        send({"username": username, "msg": msg, "time_stamp": time_stamp, "room": room})


@socketio.on('leave')
def on_leave(data):
    """User leaves a room"""
    username = data['username']
    room = data['room']
    leave_room(room)
    send({"msg": username + " has left the room"}, room=room)
