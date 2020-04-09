# -*- coding: utf-8 -*-

import collections
import sqlite3
import streamlit as st
from spacy import displacy
from seaborn import color_palette
from typing import List, Dict, Tuple, OrderedDict, Union

import app_constants.constants as const


def display_sentence_comparison(annotation_dict: dict, sentence: str, id2anno: dict,
                                e_focus: Union[None, str], a_focus: Union[None, str]):
    for annotator_id, entities_dict in annotation_dict.items():
        st.subheader(id2anno.get(annotator_id))
        st.write(
            return_html(sentence=sentence, entities=entities_dict, focus_entity=e_focus, focus_attribute=a_focus),
            unsafe_allow_html=True
        )


@st.cache()
def get_color_dict():
    entities = set()
    for anno_type in [const.LayerTypes.MEDICATION_ENTITY, const.LayerTypes.MEDICATION_ATTRIBUTE]:
        entities.update(set([ent_t[0] for ent_t in get_db_connection().execute(
            """
            SELECT DISTINCT type
            FROM {0};
            """.format(const.LAYER_TNAME_DICT.get(anno_type))
        )]))
    colors = color_palette('colorblind', len(entities)).as_hex()
    return {entity.upper(): color for entity, color in zip(entities, colors)}


@st.cache()
def return_html(sentence, entities, focus_entity, focus_attribute):
    ex = [{
        "text": sentence,
        "ents": [{
            "start": e.get("begin"),
            "end": e.get("end"),
            "label": e.get("type")
        } for e in entities.values()]
    }]
    colors = get_color_dict()
    focus_entity = focus_entity.upper() if focus_entity else None
    focus_attribute = focus_attribute.upper() if focus_attribute else None
    if focus_entity is not None or focus_attribute is not None:
        colors = {vk[0]: vk[1] for vk in colors.items()
                  if vk[0] == focus_entity or vk[0] == focus_attribute}
    return displacy.render(ex, style="ent", manual=True, minify=True, options={"colors": colors})


@st.cache()
def get_annotation_types_for_document(sentences: List, anno_layer: str) -> List[str]:
    where_clause = "WHERE sentence in {}".format(tuple(sentences))
    if len(sentences) == 1:
        where_clause = "WHERE sentence = '{}'".format(sentences[0])
    if len(sentences) == 0:
        return []
    return sorted(set([anno_t[0] for anno_t in get_db_connection().execute(
        """
        SELECT DISTINCT type
        FROM {0}
        {1}
        ORDER BY type;
        """.format(const.LAYER_TNAME_DICT.get(anno_layer), where_clause)
    )]))


@st.cache()
def get_sentences_for_document(doc_id: str) -> OrderedDict[str, str]:
    return collections.OrderedDict((sents[0], sents[1]) for sents in get_db_connection().execute(
        """
        SELECT id, text
        FROM {0}
        WHERE document = '{1}'
        ORDER BY begin;
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.SENTENCE), doc_id)
    ))


@st.cache()
def get_annotations_for_sentence(anno_ids: List[str], sent_id: str):
    where_and_clause = " AND annotator in {}".format(tuple(anno_ids))
    if len(anno_ids) == 1:
        where_and_clause = " AND annotator = '{}'".format(anno_ids[0])
    if len(anno_ids) == 0:
        return {}
    annotations = collections.defaultdict(dict)
    for result in get_db_connection().execute(
        """
        SELECT id, annotator, begin, end, type FROM {0}
        WHERE sentence = '{2}'{3}
        UNION ALL
        SELECT id, annotator, begin, end, type FROM {1}
        WHERE sentence = '{2}'{3}
        ORDER BY begin;
    """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.MEDICATION_ENTITY),
               const.LAYER_TNAME_DICT.get(const.LayerTypes.MEDICATION_ATTRIBUTE),
               sent_id, where_and_clause)):
        annotations[result[1]][result[0]] = {"begin": result[2], "end": result[3], "type": result[4]}
    return annotations


@st.cache()
def get_sentences_with_annotations(doc_id: str) -> List[str]:
    return [sents[0] for sents in get_db_connection().execute(
        """
        SELECT id
        FROM {0}
        WHERE document = '{1}' AND has_annotation = 1;
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.SENTENCE), doc_id)
    )]


@st.cache()
def get_annotators() -> Tuple[Dict[str, str], Dict[str, str]]:
    anno2id = {anno[0]: anno[1] for anno in get_db_connection().execute(
        """
        SELECT DISTINCT {0}, id
        FROM {1}
        ORDER BY {0};
        """.format(const.LayerTypes.ANNOTATOR, const.LAYER_TNAME_DICT.get(const.LayerTypes.ANNOTATOR))
    )}
    id2anno = {v: k for k, v in anno2id.items()}
    return anno2id, id2anno


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
        entities_set = get_annotation_types_for_document(sents_with_anno, const.LayerTypes.MEDICATION_ENTITY)
        focus_entity = st.sidebar.selectbox("Select focus entity", options=entities_set)
        fc_entity_color_only = st.sidebar.checkbox("Color only focus entity", False)
        attributes_set = get_annotation_types_for_document(sents_with_anno, const.LayerTypes.MEDICATION_ATTRIBUTE)
        focus_attribute = st.sidebar.selectbox("Select focus attribute", options=attributes_set)
        fc_attribute_color_only = st.sidebar.checkbox("Color only focus attribute", False)
        # --> Agreement Properties
        #     # st.sidebar.subheader("Agreement Properties")
        #     # match_type = select_match_type()
        #     # threshold, boundary = 0, 0
        #     # if match_type == "one_all":
        #     #     threshold, boundary = get_threshold_boundary(_all_annotators)
        st.sidebar.subheader("Sentences")
        # --> Annotator Selection
        # -----> anno2id_dict = dict(annotator_name: annotator_id)
        anno2id_dict, id2anno_dict = get_annotators()
        sel_annotators = [anno2id_dict.get(a_id) for a_id in
                          st.sidebar.multiselect("Select annotators",
                                                 options=list(anno2id_dict.keys()), default=list(anno2id_dict.keys()))]
        # ----- Document Agreement Visualization ----- #
        # ToDo: agreement calculation
        st.header("Document")
        if show_complete:
            st.write([s for s in sents_dict.values()])
        else:
            st.info("Select 'Show complete document' in the sidebar")
        # # ----- Visualize Sentence Comparison ----- #
        sent_id = sents_with_anno[0] if len(sents_with_anno) >= 1 else None
        # --> Sentence Selection
        if not sent_id:
            st.header("Sentences")
            st.sidebar.info("No sentences with annotations in this document")
            st.info("Sentence comparison not available")
        else:
            sent_no = st.sidebar.slider("Sentence selection", 1, len(sents_with_anno), 1)
            sent_id = sents_with_anno[sent_no - 1]
            st.header("Sentences (Nr: {})".format(str(sent_id.split("-")[-1])))
            annotation_dict = get_annotations_for_sentence(sel_annotators, sent_id)

            e_focus = None
            a_focus = None
            if fc_entity_color_only:
                e_focus = focus_entity
            if fc_attribute_color_only:
                a_focus = focus_attribute
            display_sentence_comparison(annotation_dict, sents_dict.get(sent_id), id2anno_dict, e_focus, a_focus)

main()
