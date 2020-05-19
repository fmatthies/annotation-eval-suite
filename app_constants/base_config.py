import sys
import logging
from typing import Union
from aenum import Constant

import config


class DefaultTableNames(Constant):
    annotation_types = "annotation_types"
    layers = "layers"
    annotators = "annotators"
    documents = "documents"
    sentences = "sentences"


class DatabaseCategories(Constant):
    entities = "entities"
    relations = "relations"
    base = "base"


class DatabaseConstructionKeys(Constant):
    type = "type"
    columns = "additional_columns"
    indices = "indexed_columns"
    foreign_keys = "reference_columns"


class SQLiteDataTypes(Constant):
    string = "text"
    boolean = "integer"
    integer = "integer"


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
    e_types.append(DatabaseCategories.base)
    _db = {}
    for entry_type in e_types:
        _entity = True if entry_type == DatabaseCategories.entities else False
        for entry_name, entry_dict in db_info.get(entry_type).items():
            try:
                _type: dict = entry_dict[DatabaseConstructionKeys.type] \
                    if entry_type == DatabaseCategories.entities else None
                _columns: dict = {k: d.get("data_type")
                                  for k, d in entry_dict[DatabaseConstructionKeys.columns].items()} \
                    if entry_type != DatabaseCategories.base else entry_dict[DatabaseConstructionKeys.columns]
                _indexed_columns: list = entry_dict[DatabaseConstructionKeys.indices]
                _foreign_keys: dict = entry_dict[DatabaseConstructionKeys.foreign_keys]
            except KeyError:
                logging.error("Please check if the keys 'type, 'columns', 'indexed_columns' or 'reference_columns' "
                              "of the '{e_type} - {e_name}' information in 'config.py' are present "
                              "and spelled correctly!"
                              .format(e_type=entry_type, e_name=entry_name)
                              )
                sys.exit(-1)

            if not entry_type == DatabaseCategories.base:
                _columns.update(basic_info.get(DatabaseConstructionKeys.columns))
                _indexed_columns.extend(basic_info.get(DatabaseConstructionKeys.indices))
                _foreign_keys.update(basic_info.get(DatabaseConstructionKeys.foreign_keys))
            if _entity:
                _columns.update(entity_info.get(DatabaseConstructionKeys.columns))
                _indexed_columns.extend(entity_info.get(DatabaseConstructionKeys.indices))
                _foreign_keys.update(entity_info.get(DatabaseConstructionKeys.foreign_keys))
            _foreign_keys = None if len(_foreign_keys) == 0 else _foreign_keys
            _db[entry_name] = {
                "stm": get_db_structure(columns=_columns, foreign_keys=_foreign_keys),
                "idx": _indexed_columns
            }
    return _db


def check_for_conformity(e_types: list):
    # ToDo: check for conformity between column declarations and indexed/referenced column names
    # ToDo: check for conformity of data types
    if len(set(e_types).symmetric_difference(config.additional_database_info.keys())) > 0:
        logging.error(
            " Please check if the keys of 'additional_database_info' in 'config.py' are equal to and"
            " conform with {conform}!\nexpected: {exp}\nvs.\ngot: {got}".format(
                conform=", ".join("'{}'".format(e) for e in e_types),
                exp=set(e_types), got=set(config.additional_database_info.keys()))
        )
        sys.exit(-1)

    if len(set(config.layers.keys()).symmetric_difference(
            set([k for t in e_types for k in config.additional_database_info.get(t).keys()]))) > 0:
        logging.error(
            " Please make sure that each sub key in '{e_types}' of 'additional_database_info'"
            " conforms with a key in 'layers'!\nlayers: {layers}\nvs.\nsub keys: {s_keys}".format(
                e_types=", ".join(e_types), layers=set(config.layers.keys()),
                s_keys=set([k for t in e_types for k in config.additional_database_info.get(t).keys()]))
        )
        sys.exit(-1)


entry_types = [DatabaseCategories.entities, DatabaseCategories.relations]

database_info = {
    DatabaseCategories.base: {
        DefaultTableNames.annotators: {
            DatabaseConstructionKeys.columns: {
                "id": SQLiteDataTypes.string,
                "annotator": SQLiteDataTypes.string
            },
            DatabaseConstructionKeys.indices: ["annotator"],
            DatabaseConstructionKeys.foreign_keys: {}
        },
        DefaultTableNames.documents: {
            DatabaseConstructionKeys.columns: {
                "id": SQLiteDataTypes.string,
                "document": SQLiteDataTypes.string
            },
            DatabaseConstructionKeys.indices: ["document"],
            DatabaseConstructionKeys.foreign_keys: {}
        },
        DefaultTableNames.sentences: {
            DatabaseConstructionKeys.columns: {
                "id": SQLiteDataTypes.string,
                "begin": SQLiteDataTypes.integer,
                "end": SQLiteDataTypes.integer,
                "document": SQLiteDataTypes.string,
                "text": SQLiteDataTypes.string,
                "has_annotation": SQLiteDataTypes.boolean
            },
            DatabaseConstructionKeys.indices: [],
            DatabaseConstructionKeys.foreign_keys: {
                "document": {
                    "table": DefaultTableNames.documents,
                    "column": "id"
                }
            }
        },
        DefaultTableNames.annotation_types: {
            DatabaseConstructionKeys.columns: {
                "id": SQLiteDataTypes.string,
                "type": SQLiteDataTypes.string,
                "layer": SQLiteDataTypes.string
            },
            DatabaseConstructionKeys.indices: ["type", "layer"],
            DatabaseConstructionKeys.foreign_keys: {
                "layer": {
                    "table": DefaultTableNames.layers,
                    "column": "id"
                }
            }
        },
        DefaultTableNames.layers: {
            DatabaseConstructionKeys.columns: {
                "id": SQLiteDataTypes.string,
                "layer": SQLiteDataTypes.string
            },
            DatabaseConstructionKeys.indices: ["layer"],
            DatabaseConstructionKeys.foreign_keys: {}
        }
    }
}

basic_general_info = {
    DatabaseConstructionKeys.columns: {
        "id": SQLiteDataTypes.string,
        "annotator": SQLiteDataTypes.string,
    },
    DatabaseConstructionKeys.indices: [],
    DatabaseConstructionKeys.foreign_keys: {
        "annotator": {
            "table": DefaultTableNames.annotators,
            "column": "id"
        }
    }
}

additional_entity_info = {
    DatabaseConstructionKeys.columns: {
        "type": SQLiteDataTypes.string,
        "begin": SQLiteDataTypes.integer,
        "end": SQLiteDataTypes.integer,
        "text": SQLiteDataTypes.string,
        "sentence": SQLiteDataTypes.string,
        "document": SQLiteDataTypes.string
    },
    DatabaseConstructionKeys.indices: ["sentence", "type"],
    DatabaseConstructionKeys.foreign_keys: {
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

layers = {
    DefaultTableNames.sentences: "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence",
}
layers.update(config.layers)

database_info.update(config.additional_database_info)
db_construction = construct_db_dict(entry_types, database_info, basic_general_info, additional_entity_info)
print(db_construction)
