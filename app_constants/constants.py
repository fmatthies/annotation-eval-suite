from aenum import Constant


class LayerTypes(Constant):
    SENTENCE = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence"
    MEDICATION_ENTITY = "webanno.custom.MedicationEntity"
    MEDICATION_ATTRIBUTE = "webanno.custom.MedicationAttribute"
    RELATION = "webanno.custom.MedicationAttributeRelationTypeLink"
    ANNOTATOR = "annotator"
    DOCUMENT = "document"


class LayerProperties(Constant):
    MEDICATION_ENTITY_TYPE = "drugType"
    MEDICATION_ENTITY_IS_RECOMMENDATION = "isRecommendation"
    MEDICATION_ENTITY_IS_LIST = "isList"
    MEDICATION_ATTRIBUTE_TYPE = "attributeType"
    MEDICATION_ATTRIBUTE_RELATION = "relationType"


class FileNames(Constant):
    TYPE_SYSTEM = "TypeSystem.xml"


class Keys(Constant):
    USER_ID = "user_ids"
    ANNOTATIONS = "annotations"
    DOCUMENT_ID = "document_ids"
    TYPE_SYSTEM = "type_system"
    SENTENCES = "sentences"


class StringValues(Constant):
    DOCUMENT_USER_KEY = "{}-{}"


TABLES = {
    "sentences": {
        "stm": """(
            id text PRIMARY KEY,
            begin integer NOT NULL,
            end integer NOT NULL,
            document text NOT NULL,
            text text NOT NULL,
            has_annotation integer
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
            FOREIGN KEY (annotator) REFERENCES annotators (id)
        );""",
        "idx": ["type"]
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
            FOREIGN KEY (annotator) REFERENCES annotators (id)
        );""",
        "idx": ["type"]
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
    "annotators": {
        "stm": """(
            id text PRIMARY KEY,
            annotator text NOT NULL
        );""",
        "idx": ["id"]
    },
    "documents": {
        "stm": """(
            id text PRIMARY KEY,
            document text NOT NULL
        );""",
        "idx": ["id"]
    }
}

LAYER_TNAME_DICT = {
    LayerTypes.SENTENCE: "sentences",
    LayerTypes.MEDICATION_ENTITY: "medication_entities",
    LayerTypes.MEDICATION_ATTRIBUTE: "medication_attributes",
    LayerTypes.RELATION: "relations",
    LayerTypes.ANNOTATOR: "annotators",
    LayerTypes.DOCUMENT: "documents"
}
