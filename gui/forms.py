# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm as Form
from wtforms import StringField
from wtforms import BooleanField
from wtforms.validators import DataRequired


class FileChooser(Form):
    root_dir = StringField('root_dir', validators=[DataRequired()])
    anno_sets = StringField('anno_sets', validators=None)
    index_file = BooleanField('index_file')


class DocumentForm(Form):
    pass
