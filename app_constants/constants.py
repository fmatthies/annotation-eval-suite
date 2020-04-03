from aenum import Constant


class LayerTypes(Constant):
    SENTENCE = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence"
    MEDICATION_ENTITY = "webanno.custom.MedicationEntity"
    MEDICATION_ATTRIBUTE = "webanno.custom.MedicationAttribute"


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
