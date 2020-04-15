import os
import zipfile
import io
import typing
from collections import defaultdict


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
