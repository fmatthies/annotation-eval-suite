import os
import re
import zipfile
import io
import typing
import logging
from xmltodict3 import xml_to_dict
from collections import defaultdict
from aenum import Constant
from typing import Dict

import webanno_config
import app_constants.constants as const

logging.basicConfig(level=logging.INFO)


class DeserializeConstants(Constant):
    annotation = "annotation"
    relation = "relation"
    relation_identifier = "RelationTypeLink"
    webanno_custom = "webanno.custom"


class WebAnnoLayerType:
    def __init__(self, type_description: dict):
        self._fqn = type_description.get('name')
        self._features = {f.pop('name'): f for f in type_description.get('features').get('featureDescription')}
        self._type = DeserializeConstants.annotation
        if DeserializeConstants.relation_identifier.lower() in self.name.lower():
            self._type = DeserializeConstants.relation
        self._source = None
        self._target = None

    @property
    def name(self):
        return self._fqn.split(".")[-1]

    @property
    def fqn(self):
        return self._fqn

    @property
    def features(self):
        return self._features

    @property
    def of_type(self):
        return self._type

    @property
    def dependency(self):
        return self._target

    @dependency.setter
    def dependency(self, annotation):
        self._target = annotation

    @property
    def source(self):
        if self.of_type != DeserializeConstants.relation:
            logging.warning(" Tried to access 'source' property: "
                            "{} is not a relation and has no 'source'.".format(self._fqn))
        return self._source

    @source.setter
    def source(self, source):
        if self.of_type != DeserializeConstants.relation:
            logging.warning(" Tried to set 'source' property: "
                            "{} is not a relation and accepts no 'source'. "
                            "Continue without setting 'source'...".format(self._fqn))
        else:
            self._source = source


def get_project_files(zipped_file: str, type_system: str = "TypeSystem.xml")\
        -> typing.Dict[str, typing.Union[typing.Dict[str, io.BytesIO], io.BytesIO]]:
    xmi_dict = defaultdict(dict)
    doc_dict = dict()
    anno_dict = dict()
    anno_id = 0
    doc_id = 0
    type_system_file = None
    if zipfile.is_zipfile(zipped_file):
        with zipfile.ZipFile(zipped_file, 'r') as zfile:
            for z in zfile.namelist():
                if z.startswith(const.WebAnnoExport.ROOT) and z.endswith(const.WebAnnoExport.ZIP_ENDING):
                    root, doc, zip_name = z.split("/")
                    doc_name = os.path.splitext(doc)[0]
                    if doc_name not in doc_dict.keys():
                        doc_dict[doc_name] = str(doc_id)
                        doc_id += 1
                    inner_zip = io.BytesIO(zfile.read(z))
                    with zipfile.ZipFile(inner_zip, 'r') as inner_zfile:
                        for inner_z in inner_zfile.namelist():
                            if inner_z == type_system:
                                if type_system_file is None:
                                    type_system_file = io.BytesIO(inner_zfile.read(inner_z))
                                continue
                            anno_name = os.path.splitext(inner_z)[0]
                            if anno_name not in anno_dict.keys():
                                anno_dict[anno_name] = str(anno_id)
                                anno_id += 1
                            xmi_dict[doc_name][anno_name] = io.BytesIO(inner_zfile.read(inner_z))
    xmi_dict[type_system] = type_system_file
    xmi_dict["documents"] = doc_dict
    xmi_dict["annotators"] = anno_dict
    return xmi_dict


def resolve_relations(annotation: WebAnnoLayerType,
                      annotations: Dict[str, WebAnnoLayerType], relations: Dict[str, WebAnnoLayerType]):
    for feat_name, feat in annotation.features.items():
        relation = feat.get('elementType', None)
        if relation and relation in relations.keys():
            logging.info(" resolve '{} -> {}'".format(annotation.fqn, relation))
            relation_obj = relations.get(relation)
            target_fqn = relation_obj.features.get('target').get('rangeTypeName')
            dependency = annotations.get(target_fqn)

            annotation.dependency = dependency
            relation_obj.source = annotation
            relation_obj.dependency = dependency


def get_layer_information_from_type_system(type_system: typing.Union[io.BytesIO, str], layer_fqn: dict):
    annotations = {}
    relations = {}
    layers = {v: k for k, v in layer_fqn.items()}
    ts = type_system.read().decode('utf-8') if isinstance(type_system, io.BytesIO) else type_system
    xml_dict = xml_to_dict.XmlTextToDict(ts, ignore_namespace=True).get_dict()
    for annotation in xml_dict.get('typeSystemDescription').get('types').get('typeDescription'):
        if DeserializeConstants.webanno_custom.lower() in annotation.get('name').lower():  # this makes it regard only custom layers!
            wal = WebAnnoLayerType(annotation)
            if wal.fqn in layers.keys() and wal.of_type == DeserializeConstants.annotation:
                annotations[wal.fqn] = wal
            elif wal.of_type == DeserializeConstants.relation:
                relations[wal.fqn] = wal
    for anno in annotations.values():
        resolve_relations(anno, annotations, relations)

    return {"annotations": annotations, "relations": relations}


if __name__ == "__main__":
    fi = os.path.abspath("../test/uima-test-resources/test_project.zip")
    fi_dict = get_project_files(fi)
    info = get_layer_information_from_type_system(fi_dict.get("TypeSystem.xml"), webanno_config.layers)
    print(info)
