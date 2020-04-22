# -*- coding: utf-8 -*-

import functools
import itertools
import collections
import sqlite3
import streamlit as st
import pandas as pd
from spacy import displacy
from seaborn import color_palette
from typing import List, Dict, Tuple, OrderedDict, Union

import app_constants.constants as const
from agreement import InstanceAgreement


# ToDo: replace table names with constants?


def display_sentence_comparison(sel_annotators: list, sent_id: str, doc_id: str,
                                e_focus: Union[None, str], a_focus: Union[None, str]):
    annotation_dict = annotations_for_sentence_for_anno_list([id_for_annotator(a) for a in sel_annotators], sent_id)
    for annotator_name in sel_annotators:
        annotator_id = id_for_annotator(annotator_name)
        if annotator_id not in annotation_dict.keys():
            entities_dict = {}
        else:
            entities_dict = annotation_dict.get(annotator_id)
        st.subheader(annotator_name)
        st.write(
            return_html(sentence=sentences_for_document(doc_id).get(sent_id),
                        entities=entities_dict, focus_entity=e_focus, focus_attribute=a_focus),
            unsafe_allow_html=True
        )


# def display_sentence_comparison(annotators: list, sent_id: str, doc_id: str,
#                                 e_focus: Union[None, str], a_focus: Union[None, str]):
#     annotator_ids: list = [id_for_annotator(a) for a in annotators]
#     annotation_ids: list = all_annotations_for_document(doc_id).get(sent_id).get("ids")
#     type_ids: list = all_annotations_for_document(doc_id).get(sent_id).get("types")
#     sentence_str: str = sentences_for_document(doc_id).get(sent_id)
#     for anno_id in annotator_ids:
#         mask = [True if (_id.split("-")[0] == anno_id) else False for _id in annotation_ids]
#         entities = annotation_information_for_ids(list(itertools.compress(annotation_ids, mask)),
#                                                   list(itertools.compress(type_ids, mask)))
#         st.write(
#             return_html(sentence=sentence_str, entities=entities, focus_entity=e_focus, focus_attribute=a_focus),
#             unsafe_allow_html=True
#         )


def is_drug_categorie(tid):
    return tid in drug_type_ids()


@st.cache()
def drug_type_ids():
    return [d[0] for d in db_connection().execute(
        """
        SELECT id
        FROM annotation_types
        WHERE type LIKE 'medikament%'
        """
    )]


@st.cache()
def return_html(sentence, entities, focus_entity, focus_attribute):
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
                       annotation_types_for_layer_id(id_for_layer(const.LayerTypes.MEDICATION_ENTITY))})
    if focus_attribute is not None:
        colors.update({vk[0]: vk[1] for vk in get_color_dict().items() if vk[0] == focus_attribute})
    else:
        colors.update({vk[0]: vk[1] for vk in get_color_dict().items() if vk[0].lower() in
                       annotation_types_for_layer_id(id_for_layer(const.LayerTypes.MEDICATION_ATTRIBUTE))})
    return displacy.render(ex, style="ent", manual=True, minify=True, options={"colors": colors})


# @st.cache()
# def annotation_information_for_ids(aid: Union[str, list], atype: Union[str, list]):
#     """
#
#     :param aid: list or string of an annotation id(s)
#     :param atype: list or string of the accompanying type id(s)
#     :return:
#     """
#     table = collections.defaultdict(list)
#     info = []
#     if isinstance(aid, str) and isinstance(atype, str):
#         aid = [aid]
#         atype = [atype]
#     for i in range(len(atype)):
#         if is_drug_categorie(atype[i]):
#             table["medication_entities"].append(aid[i])
#         else:
#             table["medication_attributes"].append(aid[i])
#
#     for t, v in table.items():
#         info.extend([{"id": i[0], "begin": i[1], "end": i[2], "type": i[3]} for i in db_connection().execute(
#             """
#             SELECT id, begin, end, type
#             FROM {0}
#             WHERE id in ({1})
#             ORDER BY begin;
#             """.format(t, ",".join("'{0}'".format(_id) for _id in v))
#         )])
#     return info


@st.cache()
def get_color_dict():
    entities = [e[0] for e in db_connection().execute(
        """
        SELECT type FROM annotation_types
        ORDER BY type;
        """
    )]
    colors = color_palette('colorblind', len(entities)).as_hex()
    return {entity.upper(): color for entity, color in zip(entities, colors)}


@st.cache()
def annotator_names() -> list:
    return [a[0] for a in db_connection().execute(
        """
        SELECT annotator
        FROM annotators
        ORDER BY annotator;
        """
    )]


@st.cache()
def document_titles() -> list:
    return [doc[0] for doc in db_connection().execute(
        """
        SELECT DISTINCT document
        FROM documents
        ORDER BY document;
        """
    )]


@st.cache()
def layer_for_id(lid: str):
    return [a[0] for a in db_connection().execute(
        """
        SELECT layer
        FROM layers
        WHERE id = '{}';
        """.format(lid)
    )][0]


@st.cache()
def id_for_layer(layer: str):
    return [a[0] for a in db_connection().execute(
        """
        SELECT id
        FROM layers
        WHERE layer = '{}';
        """.format(layer.lower())
    )][0]


@st.cache()
def annotation_type_for_id(annotation_id: str):
    return [a[0] for a in db_connection().execute(
        """
        SELECT type
        FROM annotation_types
        WHERE id = '{}';
        """.format(annotation_id)
    )][0]


@st.cache()
def id_for_annotation_type(annotation: str):
    return [a[0] for a in db_connection().execute(
        """
        SELECT id
        FROM annotation_types
        WHERE type = '{}';
        """.format(annotation.lower())
    )][0]


@st.cache()
def annotator_for_id(annotator_id: str):
    return [a[0] for a in db_connection().execute(
        """
        SELECT annotator
        FROM annotators
        WHERE id = '{}';
        """.format(annotator_id)
    )][0]


@st.cache()
def id_for_annotator(annotator: str):
    return [a[0] for a in db_connection().execute(
        """
        SELECT id
        FROM annotators
        WHERE annotator = '{}';
        """.format(annotator)
    )][0]


@st.cache()
def document_for_id(document_id: str):
    return [a[0] for a in db_connection().execute(
        """
        SELECT document
        FROM documents
        WHERE id = '{}';
        """.format(document_id)
    )][0]


@st.cache()
def id_for_document(document: str):
    return [a[0] for a in db_connection().execute(
        """
        SELECT id
        FROM documents
        WHERE document = '{}';
        """.format(document)
    )][0]


@st.cache()
def annotation_types_for_layer_id(lid: str):
    return [a[0] for a in db_connection().execute(
        """
        SELECT type
        FROM annotation_types
        WHERE layer = '{}';
        """.format(lid)
    )]


#
# @st.cache()
# def annotation_ids_for_document(sentences: List, anno_layer: str) -> List[str]:
#     where_clause = "WHERE sentence in {}".format(tuple(sentences))
#     if len(sentences) == 1:
#         where_clause = "WHERE sentence = '{}'".format(sentences[0])
#     if len(sentences) == 0:
#         return []
#     return sorted([anno_t[0] for anno_t in db_connection().execute(
#         """
#         SELECT DISTINCT type
#         FROM {0}
#         {1};
#         """.format(const.LAYER_TNAME_DICT.get(anno_layer), where_clause)
#     )])


@st.cache()
def sentences_for_document(doc_id: str) -> OrderedDict[str, str]:
    return collections.OrderedDict((sents[0], sents[1]) for sents in db_connection().execute(
        """
        SELECT id, text
        FROM {0}
        WHERE document = '{1}'
        ORDER BY begin;
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.SENTENCE), doc_id)
    ))


def annotations_for_sentence_for_anno_list(anno_ids: List[str], sent_id: str):
    annotations = {}
    for anno_id in set(anno_ids):
        annotations[anno_id] = annotations_for_sentence(anno_id, sent_id)
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
    for result in db_connection().execute(
            """
        SELECT id, begin, end, type
        FROM {0}
        WHERE sentence = '{2}' AND annotator = '{3}'
        UNION ALL
        SELECT id, begin, end, type
        FROM {1}
        WHERE sentence = '{2}' AND annotator = '{3}'
        ORDER BY begin;
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.MEDICATION_ENTITY),
                   const.LAYER_TNAME_DICT.get(const.LayerTypes.MEDICATION_ATTRIBUTE),
                   sent_id, anno_id)):
        annotations[result[0]] = {"begin": result[1], "end": result[2], "type": result[3]}
    return annotations


@st.cache()
def all_annotations_for_document(doc_id: str):
    return {row[1]: {"ids": row[0].split(","), "types": row[2].split(",")} for row in db_connection().execute(
        """
        SELECT group_concat(id), sentence, group_concat(type) 
        FROM
            (SELECT group_concat(id) as id, sentence, group_concat(type) as type
            FROM medication_entities
            WHERE document = '{0}'
            GROUP BY sentence
            UNION ALL
            SELECT group_concat(id), sentence, group_concat(type)
            FROM medication_attributes
            WHERE document = '{0}'
            GROUP BY sentence
            ORDER BY sentence)
        GROUP BY sentence
        """.format(doc_id))}


@st.cache()
def sentences_with_annotations(doc_id: str) -> List[str]:
    return [sents[0] for sents in db_connection().execute(
        """
        SELECT id
        FROM {0}
        WHERE document = '{1}' AND has_annotation = 1;
        """.format(const.LAYER_TNAME_DICT.get(const.LayerTypes.SENTENCE), doc_id)
    )]


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
            if combined_drugs and is_drug_categorie(type_id) and is_drug_categorie(tid):
                ids.append(id_id)
            elif tid == type_id:
                ids.append(id_id)
    return ids


def separate_annotations_by_annotators(annotation_ids: list, annotator_ids: list):
    return {anno_id: [anno for anno in annotation_ids if anno.split("-")[0] == anno_id] for anno_id in annotator_ids}


@st.cache(allow_output_mutation=True)
def instance_agreement_obj_for_document(doc_id: str):
    """
    :param doc_id:
    :return:
    """
    return InstanceAgreement(annotators=[id_for_annotator(a) for a in annotator_names()],
                             doc_id=doc_id, db_connection=db_connection())


@st.cache()
def instance_agreement(doc_id: str, instance: str, annotators: list, combined_drugs: bool = True):
    if instance is None:
        return 0
    instance_id = id_for_annotation_type(instance)
    annotators = [id_for_annotator(a) for a in annotators]
    ia = instance_agreement_obj_for_document(doc_id)
    table = const.LAYER_TNAME_DICT[const.LayerTypes.MEDICATION_ENTITY] if is_drug_categorie(instance_id) \
        else const.LAYER_TNAME_DICT[const.LayerTypes.MEDICATION_ATTRIBUTE]
    if combined_drugs and is_drug_categorie(instance_id):
        instance_id = drug_type_ids()
    return ia.agreement_fscore(instance_type=instance_id, annotators=annotators, table=table)


@st.cache(allow_output_mutation=True)
def db_connection() -> sqlite3.Connection:
    print("connect ...")
    return sqlite3.connect("./data_base_tmp/tmp.db", check_same_thread=False)


@st.cache()
def create_temporary_db(db_file_io) -> None:
    print("Create temporary db file ...")
    with open("./data_base_tmp/tmp.db", 'wb') as tmp:
        tmp.write(db_file_io.read())


def main():
    st.title("Annotation Visualizer")
    choice_desc = st.empty()
    choice_desc.info(
        """
        ### db file  
        Choose this if you have already created a database file from a WebAnno project  
        ### zip file
        Choose this if you just have an export of a WebAnno project
        """)
    upload_opt = st.empty()
    upload = upload_opt.radio("Upload db file or project zip?", ("db file", "zip file"))
    file_up = st.empty()
    fis = file_up.file_uploader("Upload db file" if upload == "db file" else "Upload zip file")
    if fis is not None:
        upload_opt.empty()
        file_up.empty()
        choice_desc.empty()
        create_temporary_db(fis)
        # ----- SIDEBAR ----- #
        st.sidebar.subheader("General")
        # --> Document Selection
        doc_name = st.sidebar.selectbox("Select document", document_titles())
        show_complete = st.sidebar.checkbox("Show complete document", False)
        doc_id = id_for_document(doc_name)
        # --> Annotation Selection
        # -----> sents_dict = OrderedDict(sentence_id: sentence_text)
        # -----> sents_with_anno = List(sentence_id)
        sents_with_anno = sentences_with_annotations(doc_id)
        # -----> Caching of "annotations for sentence" and "agreement":
        _ = [annotations_for_sentence_for_anno_list([id_for_annotator(a) for a in annotator_names()], sid)
             for sid in sents_with_anno]
        _ = instance_agreement_obj_for_document(doc_id)
        # ---> Set of annotation categories
        annotation_types = set(functools.reduce(
            lambda x, y: x + y, [_id_type.get("types")
                                 for _id_type in all_annotations_for_document(doc_id).values()], []
        ))
        focus_entity = \
            st.sidebar.selectbox("Select focus entity",
                                 options=[annotation_type_for_id(e).title() for e in annotation_types
                                          if annotation_type_for_id(e).lower().startswith("medikament")])
        fc_entity_color_only = st.sidebar.checkbox("Color only focus entity", False)
        focus_attribute = \
            st.sidebar.selectbox("Select focus attribute",
                                 options=[annotation_type_for_id(e).title() for e in annotation_types
                                          if not annotation_type_for_id(e).lower().startswith("medikament")])
        fc_attribute_color_only = st.sidebar.checkbox("Color only focus attribute", False)
        # --> Agreement Properties
        st.sidebar.subheader("Agreement Properties")
        combined_drugs = st.sidebar.checkbox("Treat all drug annotations as one type", True)
        use_only_selected_annotators = st.sidebar.checkbox(
            "Use only selected annotators under 'Sentences' for agreement calculation", True)
        #     # match_type = select_match_type()
        #     # threshold, boundary = 0, 0
        #     # if match_type == "one_all":
        #     #     threshold, boundary = get_threshold_boundary(_all_annotators)
        st.sidebar.subheader("Sentences")
        # --> Annotator Selection
        sel_annotators = st.sidebar.multiselect("Select annotators",
                                                options=annotator_names(), default=annotator_names())

        # ----- DOCUMENT AGREEMENT VISUALIZATION ----- #
        # ToDo: agreement calculation
        st.header("Document")
        if show_complete:
            st.write([s for s in sentences_for_document(doc_id).values()])
        else:
            st.info("Select 'Show complete document' in the sidebar")
        # # ----- Visualize Agreement Scores ----- #
        st.header("Agreement")
        agreement_annotators = sel_annotators if use_only_selected_annotators else annotator_names()
        if len(agreement_annotators) <= 1:
            st.info("For agreement calculation more than one annotator must be selected")
        else:
            entity_index = "Medikamente" if combined_drugs else " ".join(focus_entity.split()[1:])
            ia_drug = instance_agreement(doc_id, focus_entity, agreement_annotators, combined_drugs)
            ia_attr = instance_agreement(doc_id, focus_attribute, agreement_annotators)
            st.write(pd.DataFrame(data={"instance": [ia_drug, ia_attr], "token": ["None", "None"]},
                                  index=[entity_index, focus_attribute]))
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

            e_focus = None
            a_focus = None
            if fc_entity_color_only:
                e_focus = focus_entity
            if fc_attribute_color_only:
                a_focus = focus_attribute
            display_sentence_comparison(sel_annotators, sent_id, doc_id, e_focus, a_focus)


main()
