from flask_chat import app, socketio

if __name__ == '__main__':
    socketio.run(app, debug=True)
