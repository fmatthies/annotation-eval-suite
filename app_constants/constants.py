from aenum import Constant


class LayerTypes(Constant):
    SENTENCE = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence"
    MEDICATION_ENTITY = "webanno.custom.MedicationEntity"
    MEDICATION_ATTRIBUTE = "webanno.custom.MedicationAttribute"
    RELATION = "webanno.custom.MedicationAttributeRelationTypeLink"
    ANNOTATOR = "annotator"
    DOCUMENT = "document"
    LAYER = "layer"
    ANNOTATION_TYPE = "annotation"


class LayerProperties(Constant):
    MEDICATION_ENTITY_TYPE = "drugType"
    MEDICATION_ENTITY_IS_RECOMMENDATION = "isRecommendation"
    MEDICATION_ENTITY_IS_LIST = "isList"
    MEDICATION_ATTRIBUTE_TYPE = "attributeType"
    MEDICATION_ATTRIBUTE_RELATION = "relationType"


class WebAnnoExport(Constant):
    TYPE_SYSTEM = "TypeSystem.xml"
    ZIP_ENDING = ".zip"
    ROOT = "annotation/"


TABLES = {
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
    "medication_entities": {
        "stm": """(
            id text PRIMARY KEY,
            annotator text NOT NULL,
            begin integer NOT NULL,
            end integer NOT NULL,
            text text NOT NULL,
            sentence text NOT NULL,
            document text NOT NULL,
            type text NOT NULL,
            list integer NOT NULL,
            recommendation integer NOT NULL,
            FOREIGN KEY (sentence) REFERENCES sentences (id),
            FOREIGN KEY (annotator) REFERENCES annotators (id),
            FOREIGN KEY (type) REFERENCES annotation_types (id)
        );""",
        "idx": ["type", "sentence"]
    },
    "medication_attributes": {
        "stm": """(
            id text PRIMARY KEY,
            annotator text NOT NULL,
            begin integer NOT NULL,
            end integer NOT NULL,
            text text NOT NULL,
            sentence text NOT NULL,
            document text NOT NULL,
            type text NOT NULL,
            FOREIGN KEY (sentence) REFERENCES sentences (id),
            FOREIGN KEY (annotator) REFERENCES annotators (id),
            FOREIGN KEY (type) REFERENCES annotation_types (id)
        );""",
        "idx": ["type", "sentence"]
    },
    "relations": {
        "stm": """(
            id text PRIMARY KEY,
            annotator text NOT NULL,
            entity text NOT NULL,
            attribute text NOT NULL,
            FOREIGN KEY (entity) REFERENCES medication_entities (id),
            FOREIGN KEY (attribute) REFERENCES medication_attributes (id),
            FOREIGN KEY (annotator) REFERENCES annotators (id)
        );""",
        "idx": ["entity"]
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
    },
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
    }
}

LAYER_TNAME_DICT = {
    LayerTypes.SENTENCE: "sentences",
    LayerTypes.MEDICATION_ENTITY: "medication_entities",
    LayerTypes.MEDICATION_ATTRIBUTE: "medication_attributes",
    LayerTypes.RELATION: "relations",
    LayerTypes.ANNOTATOR: "annotators",
    LayerTypes.DOCUMENT: "documents",
    LayerTypes.LAYER: "layers",
    LayerTypes.ANNOTATION_TYPE: "annotation_types"
}
