import sys
from typing import Union

import config


def get_foreign_keys(entity: bool = True, additional_foreign_keys: Union[dict, None] = None):
    base_foreign_key = """
    FOREIGN KEY (annotator) REFERENCES annotators (id)"""

    entity_foreign_key = """
    FOREIGN KEY (sentence) REFERENCES sentences (id),
    FOREIGN KEY (type) REFERENCES annotation_types (id)"""

    foreign_key = base_foreign_key + "," + entity_foreign_key if entity else base_foreign_key
    if additional_foreign_keys is not None and isinstance(additional_foreign_keys, dict):
        for _col, _ref in additional_foreign_keys.items():
            foreign_key += ",\n    FOREIGN KEY ({}) REFERENCES {}".format(_col.lower(), _ref.lower())
    foreign_key += "\n);"
    return foreign_key


def get_db_structure(entity: bool = True, additional_columns: Union[dict, None] = None,
                     additional_foreign_keys: Union[dict, None] = None):
    base_stm_string = """(
    id text PRIMARY KEY,
    annotator text NOT NULL"""

    entity_stm_string = """
    begin integer NOT NULL,
    end integer NOT NULL,
    text text NOT NULL,
    sentence text NOT NULL,
    document text NOT NULL,
    type text NOT NULL"""

    stm = base_stm_string + "," + entity_stm_string if entity else base_stm_string
    if additional_columns is not None and isinstance(additional_columns, dict):
        for _name, _type in additional_columns.items():
            stm += ",\n    {} {} NOT NULL".format(_name.lower(), _type.lower())
    stm += "," + get_foreign_keys(entity=entity, additional_foreign_keys=additional_foreign_keys)
    return stm


def get_indices(entity: bool = True, additional_indices: Union[list, None] = None):
    entity_indices = ["type", "sentence"]

    idx = entity_indices if entity else []
    if additional_indices is not None and isinstance(additional_indices, list):
        idx.extend(additional_indices)

    return idx


database = {
    "annotators": {
        "stm": """(
            id text PRIMARY KEY,
            annotator text NOT NULL
        );""",
        "idx": ["annotator"]
    },
    "documents": {
        "stm": """(
           id text PRIMARY KEY,
           document text NOT NULL
       );""",
        "idx": ["document"]
    },
    "sentences": {
        "stm": """(
            id text PRIMARY KEY,
            begin integer NOT NULL,
            end integer NOT NULL,
            document text NOT NULL,
            text text NOT NULL,
            has_annotation integer NOT NULL,
            FOREIGN KEY (document) REFERENCES documents (id)
        );""",
        "idx": []
    },
    "annotation_types": {
        "stm": """(
            id text PRIMARY KEY,
            type text NOT NULL,
            layer text NOT NULL,
            FOREIGN KEY (layer) REFERENCES layers
        );""",
        "idx": ["type", "layer"]
    },
    "layers": {
        "stm": """(
            id text PRIMARY KEY,
            layer text NOT NULL
        );""",
        "idx": ["layer"]
    }

}

layers = {
    "sentences": "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence",
}

entry_types = ["entities", "relations"]
if len(set(entry_types).difference(config.additional_database_info.keys())) > 0:
    print("Please check if the keys of 'additional_database_info' are equal to and conform with {}!"
          .format(", ".join("'{}'".format(e) for e in entry_types))
          )
    print("expected: {}\nvs.\ngot: {}".format(set(entry_types), set(config.additional_database_info.keys())))
    sys.exit(-1)

if len(set(config.layers.keys()).difference(
        [k for t in entry_types for k in config.additional_database_info.get(t).keys()])) > 0:
    print("Please make sure that each sub key in {} of 'additional_database_info' conforms with a key in 'layers'!"
          .format(", ".join("'{}'".format(e) for e in entry_types))
          )
    print("layers: {}\nvs.\nsub keys: {}"
          .format(set(config.layers.keys()),
                  set([k for t in entry_types for k in config.additional_database_info.get(t).keys()]))
          )
    sys.exit(-1)

layers.update(config.layers)

for entry_type in entry_types:
    _entity = True if entry_type == "entities" else False
    for entry_name, entry_dict in config.additional_database_info.get(entry_type).items():
        try:
            columns: dict = entry_dict["columns"]
            indexed_columns: list = entry_dict["indexed_columns"]
            foreign_keys: dict = entry_dict["reference_columns"]
        except KeyError:
            print("Please check if the keys 'columns', 'indexed_columns' or 'reference_columns' "
                  "of the '{} - {}' information in 'config.py' are present and spelled correctly!"
                  .format(entry_type, entry_name))
            sys.exit(-1)

        database[entry_name] = {
            "stm": get_db_structure(entity=_entity, additional_columns=columns, additional_foreign_keys=foreign_keys),
            "idx": get_indices(entity=_entity, additional_indices=indexed_columns)
        }


if __name__ == "__main__":
    print(database)
    print(layers)
