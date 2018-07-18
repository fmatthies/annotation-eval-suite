# -*- coding: utf-8 -*-
import operator
import os

from flask import render_template, redirect, request
from flask_socketio import emit

from compare import comparison
from gui import gui_app, socketio
from .forms import FileChooser

SET_LIST = ["data1/alt", "data2"]
ROOT_STRING = "test_resources/"
FINDEX_STRING = "index"

cbatch = None
doc_list = None
vis = None
current_doc = None
sentence_cache = list()
sentence_index = 0


def _load(_root, _sets):
    global cbatch
    global doc_list
    if cbatch is None:
        print("[DEBUG] Loading Batch Comparison for the first time")
        _sets = [_s.rstrip() for _s in [_s.lstrip() for _s in _sets.split(",")]]
        try:
            cbatch = comparison.BatchComparison(os.path.join(_root, FINDEX_STRING), _sets, _root)
            doc_list = sorted([cbatch.get_comparison_obj(doc).get_id() for doc in cbatch.doc_iterator()])
            return "load:successful"
        except Exception as e:
            print(e)
            return _root, _sets
    return "load:successful"


def _show_first(_doc):
    global vis
    global sentence_cache
    global sentence_index

    del sentence_cache[:]
    sentence_cache.append(("START", None))
    sentence_index = 0

    vis = _doc.sent_compare_generator()
    return ({'_type': 'first',
             '_table': _get_table('Medication', 'one_all'),
             '_measure': 'one_all'},
            _cycle_sentence("next"))


def _cycle_sentence(_direction):
    global vis
    global sentence_cache
    global sentence_index
    print("[DEBUG] cycling sentences")

    _sentence = None
    _triggers = None
    if _direction == "next":
        if len(sentence_cache) == sentence_index+1:
            _sentence, _triggers = next(vis, ("END", None))
            if _sentence != "END":
                sentence_cache.append((_sentence, _triggers))
                sentence_index += 1
        elif len(sentence_cache) > sentence_index:
            sentence_index += 1
            _sentence, _triggers = sentence_cache[sentence_index]
    elif _direction == "previous":
        if len(sentence_cache) != 0:
            _sentence, _triggers = sentence_cache[sentence_index - 1]
            if _sentence != "START":
                sentence_index -= 1

    if _sentence != "END" and _triggers is not None:
        _sorted = sorted(_triggers.items(), key=operator.itemgetter(0))
        return {"_sentence": _sentence,
                "_entities": [{"id": (x[0]).replace(".", "_"), "entities": x[1], "name": x[0]} for x in _sorted]}
    return {"_sentence": "",
            "_entities": []}


def _get_table(_trigger_type, _measure_type):
    global cbatch
    global current_doc
    _doc = cbatch.get_comparison_obj(document=current_doc)
    if _measure_type == "one_all":
        return _doc.return_agreement_scores(trigger=_trigger_type, match_type=_measure_type).to_html()
    return (_doc.return_agreement_scores(
        trigger=_trigger_type, match_type=_measure_type)[["all_fscore", "all_precision", "all_recall"]]).to_html()


def _get_annotators():
    global cbatch
    return [(x.replace(".", "_"), x) for x in cbatch.get_sets()]


@socketio.on('cycle sentences')
def cycle_sentences(direction):
    _sent_result = _cycle_sentence(direction)
    emit('vis sentence', _sent_result, json=True)


@socketio.on('change table')
def change_table(types):
    _ttype = types.get('ttype')
    _mtype = types.get('mtype')
    _table_result = _get_table(_ttype, _mtype)
    emit('ch table', _table_result)


@gui_app.route('/', methods=['GET', 'POST'])
@gui_app.route('/index', methods=['GET', 'POST'])
def index():
    global cbatch
    if cbatch is not None:
        return redirect('/documents')
    form = FileChooser(request.form)
    if form.validate_on_submit():
        _root = form.root_dir.data
        _sets = form.anno_sets.data
        _load_result = _load(_root, _sets)
        if _load_result != "load:successful":
            print(_load_result)
            print("[DEBUG] somethings wrong with input; root: {}, sets: {}".format(*_load_result))
            return render_template('index.html', title='Home', form=form)
        print("[DEBUG] redirect to documents")
        return redirect('/documents')
    print("[DEBUG] form is not validated")
    return render_template('index.html', title='Home', form=form)


@gui_app.route('/documents')
def document_list():
    global doc_list
    return render_template('index.html', title='Documents', documents=doc_list)


@gui_app.route('/documents/<string:doc_id>/results', methods=['GET', 'POST'])
def resolve_request(doc_id="None"):
    global doc_list
    global current_doc
    doc = cbatch.get_comparison_obj(doc_id)
    pos = doc_list.index(doc_id)
    _new_doc = False

    if current_doc != doc_id:
        _new_doc = True
    current_doc = doc_id

    result, sentences = None, None
    if _new_doc:
        print("[DEBUG] new document")
        result, sentences = request_map["showFirst"](doc)

    if request.method == 'POST':
        if request.form['submit'] == '<< previous':
            doc_id = doc_list[pos - 1] if pos - 1 >= 0 else doc_id
            print("[DEBUG] previous doc {}; pos: {}".format(doc_id, pos))
            return redirect('/documents/{}/results'.format(doc_id))
        elif request.form['submit'] == 'next >>':
            doc_id = doc_list[pos + 1] if pos + 1 < len(doc_list) else doc_id
            print("[DEBUG] next doc {}; pos: {}".format(doc_id, pos))
            return redirect('/documents/{}/results'.format(doc_id))
    if request.method == 'GET':
        _request = dict(request.args)
        if _request.get("_request"):
            _action = _request.get("_request")[0]
            sentences = _cycle_sentence()
            print(sentences)
    print("[DEBUG] render documents page")
    return render_template('document.html', title='Document - ' + doc_id,
                           document=doc, result=result, sentences=sentences, annotators=_get_annotators())


@gui_app.route('/index/reset')
def reset():
    global cbatch
    cbatch = None
    return redirect('/index')


request_map = {'showFirst': _show_first}
