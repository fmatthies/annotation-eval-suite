import zipfile
import io
import typing
from collections import defaultdict

ROOT_NAME = "annotation/"
ZIP_ENDING = ".zip"
TYPE_SYSTEM_FILE_NAME = "TypeSystem.xml"


def get_project_files(zipped_file: str, type_system: str = TYPE_SYSTEM_FILE_NAME)\
        -> typing.Dict[str, typing.Union[typing.Dict[str, io.BytesIO], io.BytesIO]]:
    """

    :param zipped_file:
    :param type_system:
    :return: a dictionary with the TypeSystem as io.BytesIO and
     all documents with each individual annotator files as io.BytesIO
    """
    xmi_dict = defaultdict(dict)
    type_system_file = None
    if zipfile.is_zipfile(zipped_file):
        with zipfile.ZipFile(zipped_file, 'r') as zfile:
            for z in zfile.namelist():
                if z.startswith(ROOT_NAME) and z.endswith(ZIP_ENDING):
                    root, doc, zip_name = z.split("/")
                    inner_zip = io.BytesIO(zfile.read(z))
                    with zipfile.ZipFile(inner_zip, 'r') as inner_zfile:
                        for inner_z in inner_zfile.namelist():
                            if inner_z == type_system:
                                if type_system_file is None:
                                    type_system_file = io.BytesIO(inner_zfile.read(inner_z))
                                continue
                            xmi_dict[doc][inner_z] = io.BytesIO(inner_zfile.read(inner_z))
    xmi_dict[type_system] = type_system_file
    return xmi_dict
