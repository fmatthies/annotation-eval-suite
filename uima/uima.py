from functools import lru_cache
from typing import Tuple, Iterable, Union
from cassis import load_typesystem, load_cas_from_xmi
from cassis.cas import FeatureStructure, Cas, TypeSystem

TYPE_SYSTEM = "TypeSystem.xml"
MEDICATION_ENTITY = "webanno.custom.MedicationEntity"
MEDICATION_ENTITY_TYPE = "drugType"
MEDICATION_ENTITY_IS_RECOMMENDATION = "isRecommendation"
MEDICATION_ENTITY_IS_LIST = "isList"
MEDICATION_ATTRIBUTE = "webanno.custom.MedicationAttribute"
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
    def get_fs_property(self, name: str) -> Union[bool, str, list, None]:
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
                    _type[0](self._get_fs_from_target(x), self._cas)
                    for x in _attr
                ]
        return _return


class MedicationEntity(WebAnnoLayer):
    def __init__(self, fs, cas):
        super().__init__(
            MEDICATION_ENTITY,
            [(MEDICATION_ENTITY_TYPE, str),
             (MEDICATION_ENTITY_IS_LIST, bool),
             (MEDICATION_ENTITY_IS_RECOMMENDATION, bool)],
            fs,
            cas
        )

    @property
    def type(self):
        return self.get_fs_property(MEDICATION_ENTITY_TYPE)


class MedicationAttribute(WebAnnoLayer):
    def __init__(self, fs, cas):
        super().__init__(
            MEDICATION_ATTRIBUTE,
            [(MEDICATION_ATTRIBUTE_TYPE, str),
             (MEDICATION_ATTRIBUTE_RELATION, [LAYER_DICT.get(MEDICATION_ENTITY)])],
            fs,
            cas
        )

    @property
    def type(self):
        return self.get_fs_property(MEDICATION_ATTRIBUTE_TYPE)


LAYER_DICT = {
    MEDICATION_ENTITY: MedicationEntity,
    MEDICATION_ATTRIBUTE: MedicationAttribute
}


@lru_cache()
def gather_annotations(annotation_type: str, cas: Cas):
    alist = []
    for _fs in cas.select(annotation_type):
        alist.append(LAYER_DICT.get(annotation_type)(_fs, cas))
    return alist

