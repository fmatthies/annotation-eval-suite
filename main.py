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


@st.cache
def has_document_index(folder_root):
    for _index in ["index", "index.txt", "Index", "Index.txt", "INDEX", "INDEX.txt"]:
        if os.path.exists(os.path.join(os.path.abspath(folder_root), _index)):
            return _index
    return False


@st.cache
def get_color_dict(entity_list):
    colors = color_palette('colorblind', len(entity_list)).as_hex()
    return {entity_list[i]: colors[i] for i in range(len(entity_list))}


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
def get_sentences(comparison_doc):
    sents, _ = zip(*comparison_doc.sent_compare_generator())
    return sents


@st.cache
def get_triggers(comparison_doc):
    _, triggers = zip(*comparison_doc.sent_compare_generator())
    return triggers


@st.cache
def load_data(folder_root, annotator_list):
    pass


@st.cache
def get_folder_root():
    return "test-resources"


def main():
    _folder_root = get_folder_root()
    _annotators = get_annotators(folder_root=_folder_root)

    annotators = st.multiselect("Select the annotators", options=_annotators, default=_annotators)
    doc_id = st.sidebar.selectbox("Document", get_documents(folder_root=_folder_root, annotators=annotators))

    if st.button("Load data"):
        load_data(folder_root=_folder_root, annotator_list=annotators)


main()
# if __name__ == "__main__":
#     alist = ["anno01", "anno02", "anno03", "anno04"]
#     froot = "test-resources"
#     findex = "index"
#     ent_list = ["MEDICATION", "ANAPHORA", "FREQUENCY", "DOSE", "REASON", "MODUS"]
#
#     comparison_batch = get_comparison_batch(froot, findex, alist)
#
#     doc_id = st.sidebar.selectbox("Document", sorted(comparison_batch.doc_list()))
#     comparison_doc = get_comparison_doc(comparison_batch, doc_id)
#
#     sentences = get_sentences(comparison_doc)
#     sent_no = st.sidebar.slider("Sentence No.", 1, len(sentences), 1)
#
#     st.header("Sentence " + str(sent_no))
#     sent_no -= 1
#     for a, v in get_triggers(comparison_doc)[sent_no].items():
#         st.subheader(a)
#         st.write(return_html(sentences[sent_no], v, ent_list), unsafe_allow_html=True)
