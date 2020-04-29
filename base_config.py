from typing import Union

import config


def get_default_infos(entity: bool = True):
    base_stm_string = """
    id text PRIMARY KEY,
    annotator text NOT NULL"""

    entity_stm_string = """
    begin integer NOT NULL,
    end integer NOT NULL,
    text text NOT NULL,
    sentence text NOT NULL,
    document text NOT NULL,
    type text NOT NULL"""

    return base_stm_string + "," + entity_stm_string if entity else base_stm_string


def get_default_indices():
    entity_indices = ["type", "sentence"]

    return entity_indices


def get_default_foreign_keys(entity: bool = True, additional_foreign_keys: Union[dict, None] = None):
    base_foreign_key = """
    FOREIGN KEY (annotator) REFERENCES annotators (id)"""

    entity_foreign_key = """
    FOREIGN KEY (sentence) REFERENCES sentences (id),
    FOREIGN KEY (type) REFERENCES annotation_types (id)"""

    if additional_foreign_keys is None:
        additional_foreign_keys = {}

    return base_foreign_key + "," + entity_foreign_key if entity else base_foreign_key


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

layers.update(config.layers)


if __name__ == "__main__":
    print(get_default_infos())
    print(get_default_foreign_keys())
