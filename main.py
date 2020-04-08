# -*- coding: utf-8 -*-

import sqlite3
import streamlit as st
from spacy import displacy
from seaborn import color_palette
from typing import Iterable

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


def create_selectbox_with_counts(entities, counts):
    _entity = st.sidebar.selectbox(
        "Select focus entity", [entities[i] + " ({})".format(counts[i]) for i in range(len(entities))])
    return _entity.split()[0]


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


@st.cache()
def get_entity_types_for_document(sentences: Iterable):
    return sorted(set([ent_t[0] for ent_t in get_db_connection().execute(
        """
        SELECT DISTINCT type
        FROM {0}
        WHERE sentence in {1}
        ORDER BY type
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.MEDICATION_ENTITY), tuple(s[0] for s in sentences))
    )]))


@st.cache()
def get_sentences_for_document(doc_id: str):
    return [(sents[0], sents[1]) for sents in get_db_connection().execute(
        """
        SELECT id, text
        FROM {0}
        WHERE document = {1}
        ORDER BY begin;
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.SENTENCE), doc_id)
    )]


@st.cache()
def get_annotators():
    return {anno[0]: anno[1] for anno in get_db_connection().execute(
        """
        SELECT DISTINCT {0}, id
        FROM {1}
        ORDER BY {0};
        """.format(const.LayerTypes.ANNOTATOR, const.LAYER_TNAME_DICT.get(const.LayerTypes.ANNOTATOR))
    )}


@st.cache()
def get_documents():
    return {doc[0]: doc[1] for doc in get_db_connection().execute(
        """
        SELECT DISTINCT {0}, id
        FROM {1}
        ORDER BY {0};
        """.format(const.LayerTypes.DOCUMENT, const.LAYER_TNAME_DICT.get(const.LayerTypes.DOCUMENT))
    )}


@st.cache(allow_output_mutation=True)
def get_db_connection():
    return sqlite3.connect("./tmp.db", check_same_thread=False)


@st.cache()
def create_temporary_db(db_file_io):
    print("Create temporary db file")
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
        doc_id = doc_dict.get(doc_name)
        # --> Entity Selection
        # -----> sent_list = list(tuple(sentence_id, sentence_text))
        sents_list = get_sentences_for_document(doc_id)
        # ----->
        entities_set = get_entity_types_for_document(sents_list)
        st.write(entities_set)
        #     # entity = create_selectbox_with_counts(_doc_entities, _doc_entity_counts)
        #     # fc_entity_color_only = st.sidebar.checkbox("Color only focus entity", False)
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
        # --> Sentence Selection
        sent_no = st.sidebar.slider("Sentence no.", 1, len(sents_list), 1)
#     #
#     # # ----- Document Agreement Visualization ----- #
#     # st.header("Agreement - Document " + str(doc_id) + " ({})".format(entity))
#     # display_document_agreement(_folder_root, _all_annotators, entity, doc_id, _index, match_type, threshold, boundary)
#     #
#     # # ----- Visualize Sentence Comparison ----- #
#     st.header("Comparison - Sentence " + str(sent_no))
#     sent_no -= 1
#     st.write(sentences[sent_no].get_covered_text())
#     st.write([e for e in get_entities(uima.MEDICATION_ENTITY, doc_id, annotators, data)])
#     # focus_entity = None
#     # if fc_entity_color_only:
#     #     focus_entity = entity
#     # display_sentence_comparison(annotators, _sentences, _triggers, _all_entities, sent_no, focus_entity)


main()
