# -*- coding: utf-8 -*-
import operator
import os
import glob

from flask import render_template, redirect, request
from flask_socketio import emit

from compare import comparison
from gui import gui_app, socketio
from .forms import FileChooser

FINDEX_STRING = "index"
IS_INDEX_FILE = False

cbatch = None
doc_list = None
trigger_list = None
vis = None
current_doc = None
sentence_cache = list()
sentence_index = 0


def _get_doc_list(_root, _sets):
    _docs = set()
    for _anno in _sets:
        _d = {f.name.rstrip(".txt") for f in os.scandir(os.path.join(_root, _anno)) if f.is_file() and f.name.endswith(".txt")}
        if len(_docs) == 0:
            _docs = _d
        else:
            _docs.union(_d)
    return list(_docs)


def _load(_root, _sets):
    global cbatch
    global doc_list
    global trigger_list
    if cbatch is None:
        print("[DEBUG] Loading Batch Comparison for the first time")
        try:
            if _sets != "":
                _sets = [_s.rstrip() for _s in [_s.lstrip() for _s in _sets.split(",")]]
            else:
                _folder = [f.name for f in os.scandir(_root) if f.is_dir()]
                _sets = [anno for anno in _folder if not anno.startswith(".")]

            # ToDo: remove this global and have a checkbox for whether to use an index file of docs
            #  or all docs across all annotators that have the same name
            if IS_INDEX_FILE:
                _index = os.path.join(_root, FINDEX_STRING)
            else:
                _index = _get_doc_list(_root, _sets)

            cbatch = comparison.BatchComparison(_index, _sets, _root)
            trigger_list = list(cbatch.get_trigger_set())
            doc_list = sorted([cbatch.get_comparison_obj(doc).get_id() for doc in cbatch.doc_iterator()])
            if len(doc_list) == 0:
                return "[Error] no documents"
            return "load:successful"
        except Exception as e:
            print(e)
            return _root, _sets
    return "load:successful"


def _get_highest_count_trigger(doc):
    highest = doc.get_trigger_set().most_common(1)
    return highest[0][0]


def _show_first(_doc):
    global vis
    global sentence_cache
    global sentence_index

    del sentence_cache[:]
    sentence_cache.append(("START", None))
    sentence_index = 0

    vis = _doc.sent_compare_generator()
    highest = _get_highest_count_trigger(_doc)
    return ({'_type': 'first',
             '_table': _get_table(highest, 'one_all', _threshold=0, _boundary=0),
             '_measure': 'one_all',
             '_highest_count': highest},
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


def _get_table(_trigger_type, _measure_type, _threshold, _boundary):
    global cbatch
    global current_doc
    _doc = cbatch.get_comparison_obj(document=current_doc)
    if _measure_type == "one_all":
        return _doc.return_agreement_scores(trigger=_trigger_type, match_type=_measure_type,
                                            threshold=_threshold, boundary=_boundary).to_html()
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
def change_table(tvalues):
    _ttype = tvalues.get('ttype')
    _mtype = tvalues.get('mtype')
    _threshold = tvalues.get('threshold')
    _boundary = tvalues.get('boundary')
    print("measurement: {}, trigger: {}, threshold: {}, boundary: {}".format(_mtype, _ttype, _threshold, _boundary))
    _table_result = _get_table(_ttype, _mtype, _threshold, _boundary)
    emit('ch table', _table_result)


@socketio.on('cycle doc')
def cycle_doc(dvalues):
    global doc_list
    _id = dvalues.get('currentId')
    _dir = dvalues.get('direction')

    pos = doc_list.index(_id)
    if _dir == "prev":
        _id = doc_list[pos - 1] if pos - 1 >= 0 else _id
    elif _dir == "next":
        _id = doc_list[pos + 1] if pos + 1 < len(doc_list) else _id

    if _id == dvalues.get('currentId'):
        return
    emit('cy doc', _id)


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


@gui_app.route('/documents/<string:doc_id>/results')
def resolve_request(doc_id="None"):
    global doc_list
    global current_doc

    if doc_id not in doc_list:
        return redirect('/index')

    doc = cbatch.get_comparison_obj(doc_id)
    current_doc = doc_id

    print("[DEBUG] new document")
    result, sentences = request_map["showFirst"](doc)

    print("[DEBUG] render documents page")
    return render_template('document.html', title='Document - ' + doc_id,
                           document=doc, result=result, sentences=sentences, annotators=_get_annotators(),
                           triggers=[t[0] for t in doc.get_trigger_set().most_common()])


@gui_app.route('/index/reset')
def reset():
    global cbatch
    cbatch = None
    return redirect('/index')


request_map = {'showFirst': _show_first}
