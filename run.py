#!/home/matthies/workspaces/virtual_envs/bionlpformat_annotation/bin/python
# -*- coding: utf-8 -*-
# TODO: change execution path
import logging
import sys
from gui import gui_app, socketio

logger = logging.getLogger('mylogger')
# Configure logger to write to a file...


def my_handler(type, value, tb):
    logger.exception("Uncaught exception: {0}".format(str(value)))


# Install exception handler
sys.excepthook = my_handler


# gui_app.run(debug=True)
socketio.run(gui_app, debug=True, host="0.0.0.0")
