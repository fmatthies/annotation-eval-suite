# -*- coding: utf-8 -*-

import io
import streamlit as st

from typing import Iterable
from spacy import displacy
from seaborn import color_palette

from deserialize import get_project_files
import uima
from uima import gather_annotations
from uima import load_cas_from_xmi, load_typesystem
from uima import MedicationEntity, MedicationAttribute


TYPE_SYSTEM_FILE_NAME = "TypeSystem.xml"
USERS_KEY = "users"
DOCUMENTS_KEY = "documents"
TYPE_SYSTEM_KEY = "type_system"
SENTENCE_TYPE = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence"


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


@st.cache
def get_entities(entity_type: str, document: str, user: str, data: dict):
    type_system = load_typesystem(str(data.get(TYPE_SYSTEM_KEY), 'utf-8'))
    cas = load_cas_from_xmi(str(data.get("{}-{}".format(document, user)), 'utf-8'), type_system)
    return [e for e in cas.select(entity_type)]


@st.cache
def get_all_sentences(document: str, data: dict) -> list:
    key = [k for k in data.keys() if k.startswith(document)][0]
    type_system = load_typesystem(str(data.get(TYPE_SYSTEM_KEY), 'utf-8'))
    cas = load_cas_from_xmi(str(data.get(key), 'utf-8'), type_system)
    return [s for s in cas.select(SENTENCE_TYPE)]


@st.cache(hash_funcs={io.BytesIO: hash})
def load_data(zip_file: str) -> dict:
    documents = list()
    users = set()
    data_dict = dict()
    for document, value in get_project_files(zip_file).items():
        if document == TYPE_SYSTEM_FILE_NAME:
            data_dict[TYPE_SYSTEM_KEY] = value.read()
        else:
            document = "".join(document.split(".")[:-1])
            documents.append(document)
            for user, xmi_bytes in value.items():
                user = "".join(user.split(".")[:-1])
                users.add(user)
                data_dict["{}-{}".format(document, user)] = xmi_bytes.read()

    data_dict[DOCUMENTS_KEY] = sorted(documents)
    data_dict[USERS_KEY] = sorted(users)
    return data_dict


def main():
    data = None
    # ----- Sidebar ----- #
    fis = st.sidebar.file_uploader("Upload test data")
    # Todo: implement deserializing from project zip file
    if fis is not None:
        data = load_data(fis)
        st.write(data)

    st.sidebar.subheader("General")
    # --> Document Selection
    doc_id = st.sidebar.selectbox("Select document", data.get(DOCUMENTS_KEY))
    # --> Entity Selection
    # _doc_entities, _doc_entity_counts = get_entities(_folder_root, _all_annotators, doc_id, _index)
    # entity = create_selectbox_with_counts(_doc_entities, _doc_entity_counts)
    # fc_entity_color_only = st.sidebar.checkbox("Color only focus entity", False)
    # # --> Agreement Properties
    # st.sidebar.subheader("Agreement Properties")
    # match_type = select_match_type()
    # threshold, boundary = 0, 0
    # if match_type == "one_all":
    #     threshold, boundary = get_threshold_boundary(_all_annotators)
    # --> Annotator Selection
    st.sidebar.subheader("Sentences")
    annotators = st.sidebar.multiselect("Select annotators", options=data.get(USERS_KEY), default=data.get(USERS_KEY))
    # --> Sentence Selection
    sentences = get_all_sentences(doc_id, data)
    sent_no = st.sidebar.slider("Sentence no.", 1, len(sentences), 1)
    #
    # # ----- Document Agreement Visualization ----- #
    # st.header("Agreement - Document " + str(doc_id) + " ({})".format(entity))
    # display_document_agreement(_folder_root, _all_annotators, entity, doc_id, _index, match_type, threshold, boundary)
    #
    # # ----- Visualize Sentence Comparison ----- #
    st.header("Comparison - Sentence " + str(sent_no))
    sent_no -= 1
    st.write(sentences[sent_no].get_covered_text())
    st.write([e.get_covered_text() for e in get_entities(uima.MEDICATION_ATTRIBUTE, doc_id, annotators[0], data)])
    # focus_entity = None
    # if fc_entity_color_only:
    #     focus_entity = entity
    # display_sentence_comparison(annotators, _sentences, _triggers, _all_entities, sent_no, focus_entity)


main()
