#!/home/matthies/workspaces/virtual_envs/bionlpformat_annotation/bin/python
# -*- coding: utf-8 -*-

import os
import streamlit as st

from compare import comparison
from spacy import displacy
from seaborn import color_palette


def get_comparison_batch(folder_root, index_file, annotator_list, init_comp=True):
    cbatch = comparison.BatchComparison(index=os.path.join(folder_root, index_file), set_list=annotator_list,
                                        root=os.path.join(folder_root), init_comp=init_comp)
    return cbatch


def get_comparison_doc(comparison_batch, doc_id):
    cdoc = comparison_batch.get_comparison_obj(doc_id)
    return cdoc


def display_sentence_comparison(annotators, sentences, triggers, entities, sent_no):
    for _annotator, _values in triggers[sent_no].items():
        if _annotator in annotators:
            st.subheader(_annotator)
            st.write(
                return_html(sentence=sentences[sent_no], triggers=_values, entity_list=entities),
                unsafe_allow_html=True
            )


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
def return_html(sentence, triggers, entity_list):
    ex = [{
        "text": sentence,
        "ents": [{
            "start": t[2][0][0],
            "end": t[2][0][1],
            "label": t[1]
        } for t in triggers]
    }]
    return displacy.render(ex, style="ent", manual=True, minify=True, options={"colors": get_color_dict(entity_list)})


@st.cache
def get_annotators(folder_root):
    _abs_path = os.path.abspath(folder_root)
    return sorted([foo for foo in os.listdir(_abs_path) if os.path.isdir(os.path.join(_abs_path, foo))])


@st.cache
def get_documents(folder_root, annotators):
    # ToDo: what if no index file
    _index = has_document_index(folder_root)
    if _index:
        return sorted(get_comparison_batch(folder_root=folder_root, index_file=_index,
                                           annotator_list=annotators, init_comp=False).doc_list())


@st.cache
def get_entity_set(folder_root, annotator_list):
    _index = has_document_index(folder_root)
    _comparison_batch = get_comparison_batch(folder_root=folder_root, index_file=_index, annotator_list=annotator_list)
    return sorted(_comparison_batch.get_trigger_set())


@st.cache
def get_sentence_annotation(folder_root, annotator_list, doc_id):
    _index = has_document_index(folder_root)
    _comparison_batch = get_comparison_batch(folder_root=folder_root, index_file=_index, annotator_list=annotator_list)
    _comparison_doc = get_comparison_doc(_comparison_batch, doc_id)
    sentences, triggers = zip(*_comparison_doc.sent_compare_generator())
    return sentences, triggers


@st.cache
def get_folder_root():
    return "test-resources"


def main():
    _folder_root = get_folder_root()
    _all_annotators = get_annotators(folder_root=_folder_root)
    _entities = get_entity_set(folder_root=_folder_root, annotator_list=_all_annotators)

    annotators = st.sidebar.multiselect("Select annotators", options=_all_annotators, default=_all_annotators)
    doc_id = st.sidebar.selectbox("Select document", get_documents(folder_root=_folder_root, annotators=annotators))

    _sentences, _triggers = get_sentence_annotation(folder_root=_folder_root, annotator_list=_all_annotators, doc_id=doc_id)
    sent_no = st.sidebar.slider("Sentence no.", 1, len(_sentences), 1)

    st.header("Sentence " + str(sent_no))
    sent_no -= 1
    display_sentence_comparison(annotators, _sentences, _triggers, _entities, sent_no)


main()
