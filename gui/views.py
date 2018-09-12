# -*- coding: utf-8 -*-
import operator
import os

from math import pi
from bokeh.embed import components
from bokeh.plotting import figure as bfigure
import bokeh.palettes as bpalettes
from pandas import DataFrame
from seaborn import color_palette
from flask import render_template, redirect, request
from flask_socketio import emit

from compare import comparison
from gui import gui_app, socketio
from .forms import FileChooser

FINDEX_STRING = "index"
SCRIPT_STRING = '<script type="text/javascript">'
SCRIPT_END_STRING = "</script>"

cbatch = None
doc_list = None
trigger_list = None
vis = None
current_doc = None
brat_entity_vis = None
sentence_cache = list()
sentence_index = 0


def _gather_entity_types(entity_list):
    global cbatch

    cp = color_palette('colorblind', len(entity_list)).as_hex()
    annotation_entities = {"entity_types": []}
    for ent in entity_list:
        annotation_entities["entity_types"].append(
            {
                "type": ent,
                "labels": [ent],
                "bgColor": cp[entity_list.index(ent)],
                "borderColor": "darken"
            }
        )

    return annotation_entities


def _get_doc_list(_root, _sets):
    _docs = set()
    for _anno in _sets:
        _d = {os.path.splitext(f.name)[0] for f in os.scandir(os.path.join(_root, _anno)) if f.is_file() and
              os.path.splitext(f)[1].endswith(".txt")}
        if len(_docs) == 0:
            _docs = _d
        else:
            _docs.union(_d)
    return list(_docs)


def _load(_root, _sets, _index_file):
    global cbatch
    global doc_list
    global trigger_list
    global brat_entity_vis
    if cbatch is None:
        print("[DEBUG] Loading Batch Comparison for the first time")
        try:
            if _sets != "":
                _sets = [_s.rstrip() for _s in [_s.lstrip() for _s in _sets.split(",")]]
            else:
                _folder = [f.name for f in os.scandir(_root) if f.is_dir()]
                _sets = [anno for anno in _folder if not anno.startswith(".")]

            if _index_file and os.path.exists(os.path.join(_root, FINDEX_STRING)):
                _index = os.path.join(_root, FINDEX_STRING)
            else:
                print("[INFO] not using an index file")
                _index = _get_doc_list(_root, _sets)

            cbatch = comparison.BatchComparison(_index, _sets, _root)
            trigger_list = list(cbatch.get_trigger_set())
            brat_entity_vis = _gather_entity_types(trigger_list)
            doc_list = sorted([cbatch.get_comparison_obj(doc).get_id() for doc in cbatch.doc_iterator()])
            if len(doc_list) == 0:
                return "[Error] no documents"
            return "load:successful"
        except Exception as e:
            print(e)
            return _root, _sets
    return "load:successful"


def _get_highest_count_trigger(doc: comparison.Comparison):
    highest = doc.get_trigger_set().most_common(1)
    if highest:
        return highest[0][0]
    return None


def _get_stats(_doc):
    _sets = _doc.get_sets()
    _triggers = [t for t in _doc.get_trigger_set()]
    _df = DataFrame(index=_sets, columns=_triggers)
    _bfigure = bfigure(y_axis_label='Count',
                       plot_height=60*len(_sets) if len(_sets) >= 4 else 250)

    for annotator in _sets:
        _counter = _doc.get_triggers_for_annotator(annotator)
        for _t in _counter:
            _df.at[annotator, _t] = _counter[_t]

    if not _df.empty:
        ax = _df.T.plot.bar()
        for _con in ax.containers:
            for _bar in _con:
                _bfigure.quad(bottom=_bar._y0, top=_bar._y1, left=_bar._x0, right=_bar._x1, line_color='black',
                              fill_color=bpalettes.Category10[10][_sets.index(_con._label)], legend=_con._label)
        _bfigure.xaxis.ticker = list(range(len(_triggers)))
        _bfigure.xaxis.major_label_overrides = {x: _triggers[x] for x in range(len(_triggers))}
        _bfigure.xaxis.major_label_orientation = pi / 6
        _bfigure.xaxis.major_label_text_font_size = "11pt"
    else:
        pass

    return components(_bfigure)


def _show_first(_doc):
    global vis
    global sentence_cache
    global sentence_index

    del sentence_cache[:]
    sentence_cache.append(("START", None))
    sentence_index = 0

    vis = _doc.sent_compare_generator()
    highest = _get_highest_count_trigger(_doc)
    script, div = _get_stats(_doc)
    # This is really hacky, but I needed a way to load the bokeh script with 'head'
    script = SCRIPT_STRING + "\nhead" + script[len(SCRIPT_STRING)+1:-(len(SCRIPT_END_STRING)+4)] + ";\n" + SCRIPT_END_STRING
    return ({'_type': 'first',
             '_table': _get_table(highest, 'one_all', _threshold=0, _boundary=0),
             '_measure': 'one_all',
             '_highest_count': highest,
             '_bokeh_script': script,
             '_bokeh_div': div},
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
    _doc: comparison.Comparison = cbatch.get_comparison_obj(document=current_doc)
    if _trigger_type is not None:
        if _measure_type == "one_all":
            return _doc.return_agreement_scores(trigger=_trigger_type, match_type=_measure_type,
                                                threshold=_threshold, boundary=_boundary).to_html()
        return (_doc.return_agreement_scores(
            trigger=_trigger_type, match_type=_measure_type)[["all_fscore", "all_precision", "all_recall"]]).to_html()
    return


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
    global brat_entity_vis
    if cbatch is not None:
        return redirect('/documents')
    form = FileChooser(request.form)
    if form.validate_on_submit():
        _root = form.root_dir.data
        _sets = form.anno_sets.data
        _index_file = form.index_file.data
        _load_result = _load(_root, _sets, _index_file)
        if _load_result != "load:successful":
            print(_load_result)
            print("[DEBUG] somethings wrong with input; root: {}, sets: {}".format(*_load_result))
            return render_template('index.html', title='Home', form=form)
        print("[DEBUG] redirect to documents")
        return redirect('/documents')
    print("[DEBUG] form is not validated")
    return render_template('index.html', title='Home', form=form,
                           entities=brat_entity_vis)


@gui_app.route('/documents')
def document_list():
    global doc_list
    global brat_entity_vis
    return render_template('index.html', title='Documents', documents=doc_list,
                           entities=brat_entity_vis)


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
                           triggers=[t[0] for t in doc.get_trigger_set().most_common()],
                           entities=brat_entity_vis)


@gui_app.route('/index/reset')
def reset():
    global cbatch
    cbatch = None
    return redirect('/index')


request_map = {'showFirst': _show_first}
