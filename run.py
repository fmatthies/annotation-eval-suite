#!/home/matthies/workspaces/virtual_envs/bionlpformat_annotation/bin/python
# -*- coding: utf-8 -*-
# TODO: change execution path
from gui import gui_app, socketio


#gui_app.run(debug=True)
socketio.run(gui_app, debug=True)
