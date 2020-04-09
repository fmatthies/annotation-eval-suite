# -*- coding: utf-8 -*-

import collections
import sqlite3
import streamlit as st
from spacy import displacy
from seaborn import color_palette
from typing import Iterable, List, Dict, Tuple, OrderedDict

import app_constants.constants as const


def display_sentence_comparison(annotators, sentences, triggers, entities, sent_no, focus_entity=None):
    for _annotator, _values in triggers[sent_no].items():
        if _annotator in annotators:
            st.subheader(_annotator)
            st.write(
                return_html(sentence=sentences[sent_no], triggers=_values,
                            entity_list=entities, focus_entity=focus_entity),
                unsafe_allow_html=True
            )


@st.cache()
def get_color_dict(entity_list):
    colors = color_palette('colorblind', len(entity_list)).as_hex()
    return {entity_list[i]: colors[i] for i in range(len(entity_list))}


@st.cache()
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


@st.cache()
def get_entity_types_for_document(sentences: Iterable) -> List[str]:
    return sorted(set([ent_t[0] for ent_t in get_db_connection().execute(
        """
        SELECT DISTINCT type
        FROM {0}
        WHERE sentence in {1}
        ORDER BY type
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.MEDICATION_ENTITY), tuple(sentences))
    )]))


@st.cache()
def get_sentences_for_document(doc_id: str) -> OrderedDict[str, str]:
    return collections.OrderedDict((sents[0], sents[1]) for sents in get_db_connection().execute(
        """
        SELECT id, text
        FROM {0}
        WHERE document = {1}
        ORDER BY begin;
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.SENTENCE), doc_id)
    ))


# @st.cache()
# def get_annotations_for_annotator(anno_id: str)


@st.cache()
def get_sentences_with_annotations(doc_id: str) -> List[str]:
    return [sents[0] for sents in get_db_connection().execute(
        """
        SELECT id
        FROM {0}
        WHERE document = {1} AND has_annotation = 1
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.SENTENCE), doc_id)
    )]


@st.cache()
def get_annotators() -> Dict[str, str]:
    return {anno[0]: anno[1] for anno in get_db_connection().execute(
        """
        SELECT DISTINCT {0}, id
        FROM {1}
        ORDER BY {0};
        """.format(const.LayerTypes.ANNOTATOR, const.LAYER_TNAME_DICT.get(const.LayerTypes.ANNOTATOR))
    )}


@st.cache()
def get_documents() -> Dict[str, str]:
    return {doc[0]: doc[1] for doc in get_db_connection().execute(
        """
        SELECT DISTINCT {0}, id
        FROM {1}
        ORDER BY {0};
        """.format(const.LayerTypes.DOCUMENT, const.LAYER_TNAME_DICT.get(const.LayerTypes.DOCUMENT))
    )}


@st.cache(allow_output_mutation=True)
def get_db_connection() -> sqlite3.Connection:
    print("connect ...")
    return sqlite3.connect("./tmp.db", check_same_thread=False)


@st.cache()
def create_temporary_db(db_file_io) -> None:
    print("Create temporary db file ...")
    with open("./tmp.db", 'wb') as tmp:
        tmp.write(db_file_io.read())


def main():
    # ----- Sidebar ----- #
    fis = st.sidebar.file_uploader("Upload db file")
    if fis is not None:
        create_temporary_db(fis)
        st.sidebar.subheader("General")
        # --> Document Selection
        # -----> doc_dict = dict(document_name: document_id)
        doc_dict = get_documents()
        doc_name = st.sidebar.selectbox("Select document", sorted(doc_dict.keys()))
        show_complete = st.sidebar.checkbox("Show complete document", False)
        doc_id = doc_dict.get(doc_name)
        # --> Entity Selection
        # -----> sents_dict = OrderedDict(sentence_id: sentence_text)
        # -----> sents_with_anno = List(sentence_id)
        sents_dict = get_sentences_for_document(doc_id)
        sents_with_anno = get_sentences_with_annotations(doc_id)
        # -----> unique_sorted_list(entity_types)
        entities_set = get_entity_types_for_document(sents_with_anno)
        focus_entity = st.sidebar.selectbox("Select focus entity", options=entities_set)
        fc_entity_color_only = st.sidebar.checkbox("Color only focus entity", False)
        #     # # --> Agreement Properties
        #     # st.sidebar.subheader("Agreement Properties")
        #     # match_type = select_match_type()
        #     # threshold, boundary = 0, 0
        #     # if match_type == "one_all":
        #     #     threshold, boundary = get_threshold_boundary(_all_annotators)
        st.sidebar.subheader("Sentences")
        # --> Annotator Selection
        # -----> anno_dict = dict(annotator_name: annotator_id)
        anno_dict = get_annotators()
        annotators = st.sidebar.multiselect("Select annotators",
                                            options=list(anno_dict.keys()), default=list(anno_dict.keys()))
        # ----- Document Agreement Visualization ----- #
        st.header("Document")
        if show_complete:
            st.write(["\n".join([s for s in sents_dict.values()])])
        else:
            st.info("Select 'Show complete document' in the sidebar")
#     # st.header("Agreement - Document " + str(doc_id) + " ({})".format(entity))
#     # display_document_agreement(_folder_root, _all_annotators, entity, doc_id, _index, match_type, threshold, boundary)
#     #
        # # ----- Visualize Sentence Comparison ----- #
        sent_id = sents_with_anno[0] if len(sents_with_anno) >= 1 else None
        # --> Sentence Selection
        if len(sents_with_anno) <= 0:
            st.header("Sentences")
            st.sidebar.info("No sentences with annotations in this document")
            st.info("Sentence comparison not available")
        else:
            sent_no = st.sidebar.slider("Sentence no.", 1, len(sents_with_anno), 1)
            sent_id = sents_with_anno[sent_no - 1]
            st.header("Sentences (Nr: {})".format(str(sent_id.split("-")[-1])))
            st.write(sents_dict.get(sent_id))
#     st.write([e for e in get_entities(uima.MEDICATION_ENTITY, doc_id, annotators, data)])
#     # focus_entity = None
#     # if fc_entity_color_only:
#     #     focus_entity = entity
#     # display_sentence_comparison(annotators, _sentences, _triggers, _all_entities, sent_no, focus_entity)


main()
