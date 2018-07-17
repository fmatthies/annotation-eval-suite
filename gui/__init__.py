from flask import Flask
from flask_socketio import SocketIO, emit

gui_app = Flask(__name__)
gui_app.config.from_object('gui_config')
gui_app.static_folder = 'static'

socketio = SocketIO(gui_app)

from gui import views
