from functools import lru_cache
from typing import Iterable, Tuple, Union

from aenum import Constant
from cassis import Cas
from cassis.typesystem import FeatureStructure


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


class WebAnnoLayer:
    def __init__(self, fqn: str, props: Iterable[Tuple[str, object]], fs: FeatureStructure, cas: Cas):
        self._fqn = fqn
        self._properties = {k: v for (k, v) in props}
        self._fs = fs
        self._cas = cas

    @property
    def xmi_id(self) -> int:
        return self._fs.xmiID

    @property
    def fqn(self) -> str:
        return self._fqn

    @property
    def covered_text(self) -> str:
        return self._fs.get_covered_text()

    @property
    def begin(self):
        return getattr(self._fs, "begin", None)

    @property
    def end(self):
        return getattr(self._fs, "end", None)

    @property
    def length(self):
        return self.end - self.begin

    def _get_fs_from_target(self, target: object) -> FeatureStructure:
        _type = target.target.type
        _xmi_id = target.target.xmiID
        for _fs in self._cas.select(_type):
            if _xmi_id == _fs.xmiID:
                return _fs

    @lru_cache()
    def get_fs_property(self, name: str) -> Union[bool, str, Iterable[dict], None]:
        _return = None
        if name in self._properties.keys():
            _attr = getattr(self._fs, name, None)
            _type = self._properties.get(name)

            if _type == bool:
                if _attr.lower() in ("false", "falsch", "no", "nein"):
                    _return = False
                elif _attr.lower() in ("true", "wahr", "yes", "ja"):
                    _return = True
            elif _type == str or _type == int:
                _return = _type(_attr)
            elif isinstance(_type, list):
                _return = [
                    (x.xmiID, _type[0](self._get_fs_from_target(x), self._cas))
                    for x in _attr
                ]
        return _return

    @lru_cache()
    def get_containing(self, container: str):
        return self._cas.select_covering(container, self._fs)


class MedicationEntity(WebAnnoLayer):
    def __init__(self, fs, cas):
        super().__init__(
            LayerTypes.MEDICATION_ENTITY,
            [(LayerProperties.MEDICATION_ENTITY_TYPE, str),
             (LayerProperties.MEDICATION_ENTITY_IS_LIST, bool),
             (LayerProperties.MEDICATION_ENTITY_IS_RECOMMENDATION, bool)],
            fs,
            cas
        )


class MedicationAttribute(WebAnnoLayer):
    def __init__(self, fs, cas):
        super().__init__(
            LayerTypes.MEDICATION_ATTRIBUTE,
            [(LayerProperties.MEDICATION_ATTRIBUTE_TYPE, str),
             (LayerProperties.MEDICATION_ATTRIBUTE_RELATION,
              [LAYER_DICT.get(LayerTypes.MEDICATION_ENTITY)])],
            fs,
            cas
        )


LAYER_DICT = {
    LayerTypes.MEDICATION_ENTITY: MedicationEntity,
    LayerTypes.MEDICATION_ATTRIBUTE: MedicationAttribute
}
