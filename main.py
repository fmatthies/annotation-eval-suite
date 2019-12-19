#!/home/matthies/workspaces/virtual_envs/bionlpformat_annotation/bin/python
# -*- coding: utf-8 -*-

import os
import streamlit as st

from compare import comparison
from spacy import displacy
from seaborn import color_palette


def select_match_type():
    match_dict = {"One vs. All": "one_all", "Strict": "strict", "Approximate": "approximate"}
    _mtype = st.sidebar.selectbox("Match type", list(match_dict.keys()))
    return match_dict[_mtype]


def get_threshold_boundary(annotators):
    _max_t = len(annotators) - 1
    _max_b = _max_t - 1
    _threshold = st.sidebar.slider("Threshold", 0, _max_t, 0)
    _boundary = st.sidebar.slider("Boundary", 0, _max_b, 0)
    return _threshold, _boundary


def display_document_agreement(folder_root, annotators, entity, doc_id, index_file=None,
                               match_type="strict", threshold=0, boundary=0):
    _cmp = load_data(folder_root, annotators, index_file)
    _df = _cmp.return_agreement(entity, doc_id, match_type, threshold, boundary)
    if match_type != "one_all":
        _annotators = _df.index.values
        _df_view = _df[[a + "_fscore" for a in _annotators]]
        st.write(_df_view)
    else:
        st.write(_df)


def display_sentence_comparison(annotators, sentences, triggers, entities, sent_no, focus_entity=None):
    for _annotator, _values in triggers[sent_no].items():
        if _annotator in annotators:
            st.subheader(_annotator)
            st.write(
                return_html(sentence=sentences[sent_no], triggers=_values,
                            entity_list=entities, focus_entity=focus_entity),
                unsafe_allow_html=True
            )


def create_selectbox_with_counts(entities, counts):
    _entity = st.sidebar.selectbox(
        "Select focus entity", [entities[i] + " ({})".format(counts[i]) for i in range(len(entities))])
    return _entity.split()[0]


@st.cache
def has_document_index(folder_root):
    for _index in ["index", "index.txt", "Index", "Index.txt", "INDEX", "INDEX.txt"]:
        if os.path.exists(os.path.join(os.path.abspath(folder_root), _index)):
            return _index
    return False


@st.cache
def get_color_dict(entity_list):
    colors = color_palette('colorblind', len(entity_list)).as_hex()
    return {entity_list[i].upper(): colors[i] for i in range(len(entity_list))}


@st.cache
def return_html(sentence, triggers, entity_list, focus_entity):
    ex = [{
        "text": sentence,
        "ents": [{
            "start": t[2][0][0],
            "end": t[2][0][1],
            "label": t[1]
        } for t in triggers]
    }]
    _colors = get_color_dict(entity_list)
    if focus_entity is not None:
        _colors = {vk[0]: vk[1] for vk in _colors.items() if vk[0] == focus_entity.upper()}
    return displacy.render(ex, style="ent", manual=True, minify=True, options={"colors": _colors})


@st.cache
def get_entities(folder_root, annotators, doc_id=None, index_file=None):
    _cmp = load_data(folder_root, annotators, index_file)
    if doc_id is None:
        _entities, _counts = zip(*_cmp.get_trigger_set().most_common())
    else:
        _entities, _counts = zip(*_cmp.get_comparison_obj(doc_id).get_trigger_set().most_common())
    return _entities, _counts


@st.cache
def get_annotators(folder_root):
    _abs_path = os.path.abspath(folder_root)
    return sorted([foo for foo in os.listdir(_abs_path) if os.path.isdir(os.path.join(_abs_path, foo))])


@st.cache
def get_documents(folder_root, annotators, index_file=None):
    _cmp = load_data(folder_root, annotators, index_file)
    return sorted(_cmp.doc_list())


@st.cache
def get_sentence_annotation(folder_root, annotator_list, doc_id, index_file=None):
    _cmp = load_data(folder_root, annotator_list, index_file)
    _comparison_doc = _cmp.get_comparison_obj(doc_id)
    sentences, triggers = zip(*_comparison_doc.sent_compare_generator())
    return sentences, triggers


@st.cache
def get_folder_root():
    return "test-resources"


@st.cache(allow_output_mutation=True)
def load_data(folder_root, annotators, index_file=None):
    _index = index_file
    if index_file is None:
        _index = has_document_index(folder_root)
    cbatch = comparison.BatchComparison(index=os.path.join(folder_root, _index), set_list=annotators,
                                        root=os.path.join(folder_root))
    return cbatch


def main():

    _index = None
    _folder_root = get_folder_root()
    _all_annotators = get_annotators(folder_root=_folder_root)

    cmp = load_data(_folder_root, _all_annotators, _index)
    _all_entities, _all_entity_counts = get_entities(_folder_root, _all_annotators, index_file=_index)

    # ----- Sidebar ----- #
    st.sidebar.subheader("General")
    # --> Document Selection
    _documents = get_documents(_folder_root, _all_annotators, _index)
    doc_id = st.sidebar.selectbox("Select document", _documents)
    # --> Entity Selection
    _doc_entities, _doc_entity_counts = get_entities(_folder_root, _all_annotators, doc_id, _index)
    entity = create_selectbox_with_counts(_doc_entities, _doc_entity_counts)
    fc_entity_color_only = st.sidebar.checkbox("Color only focus entity", False)
    # --> Agreement Properties
    st.sidebar.subheader("Agreement Properties")
    match_type = select_match_type()
    threshold, boundary = 0, 0
    if match_type == "one_all":
        threshold, boundary = get_threshold_boundary(_all_annotators)
    # --> Annotator Selection
    st.sidebar.subheader("Sentences")
    annotators = st.sidebar.multiselect("Select annotators", options=_all_annotators, default=_all_annotators)
    # --> Sentence Selection
    _sentences, _triggers = get_sentence_annotation(_folder_root, _all_annotators, doc_id, _index)
    sent_no = st.sidebar.slider("Sentence no.", 1, len(_sentences), 1)

    # ----- Document Agreement Visualization ----- #
    st.header("Agreement - Document " + str(doc_id) + " ({})".format(entity))
    display_document_agreement(_folder_root, _all_annotators, entity, doc_id, _index, match_type, threshold, boundary)

    # ----- Visualize Sentence Comparison ----- #
    st.header("Comparison - Sentence " + str(sent_no))
    sent_no -= 1
    focus_entity = None
    if fc_entity_color_only:
        focus_entity = entity
    display_sentence_comparison(annotators, _sentences, _triggers, _all_entities, sent_no, focus_entity)


main()
