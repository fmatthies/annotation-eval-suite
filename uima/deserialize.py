import os
import zipfile
import io
import typing
from xml.etree import ElementTree
from collections import defaultdict

import config
import app_constants.constants as const


def get_project_files(zipped_file: str, type_system: str = const.WebAnnoExport.TYPE_SYSTEM)\
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


def get_layer_information_from_type_system(type_system: io.BytesIO, layer_fqn: dict):
    ns = "{http://uima.apache.org/resourceSpecifier}"
    et = ElementTree.parse(type_system)
    layers = {v: k for k, v in layer_fqn.items()}
    annotations = [gc for c in et.getroot() for gc in c if gc.find(ns+"name").text in layers.keys()]


if __name__ == "__main__":
    fi = os.path.abspath("../test/test-resources/test_project.zip")
    fi_dict = get_project_files(fi)
    get_layer_information_from_type_system(fi_dict.get("TypeSystem.xml"), config.layers)
