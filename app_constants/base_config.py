import sys
import logging
from typing import Union

import config


def get_foreign_keys(foreign_keys: Union[dict, None] = None):
    foreign_key = ""
    for _col, _dict in foreign_keys.items():
        foreign_key += "    FOREIGN KEY ({column}) REFERENCES {table} ({ref_column}),\n".format(
            column=_col.lower(), table=_dict.get("table").lower(), ref_column=_dict.get("column").lower()
        )
    return foreign_key[:-2] + "\n);"


def get_db_structure(columns: Union[dict, None] = None, foreign_keys: Union[dict, None] = None):
    stm = "(\n    id text PRIMARY KEY,\n"
    for _name, _type in columns.items():
        if _name != "id":
            stm += "    {} {} NOT NULL,\n".format(_name.lower(), _type.lower())
    if foreign_keys is not None:
        stm += get_foreign_keys(foreign_keys=foreign_keys)
    else:
        return stm[:-2] + "\n);"
    return stm


def construct_db_dict(e_types: list, db_info: dict, basic_info: dict, entity_info: dict):
    e_types.append("base")
    _db = {}
    for entry_type in e_types:
        _entity = True if entry_type == "entities" else False
        for entry_name, entry_dict in db_info.get(entry_type).items():
            try:
                _columns: dict = entry_dict["columns"]
                _indexed_columns: list = entry_dict["indexed_columns"]
                _foreign_keys: dict = entry_dict["reference_columns"]
            except KeyError:
                logging.error("Please check if the keys 'columns', 'indexed_columns' or 'reference_columns' "
                              "of the '{e_type} - {e_name}' information in 'config.py' are present "
                              "and spelled correctly!"
                              .format(e_type=entry_type, e_name=entry_name)
                              )
                sys.exit(-1)

            if not entry_type == "base":
                _columns.update(basic_info.get("columns"))
                _indexed_columns.extend(basic_info.get("indexed_columns"))
                _foreign_keys.update(basic_info.get("reference_columns"))
            if _entity:
                _columns.update(entity_info.get("columns"))
                _indexed_columns.extend(entity_info.get("indexed_columns"))
                _foreign_keys.update(entity_info.get("reference_columns"))
            _foreign_keys = None if len(_foreign_keys) == 0 else _foreign_keys
            _db[entry_name] = {
                "stm": get_db_structure(columns=_columns, foreign_keys=_foreign_keys),
                "idx": _indexed_columns
            }
    return _db


def check_for_conformity(e_types: list):
    # ToDo: check for conformity between column declarations and indexed/referenced column names
    if len(set(e_types).difference(config.additional_database_info.keys())) > 0:
        logging.error(
            " Please check if the keys of 'additional_database_info' are equal to and conform with {conform}!\n"
            "expected: {exp}\nvs.\ngot: {got}".format(
                conform=", ".join("'{}'".format(e) for e in e_types),
                exp=set(e_types), got=set(config.additional_database_info.keys()))
        )
        sys.exit(-1)

    if len(set(config.layers.keys()).difference(
            [k for t in e_types for k in config.additional_database_info.get(t).keys()])) > 0:
        logging.error(
            " Please make sure that each sub key in {e_types} of 'additional_database_info'"
            " conforms with a key in 'layers'!\nlayers: {layers}\nvs.\nsub keys: {s_keys}".format(
                e_types=", ".join("'{}'".format(e) for e in e_types), layers=set(config.layers.keys()),
                s_keys=set([k for t in e_types for k in config.additional_database_info.get(t).keys()]))
        )
        sys.exit(-1)


entry_types = ["entities", "relations"]

database_info = {
    "base": {
        "annotators": {
            "columns": {
                "id": "text",
                "annotator": "text"
            },
            "indexed_columns": ["annotator"],
            "reference_columns": {}
        },
        "documents": {
            "columns": {
                "id": "text",
                "document": "text"
            },
            "indexed_columns": ["document"],
            "reference_columns": {}
        },
        "sentences": {
            "columns": {
                "id": "text",
                "begin": "integer",
                "end": "integer",
                "document": "text",
                "text": "text",
                "has_annotation": "integer"
            },
            "indexed_columns": [],
            "reference_columns": {
                "document": {
                    "table": "documents",
                    "column": "id"
                }
            }
        },
        "annotation_types": {
            "columns": {
                "id": "text",
                "type": "text",
                "layer": "text"
            },
            "indexed_columns": ["type", "layer"],
            "reference_columns": {
                "layer": {
                    "table": "layers",
                    "column": "id"
                }
            }
        },
        "layers": {
            "columns": {
                "id": "text",
                "layer": "text"
            },
            "indexed_columns": ["layer"],
            "reference_columns": {}
        }
    }
}

basic_general_info = {
    "columns": {
        "id": "text",
        "annotator": "text",
    },
    "indexed_columns": [],
    "reference_columns": {
        "annotator": {
            "table": "annotators",
            "column": "id"
        }
    }
}

additional_entity_info = {
    "columns": {
        "begin": "integer",
        "end": "integer",
        "text": "text",
        "sentence": "text",
        "document": "text",
        "type": "text",
    },
    "indexed_columns": ["type", "sentence"],
    "reference_columns": {
        "sentence": {
            "table": "sentences",
            "column": "id"
        },
        "type": {
            "table": "annotation_types",
            "column": "id"
        }
    }
}

check_for_conformity(entry_types)

layers = config.layers.update({
    "sentences": "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence",
})

database_info.update(config.additional_database_info)
db_construction = construct_db_dict(entry_types, database_info, basic_general_info, additional_entity_info)
