# -*- coding: utf-8 -*-

import pathlib
import functools
import collections
import itertools
import sqlite3
import time

import streamlit as st
import pandas as pd
from spacy import displacy
from seaborn import color_palette
from typing import List, OrderedDict, Union, Dict, Set, Tuple

import SessionState
from agreement import InstanceAgreement, TokenAgreement

# ToDo: replace table names with constants?
from app_constants.base_config import DatabaseCategories, DefaultTableNames, layers


def display_sentence_comparison(sel_annotators: list, sent_id: str, doc_id: str,
                                e_focus: Union[None, str], a_focus: Union[None, str], disp_sents: list,
                                columns: int):
    sent_tuple = (sent_id, set(disp_sents))
    annotation_dict = annotations_for_sentence_for_anno_list([id_for_annotator(a) for a in sel_annotators], sent_tuple,
                                                             session.allow_disp_sent)
    anno_cols = st.beta_columns(columns)
    for i, annotator_name in enumerate(sel_annotators):
        annotator_id = id_for_annotator(annotator_name)
        _sent_ann_id = f"{sent_id}-{annotator_id}"
        if (_sent_ann_id not in disp_sents) and (len(disp_sents[0].split("-")) >= 3):
            continue
        _sent_id = _sent_ann_id if (len(disp_sents) > 1 or _sent_ann_id in disp_sents) else sent_id
        entities_dict = annotation_dict.get(annotator_id, {})
        sentence = sentences_for_document(doc_id).get(_sent_id)
        col = i % columns
        anno_cols[col].subheader(annotator_name)
        anno_cols[col].write(
            return_entity_html(sentence=sentence,
                               entities=entities_dict, focus_entity=e_focus, focus_attribute=a_focus),
            unsafe_allow_html=True
        )


def is_entity_categorie(tid):
    return tid in entity_type_ids()


@st.cache()
def reversed_layers():
    return {x: y for y, x in layers.items()}


@st.cache()
def entity_type_ids():
    res = [d[0] for d in session.db_connection.execute(
        """
        SELECT id
        FROM annotation_types
        WHERE layer IS {}
        """.format(id_for_layer("entities"))
    ) if len(d) >= 1]
    return res


@st.cache()
def entity_names_in_document(annotation_names, sort=False):
    _ents = [annotation_type_for_id(e).title() for e in annotation_names
             if layer_for_id(layer_for_annotation_type_id(e)).lower() == "entities"]
    return _ents if not sort else sorted(_ents)


@st.cache()
def event_names_in_document(annotation_names, sort=False):
    _evts = [annotation_type_for_id(e).title() for e in annotation_names
             if layer_for_id(layer_for_annotation_type_id(e)).lower() == "events"]
    return _evts if not sort else sorted(_evts)


@st.cache()
def event_type_ids():
    res = [d[0] for d in session.db_connection.execute(
        """
        SELECT id
        FROM annotation_types
        WHERE layer IS {}
        """.format(id_for_layer("events"))
    ) if len(d) >= 1]
    return res


@st.cache()
def return_entity_html(sentence, entities, focus_entity, focus_attribute):
    ex = [{
        "text": sentence,
        "ents": [{
            "start": e.get("begin"),
            "end": e.get("end"),
            "label": annotation_type_for_id(e.get("type"))
        } for e in entities.values()]
    }]
    focus_entity = focus_entity.upper() if focus_entity else None
    focus_attribute = focus_attribute.upper() if focus_attribute else None
    colors = {}
    if focus_entity is not None:
        colors.update({vk[0]: vk[1] for vk in get_color_dict().items() if vk[0] == focus_entity})
    else:
        colors.update({vk[0]: vk[1] for vk in get_color_dict().items() if vk[0].lower() in
                       annotation_types_for_layer_id(id_for_layer(DatabaseCategories.entities))})
    if focus_attribute is not None:
        colors.update({vk[0]: vk[1] for vk in get_color_dict().items() if vk[0] == focus_attribute})
    else:
        colors.update({vk[0]: vk[1] for vk in get_color_dict().items() if vk[0].lower() in
                       annotation_types_for_layer_id(id_for_layer(DatabaseCategories.events))})
    return displacy.render(ex, style="ent", manual=True, minify=True, options={"colors": colors})


# @st.cache()
def return_relation_html():
    rel = {
        "words": [
            {"text": "This", "tag": "Medikament"},
            {"text": "is", "tag": ""},
            {"text": "a", "tag": ""},
            {"text": "sentence", "tag": "Grund"}
        ],
        "arcs": [
            {"start": 3, "end": 0, "label": "", "dir": "right"}
        ]
    }
    # words = "Have me some text".split()
    # svg = svg_drawing.Drawing()
    # x_last = 0
    # for i, w in enumerate(words):
    #     txt = svg_text.Text(w, insert=(x_last, 25))
    #     svg.add(txt)
    #     x_last += len(w) * 10 + 5
    # return svg.tostring()
    return displacy.render(rel, style="dep", manual=True, minify=True,
                           options={"compact": True, "distance": 75})


@st.cache()
def get_color_dict():
    entities = [e[0] for e in session.db_connection.execute(
        """
        SELECT type FROM annotation_types
        ORDER BY type;
        """
    ) if len(e) >= 1]
    colors = color_palette('colorblind', len(entities)).as_hex()
    return {entity.upper(): color for entity, color in zip(entities, colors)}


@st.cache()
def annotator_names() -> list:
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT annotator
        FROM annotators
        ORDER BY annotator;
        """
    ) if len(a) >= 1]
    return res


@st.cache()
def document_titles() -> list:
    res = [doc[0] for doc in session.db_connection.execute(
        """
        SELECT DISTINCT document
        FROM documents
        ORDER BY document;
        """
    ) if len(doc) >= 1]
    return res


@st.cache()
def annotation_types() -> list:
    res = [a_type[0] for a_type in session.db_connection.execute(
        """
        SELECT id
        FROM annotation_types
        """
    ) if len(a_type) >= 1]
    return res


@st.cache()
def layer_for_annotation_type_id(a_id: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT layer
        FROM annotation_types
        WHERE id = '{}';
        """.format(a_id)
    ) if len(a) >= 1]
    return res[0] if len(res) >= 1 else None


@st.cache()
def layer_for_id(lid: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT layer
        FROM layers
        WHERE id = '{}';
        """.format(lid)
    ) if len(a) >= 1]
    return res[0] if len(res) >= 1 else None


@st.cache()
def id_for_layer(layer: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT id
        FROM layers
        WHERE layer = '{}';
        """.format(layer.lower())
    ) if len(a) >= 1]
    return res[0] if len(res) >= 1 else None


@st.cache()
def annotation_type_for_id(annotation_id: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT type
        FROM annotation_types
        WHERE id = '{}';
        """.format(annotation_id)
    ) if len(a) >= 1]
    return res[0] if len(res) >= 1 else None


@st.cache()
def id_for_annotation_type(annotation: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT id
        FROM annotation_types
        WHERE type = '{}';
        """.format(annotation.lower())
    ) if len(a) >= 1]
    return res[0] if len(res) >= 1 else None


@st.cache()
def annotator_for_id(annotator_id: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT annotator
        FROM annotators
        WHERE id = '{}';
        """.format(annotator_id)
    ) if len(a) >= 1]
    return res[0] if len(res) >= 1 else None


@st.cache()
def id_for_annotator(annotator: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT id
        FROM annotators
        WHERE annotator = '{}';
        """.format(annotator)
    ) if len(a) >= 1]
    return res[0] if len(res) >= 1 else None


@st.cache()
def document_for_id(document_id: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT document
        FROM documents
        WHERE id = '{}';
        """.format(document_id)
    ) if len(a) >= 1]
    return res[0] if len(res) >= 1 else None


@st.cache()
def id_for_document(document: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT id
        FROM documents
        WHERE document = '{}';
        """.format(document)
    ) if len(a) >= 1]
    return res[0] if len(res) >= 1 else None


@st.cache()
def annotation_types_for_layer_id(lid: str):
    res = [a[0] for a in session.db_connection.execute(
        """
        SELECT type
        FROM annotation_types
        WHERE layer = '{}';
        """.format(lid)
    ) if len(a) >= 1]
    return res


@st.cache()
def sentences_for_document(doc_id: str) -> OrderedDict[str, str]:
    # ToDo: try to merge sentences that are exactly the same in case of disparate sentences... very low prio
    # _ordered_dict = collections.OrderedDict()
    # _iter = itertools.cycle(session.db_connection.execute(
    #     """
    #     SELECT id, text
    #     FROM {0}
    #     WHERE document = '{1}'
    #     ORDER BY begin;
    #     """.format(DefaultTableNames.sentences, doc_id)
    # ))
    # next_iter = next(_iter)
    # start_id = next_iter[0]
    # while True:
    #     (this_id, this_sent), next_iter = next_iter, next(_iter)
    #     next_id, next_sent = next_iter
    #     ###
    #     if len(this_id.split("-")) >= 3 and this_id.split("-")[:-1] == next_id.split("-")[:-1]:
    #     ###
    #     if start_id == next_id:
    #         break
    return collections.OrderedDict((sents[0], sents[1]) for sents in session.db_connection.execute(
        """
        SELECT id, text
        FROM {0}
        WHERE document = '{1}'
        ORDER BY begin;
        """.format(DefaultTableNames.sentences, doc_id)
    ))


def annotations_for_sentence_for_anno_list(anno_ids: List[str],
                                           sent_tuple: Tuple[str, Set[str]],
                                           allow_disp: bool = False):
    annotations = {}
    sent_base_id = sent_tuple[0]
    _sent_id = sent_base_id
    for anno_id in set(anno_ids):
        if allow_disp:
            _sent_ann_id = f"{sent_base_id}-{anno_id}"
            if (_sent_ann_id not in sent_tuple[1]) and (len(sent_tuple[0].split("-")) >= 3):
                continue
            _sent_id = _sent_ann_id if (len(sent_tuple) > 1 or _sent_ann_id in sent_tuple) else sent_base_id
        annotations[anno_id] = annotations_for_sentence(anno_id, _sent_id)
    return annotations


@st.cache()
def annotations_for_sentence(anno_id: str, sent_id: str):
    # ToDo: stupid slow down because this gets executed for every combination of annotators...
    """
    Returns a dictionary of annotator `ids` as keys with a dictionary as value that has itself a
    SpaCy compliant entity visualization dictionary as value and the entity `id` as key

    :param anno_id: the id of the chosen annotator
    :param sent_id: the id of the chosen sentence
    :return:
    """
    # where_and_clause = " AND annotator in {}".format(tuple(anno_id))
    # if len(anno_id) == 1:
    #     where_and_clause = " AND annotator = '{}'".format(anno_id[0])
    # if len(anno_id) == 0:
    #     return {}
    annotations = {}
    cmd_str = ""
    # ToDo: no hard-coded list -> use a conf entry for annotation entities
    for _l in ["entities", "events"]:
        if _l not in reversed_layers():  # .keys():
            continue
        cmd_str += """
        SELECT id, begin, end, type
        FROM {0}
        WHERE sentence = '{1}' AND annotator = '{2}'
        UNION ALL
        """.format(reversed_layers()[_l], sent_id, anno_id)
    cmd_str = cmd_str.rpartition("UNION ALL")[0]
    cmd_str += "\nORDER BY begin;"
    for result in session.db_connection.execute(cmd_str):
        annotations[result[0]] = {"begin": result[1], "end": result[2], "type": result[3]}
    return annotations


@st.cache()
def all_annotations_for_document(doc_id: str):
    cmd_str = """
    SELECT group_concat(id), sentence, group_concat(type) 
    FROM
    (
    """
    # ToDo: no hard-coded list -> use a conf entry for annotation entities
    for _l in ["entities", "events"]:
        if _l not in reversed_layers():  # .keys():
            continue
        cmd_str += """
        SELECT group_concat(id) as id, sentence, group_concat(type) as type
        FROM {0}
        WHERE document = '{1}'
        GROUP BY sentence
        UNION ALL""".format(reversed_layers()[_l], doc_id)
    cmd_str = cmd_str.rpartition("UNION ALL")[0]
    cmd_str += "\nORDER BY sentence)\nGROUP BY sentence"
    return {row[1]: {"ids": row[0].split(","), "types": row[2].split(",")}
            for row in session.db_connection.execute(cmd_str)}


@st.cache()
def sentences_with_annotations(doc_id: str) -> Dict[str, Set[str]]:
    _return = collections.defaultdict(set)
    for sents in session.db_connection.execute(
            """
            SELECT id
            FROM {0}
            WHERE document = '{1}' AND has_annotation = 1;
            """.format(DefaultTableNames.sentences, doc_id)):
        sent_id_parts = sents[0].split("-")
        _return["-".join(sent_id_parts[:-1] if len(sent_id_parts) >= 3 else sent_id_parts[:])].add(sents[0])
    return _return


@st.cache()
def sentences_with_annotation_type(doc_id: str, anno_type: str):
    # ToDo: for showing only sentences in a doc that have the selected annotation
    anno_as_id = id_for_annotation_type(anno_type)
    table = reversed_layers()["entities" if is_entity_categorie(anno_as_id) else "events"]

    _sents = [sents[0] for sents in session.db_connection.execute(
        """
        SELECT sentence
        FROM {0}
        WHERE type = '{1}';
        """.format(table, anno_as_id)
    )]
    return {s_id: s_set for s_id, s_set in sentences_with_annotations(doc_id).items() if s_id in _sents}


@st.cache()
def doc_annotations_for_type(tid: str, doc_id: str, combined_drugs: bool = True):
    """

    :param tid: id of the annotation type
    :param doc_id: id of the document
    :param combined_drugs: whether all sub categories of the drugs should be handled as one
    :return:
    """
    ids = list()
    for id_types in all_annotations_for_document(doc_id).values():
        for i in range(len(id_types.get("ids"))):
            type_id = id_types.get("types")[i]
            id_id = id_types.get("ids")[i]
            if combined_drugs and is_entity_categorie(type_id) and is_entity_categorie(tid):
                ids.append(id_id)
            elif tid == type_id:
                ids.append(id_id)
    return ids


def separate_annotations_by_annotators(annotation_ids: list, annotator_ids: list):
    return {anno_id: [anno for anno in annotation_ids if anno.split("-")[0] == anno_id] for anno_id in annotator_ids}


@st.cache(allow_output_mutation=True, hash_funcs={sqlite3.Connection: id})
def instance_agreement_obj_for_document(doc_id: str):
    """
    :param doc_id:
    :return:
    """
    return InstanceAgreement(annotators=[id_for_annotator(a) for a in annotator_names()],
                             doc_id=doc_id, db_connection=session.db_connection)


@st.cache(allow_output_mutation=True, hash_funcs={sqlite3.Connection: id})
def token_agreement_obj_for_document(doc_id: str):
    """
    :param doc_id:
    :return:
    """
    return TokenAgreement(annotators=[id_for_annotator(a) for a in annotator_names()],
                          doc_id=doc_id, db_connection=session.db_connection)


@st.cache(hash_funcs={sqlite3.Connection: id})
def instance_agreement(doc_id: str, instance: str, annotators: list,
                       combined_entities: bool = True, combined_attributes: bool = False):
    # ToDo: combined_ents will never matter if combined_attrs is True
    if instance is None:
        return 0
    instance_id = id_for_annotation_type(instance)
    annotators = [id_for_annotator(a) for a in annotators]
    ia = instance_agreement_obj_for_document(doc_id)
    table = reversed_layers()["entities"] if is_entity_categorie(instance_id) \
        else reversed_layers()["events"]
    if combined_entities and is_entity_categorie(instance_id):
        instance_id = entity_type_ids()
    if combined_attributes and not is_entity_categorie(instance_id):
        instance_id = set(annotation_types()).difference(entity_type_ids())
    return ia.agreement_fscore(instance_type=instance_id, annotators=annotators, table=table)


@st.cache(hash_funcs={sqlite3.Connection: id})
def token_agreement(doc_id: str, instance: str, annotators: list,
                    combined_entities: bool = True, combined_attributes: bool = False):
    # ToDo: combined_ents will never matter if combined_attrs is True
    if instance is None:
        return 0
    instance_id = id_for_annotation_type(instance)
    annotators = [id_for_annotator(a) for a in annotators]
    ta = token_agreement_obj_for_document(doc_id)
    table = reversed_layers()["entities"] if is_entity_categorie(instance_id) \
        else reversed_layers()["events"]
    if combined_entities and is_entity_categorie(instance_id):
        instance_id = entity_type_ids()
    if combined_attributes and not is_entity_categorie(instance_id):
        instance_id = set(annotation_types()).difference(entity_type_ids())
    return ta.agreement_fscore(instance_type=instance_id, annotators=annotators, table=table)


def highlight_row(row: pd.Series, foci: list):
    return ['background-color: grey'] * len(row) if row.name.lower() in [f.lower() for f in foci if f is not None] \
        else ['background-color: white'] * len(row)


# @st.cache(allow_output_mutation=True)
# def session.db_connection -> sqlite3.Connection:
#     print("connect ...")
#     return sqlite3.connect("./data_base_tmp/tmp.db", check_same_thread=False)


# @st.cache()
def create_temporary_db(file_io, is_db_file) -> sqlite3.Connection:
    print(f"Created temporary db file under '{temp_db_file.resolve()}'")
    if temp_db_file.exists():
        temp_db_file.open('w').close()
        time.sleep(0.5)
    with temp_db_file.open('wb') as tmp:
        if is_db_file:
            tmp.write(file_io.read())
        else:
            #  ToDo: transform to sqlite db
            pass
    return sqlite3.connect(temp_db_file.resolve(), check_same_thread=False)


def main():
    st.title("Annotation Visualizer")

    choice_desc = st.empty()
    allow_disp_sent = st.empty()
    upload_opt = st.empty()
    file_up = st.empty()
    continue_btn = st.empty()

    if not session.file_upload and not session.db_connection:
        choice_desc.info(
            """
            ### db file  
            Choose this if you have already created a database file from a WebAnno project  
            ### zip file
            Choose this if you just have an export of a WebAnno project
            ### project folder
            Choose this if you just have a Brat project folder 
            
            ### Allow disparate sentences
            (Warning!) Check this only if you compare annotations that have differing sentences (e.g. for de-id replacement).
            Don't check this if you don't know what this means. Only for visualization purposes.
            """)
        session.upload_type = upload_opt.radio("Upload db file, project zip or project folder?",
                                               ("db file", "zip file", "project folder"))
        session.allow_disp_sent = allow_disp_sent.checkbox("(!Warning!) Allow disparate Sentences")
        session.file_upload = file_up.file_uploader("Upload db file" if session.upload_type == "db file"
                                                    else ("Upload zip file" if session.upload_type == "zip file" else
                                                          "Upload project folder"))
        continue_btn.button("Continue")
        if session.file_upload:
            session.db_connection = create_temporary_db(session.file_upload, session.upload_type == "db file")

    elif session.file_upload and session.db_connection:
        choice_desc.empty()
        upload_opt.empty()
        file_up.empty()

        # ----- SIDEBAR ----- #
        st.sidebar.subheader("General")
        # --> Document Selection
        doc_name = st.sidebar.selectbox("Select document", document_titles())
        doc_id = id_for_document(doc_name)

        # --> Annotation Selection
        sents_with_anno = sentences_with_annotations(doc_id)
        # -----> Caching of "annotations for sentence" and "agreement":
        _ = [annotations_for_sentence_for_anno_list([id_for_annotator(a) for a in annotator_names()], (sid, s_set),
                                                    allow_disp=session.allow_disp_sent)
             for sid, s_set in sents_with_anno.items()]
        _ = instance_agreement_obj_for_document(doc_id)
        _ = token_agreement_obj_for_document(doc_id)

        # --> Set of annotation categories
        annotation_types = set(functools.reduce(
            lambda x, y: x + y, [_id_type.get("types")
                                 for _id_type in all_annotations_for_document(doc_id).values()], []
        ))
        focus_entity = \
            st.sidebar.selectbox("Select focus entity", options=entity_names_in_document(annotation_types))
        fc_sentence_with_ents_only = st.sidebar.checkbox("Show only sentences with focus entity", False)
        fc_entity_color_only = st.sidebar.checkbox("Color only focus entity", False)
        focus_attribute = \
            st.sidebar.selectbox("Select focus event", options=event_names_in_document(annotation_types))
        fc_sentence_with_evts_only = st.sidebar.checkbox("Show only sentences with focus event", False)
        fc_attribute_color_only = st.sidebar.checkbox("Color only focus event", False)

        # --> Agreement Properties
        st.sidebar.subheader("Agreement Settings")
        # combined_entities = st.sidebar.checkbox("All entities are one type", True)
        # combined_attributes = st.sidebar.checkbox("All events are one type", False)
        collapse_agreements = st.sidebar.checkbox("Collapse Agreement Scores", False)
        use_only_selected_annotators = st.sidebar.checkbox("Use only selected annotators", True)

        # --> Annotator Selection
        st.sidebar.subheader("Sentences")
        sel_annotators = st.sidebar.multiselect("Select annotators",
                                                options=annotator_names(), default=annotator_names())
        ann_cols = 1
        if len(sel_annotators) > 1:
            ann_cols = st.sidebar.slider("Sentence columns", min_value=1, max_value=min(3, len(sel_annotators)),
                                         value=min(2, len(sel_annotators)))

        # ----- DOCUMENT AGREEMENT VISUALIZATION ----- #
        st.header("Document")
        with st.beta_expander("Complete Document Text"):
            st.text("\n".join([f"{_id}: {s}" for _id, s in sentences_for_document(doc_id).items()]))

        # # ----- Visualize Agreement Scores ----- #
        vis_anno = "all" if not use_only_selected_annotators else ", ".join(sel_annotators)
        st.header("Agreement ({})".format(vis_anno))
        with st.beta_expander("Show Agreement", expanded=True):
            agreement_annotators = sel_annotators if use_only_selected_annotators else annotator_names()
            if len(agreement_annotators) <= 1:
                st.info("For agreement calculation more than one annotator must be selected")
            else:
                ia_entity = instance_agreement(doc_id, focus_entity, agreement_annotators)
                ta_entity = token_agreement(doc_id, focus_entity, agreement_annotators)
                ia_event = instance_agreement(doc_id, focus_attribute, agreement_annotators,
                                              combined_entities=False, combined_attributes=True)
                ta_event = token_agreement(doc_id, focus_attribute, agreement_annotators,
                                           combined_entities=False, combined_attributes=True)
                if collapse_agreements:
                    _index = ["++(Entities)++", "+++(Events)+++"]
                    _data = {"instance": [ia_entity, ia_event], "token": [ta_entity, ta_event]}
                else:
                    _ent_names = entity_names_in_document(annotation_types, sort=True)
                    _ev_names = event_names_in_document(annotation_types, sort=True)
                    _index = ["--(Entities)--"] + _ent_names + ["---(Events)---"] + _ev_names
                    _data = {
                        "instance": [ia_entity] + [instance_agreement(doc_id, _foc, agreement_annotators, False, False)
                                                   for _foc in _ent_names] + [ia_event] + [
                                        instance_agreement(doc_id, _foc, agreement_annotators, False, False) for _foc in
                                        _ev_names],
                        "token": [ta_entity] + [token_agreement(doc_id, _foc, agreement_annotators, False, False) for
                                                _foc in _ent_names] + [ta_event] + [
                                     token_agreement(doc_id, _foc, agreement_annotators, False, False) for _foc in
                                     _ev_names]}

                agr_df = pd.DataFrame(data=_data, index=_index)
                _, agr_col_1, _, agr_col_2, _ = st.beta_columns((5, 5, 2, 15, 5))
                agr_rounded_to = agr_col_1.slider("Round to", 1, 4, 2)
                agr_col_2.dataframe(agr_df.style.apply(
                    lambda x: highlight_row(x, [focus_attribute, focus_entity]), axis=1)
                                    .format("{:." + str(agr_rounded_to) + "f}"),
                                    height=25 * len(_index) + 25)

        # # ----- Visualize Sentence Comparison ----- #
        if fc_sentence_with_ents_only:
            _focus = focus_entity
        elif fc_sentence_with_evts_only:
            _focus = focus_attribute
        else:
            _focus = False
        _sents_showing = sents_with_anno if not _focus else sentences_with_annotation_type(doc_id, _focus)
        sent_id = list(_sents_showing.keys())[0] if len(_sents_showing) >= 1 else None
        # --> Sentence Selection
        if not sent_id:
            st.header("Sentences & Annotators")
            st.sidebar.info("No sentences with annotations in this document")
            st.info("Sentence comparison not available")
        else:
            sent_id_prefix = "-".join(sent_id.split("-")[:-1])
            st.header("Sentences")
            _, _slider, _ = st.beta_columns((0.25, 4, 10))
            with _slider:
                _options = [_id.split("-")[-1] for _id in _sents_showing.keys()]
                _sent = _options[0]
                if len(_sents_showing) > 1:
                    _sent = st.select_slider("", options=_options)
            sent_id = "-".join([sent_id_prefix, _sent])
            disp_sent = list(_sents_showing[sent_id])

            e_focus = None
            a_focus = None
            if fc_entity_color_only:
                e_focus = focus_entity
            if fc_attribute_color_only:
                a_focus = focus_attribute
            display_sentence_comparison(sel_annotators, sent_id, doc_id, e_focus, a_focus, disp_sent, ann_cols)


temp_db_file = pathlib.Path("./data_base_tmp/tmp.db")
session = SessionState.get(db_connection='', file_upload='', upload_type='')
st.set_page_config(layout="wide", page_icon="🧰", page_title="Annotation Visualizer")
main()
