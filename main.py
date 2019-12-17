#!/home/matthies/workspaces/virtual_envs/bionlpformat_annotation/bin/python
# -*- coding: utf-8 -*-

import os
import streamlit as st

from compare import comparison
from spacy import displacy
from seaborn import color_palette


@st.cache(hash_funcs={comparison.BatchComparison: id})
def get_documents(froot, findex, alist):
    cbatch = comparison.BatchComparison(index=os.path.join(froot, findex), set_list=alist, root=os.path.join(froot))
    return cbatch


@st.cache
def get_color_dict(ent_list):
    colors = color_palette('colorblind', len(ent_list)).as_hex()
    return {ent_list[i]: colors[i] for i in range(len(ent_list))}


@st.cache
def get_sentences(folder_root, index_file, annotator_list):
    cdoc = get_documents(folder_root, index_file, annotator_list).get_comparison_obj(doc)
    sents, triggers = zip(*cdoc.sent_compare_generator())
    return sents, triggers


@st.cache
def return_html(sent, trigger, ent_list):
    ex = [{
        "text": sent,
        "ents": [{
            "start": t[2][0][0],
            "end": t[2][0][1],
            "label": t[1]
        } for t in trigger]
    }]
    return displacy.render(ex, style="ent", manual=True, minify=True, options={"colors": get_color_dict(ent_list)})


@st.cache
def get_doc_list(folder_root, index_file, annotator_list):
    ldoc = sorted(get_documents(folder_root, index_file, annotator_list).doc_list())
    return ldoc


alist = ["anno01", "anno02", "anno03", "anno04"]
froot = "test-resources"
findex = "index"
ent_list = ["MEDICATION", "ANAPHORA", "FREQUENCY", "DOSE", "REASON", "MODUS"]

doc = st.sidebar.selectbox("Document", list(get_doc_list(froot, findex, alist)))
sents, triggers = get_sentences(froot, findex, alist)
sent_no = st.sidebar.slider("Sentence No.", 1, len(sents), 1)

st.header("Sentence " + str(sent_no))
sent_no -= 1
for a, v in triggers[sent_no].items():
    st.subheader(a)
    st.write(return_html(sents[sent_no], v, ent_list), unsafe_allow_html=True)


@st.cache(hash_funcs={comparison.BatchComparison: id})
def get_comparison_batch(folder_root, index_file, annotator_list):



if __name__ == "__main__":
    comparison_batch = get_comparison_batch()
