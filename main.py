# -*- coding: utf-8 -*-

import io
from typing import Union, List, IO
from collections import defaultdict

import streamlit as st
from spacy import displacy
from seaborn import color_palette

import uima
import app_constants.constants as const
from deserialize import get_project_files


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


def get_annotations_for_sentence(document: str, sentence: int, user: str, data: dict):
    pass


def get_sentence_text(document: str, sentence: int, data: dict):
    return get_sentences_for_document(document, data)[sentence].covered_text()


def get_sentences_for_document(document: str, data: dict) -> list:
    return data.get(const.Keys.ANNOTATIONS)[document].get(const.Keys.SENTENCES)


def get_annotation_layer(cas: uima.Cas, layer: str) -> list:
    return [annotation for annotation in cas.select(layer)]


@st.cache(hash_funcs={io.BytesIO: hash})
def load_data(zip_file: str) -> dict:
    data_dict = dict()
    annotations = defaultdict(dict)
    documents_ids = set()
    user_ids = set()
    type_system = None
    # -> load type system first
    for document, value in get_project_files(zip_file).items():
        if document == const.FileNames.TYPE_SYSTEM:
            type_system = uima.load_typesystem(str(value.read(), 'utf-8'))
            data_dict[const.Keys.TYPE_SYSTEM] = type_system
            break
    if not type_system:
        # ToDo: implement error when no type system encountered
        pass
    # -> then analyze the CASes
    for document, value in get_project_files(zip_file).items():
        if document != const.FileNames.TYPE_SYSTEM:
            document = "".join(document.split(".")[:-1])
            documents_ids.add(document)
            annotations[document][const.Keys.SENTENCES] = None
            for user, xmi_bytes in value.items():
                user = "".join(user.split(".")[:-1])
                user_ids.add(user)
                cas = uima.load_cas_from_xmi(xmi_bytes, type_system)
                if annotations[document][const.Keys.SENTENCES] is None:
                    # -> add sentence layer annotation to data
                    annotations[document][const.Keys.SENTENCES] = get_annotation_layer(cas, const.LayerTypes.SENTENCE)
                # -> add annotation for different layers to specific user
                user_annotations = list()
                for layer, obj in uima.LAYER_DICT.items():
                    for anno in get_annotation_layer(cas, layer):
                        user_annotations.append(obj(anno, cas))
                annotations[document][user] = user_annotations

    data_dict[const.Keys.ANNOTATIONS] = annotations
    data_dict[const.Keys.DOCUMENT_ID] = sorted(documents_ids)
    data_dict[const.Keys.USER_ID] = sorted(user_ids)
    return data_dict


def main():
    data = None
    # ----- Sidebar ----- #
    fis = st.sidebar.file_uploader("Upload test data")
    if fis is not None:
        data = load_data(fis)
        st.write(data)

    st.sidebar.subheader("General")
    # --> Document Selection
    doc_id = st.sidebar.selectbox("Select document", data.get(const.Keys.DOCUMENT_ID))
#     # --> Entity Selection
#     # _doc_entities, _doc_entity_counts = get_entities(_folder_root, _all_annotators, doc_id, _index)
#     # entity = create_selectbox_with_counts(_doc_entities, _doc_entity_counts)
#     # fc_entity_color_only = st.sidebar.checkbox("Color only focus entity", False)
#     # # --> Agreement Properties
#     # st.sidebar.subheader("Agreement Properties")
#     # match_type = select_match_type()
#     # threshold, boundary = 0, 0
#     # if match_type == "one_all":
#     #     threshold, boundary = get_threshold_boundary(_all_annotators)
#     # --> Annotator Selection
#     st.sidebar.subheader("Sentences")
#     annotators = st.sidebar.multiselect("Select annotators", options=data.get(app_constants.Keys.USERS),
#                                         default=data.get(app_constants.Keys.USERS))
    # --> Sentence Selection
    sent_no = st.sidebar.slider("Sentence no.", 1, len(get_sentences_for_document(doc_id, data)), 1)
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
