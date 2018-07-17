# -*- coding: utf-8 -*-

import os
from typing import Dict, List, Tuple, Union, Set

from .properties import AnnotationTypes


class Annotation(object):

    def __init__(self, aid: str, atype: str, parent: 'Document') -> None:
        """
        
        :param aid: 
        :param atype: 
        :param parent: 
        """
        self._parent = parent
        self._id = aid
        self._type = atype

    def _get_text_object(self) -> 'Document':
        """
        
        :return: 
        """
        return self._parent

    def update(self) -> None:
        """
        
        :return: 
        """
        pass

    def get_id(self) -> str:
        """
        
        :return: 
        """
        return self._id

    def get_type(self) -> str:
        """

        :return: 
        """
        return self._type


class ArgsAnnotation(Annotation):

    def __init__(self, aid: str, atype: str, args: List[str], parent: 'Document') -> None:
        """

        :param aid: 
        :param atype: 
        :param args: 
        :param parent: 
        """
        super().__init__(aid, atype, parent)

        self._args_dict = dict()
        self._parse_args(args)

    def _parse_args(self, args: List[str]) -> None:
        """

        :param args: 
        """
        for pair in args:
            pair = pair.split(":")
            self._args_dict[pair[0]] = pair[1]

    def _get_arg(self, tid: str) -> Union[Annotation, None]:
        """

        :param tid: 
        :return: 
        """
        parent = self._get_text_object()
        for arg_dict in [
            parent.get_triggers(),  # tid is a Trigger
            parent.get_events(),  # tid is an Event ?
            parent.get_relations(),  # tid is a Relation ?
            parent.get_modifications()  # tid is a Modification ?
        ]:
            arg = arg_dict.get(tid, None)
            if arg:
                return arg
        return None

    def update(self) -> None:
        """

        """
        for pair in self._args_dict.items():
            self._args_dict[pair[0]] = self._get_arg(pair[1])

    def get_arguments(self) -> Dict[str, Annotation]:
        """

        :return: 
        """
        return self._args_dict


class Trigger(Annotation):

    def __init__(self, ann_list: List[str], parent: 'Document') -> None:
        """
        Some description::
        
            T#    TYPE begin end     TEXT    (begin end    TEXT)
            -- e.g. --
            T1    Medication 6827 6835    Daraprim
        
        some more description
        
        :param ann_list: 
        :param parent: 
        """
        args = (ann_list[1]).split()
        super().__init__(ann_list[0], args[0], parent)
        self._get_spans(" ".join(((ann_list[1]).split())[1:]))
        self._text = ann_list[2]

        self._spec_text = None
        self._spec_begin = None
        self._spec_end = None
        if len(ann_list) > 3:
            self._spec_text = ann_list[4]
            self._spec_begin = int((ann_list[3]).split()[0])
            self._spec_end = int((ann_list[3]).split()[1])

    def _get_spans(self, span_list: str) -> None:
        """

        :param span_list: 
        """
        self._begin = list()
        self._end = list()
        spans = span_list.split(";") # 2493 2504;2505 2509
        _merge = False
        for _i in range(len(spans)):
            span = spans[_i].split()
            _b = int(span[0])
            _e = int(span[1])
            if not _merge:
                self._begin.append(_b)
            if _i < len(spans) - 1:
                if int(spans[_i+1].split()[0]) - _e <= 1:
                    _merge = True
                else:
                    _merge = False
            else:
                _merge = False
            if not _merge:
                self._end.append(_e)

    def get_text(self) -> str:
        """

        :return: 
        """
        return self._text

    def get_span(self) -> Tuple[List[int], List[int]]:
        """

        :return: 
        """
        return self._begin, self._end

    def has_specific(self) -> Union[Tuple[str, Tuple[int, int]], bool]:
        """

        :return: 
        """
        if self._spec_text:
            return self._spec_text, (self._spec_begin, self._spec_end)
        return False


class Relation(ArgsAnnotation):

    def __init__(self, ann_list: List[str], parent: 'Document') -> None:
        """
        Desc::
        
            R#    TYPE *ARGS[ARG:TYPE; space-sep]    (...)
            -- e.g. --
            R1    Coreference Subject:T13 Object:T14
            
        Desc
        
        :param ann_list: 
        :param parent: 
        """
        args = (ann_list[1]).split()
        super().__init__(ann_list[0], args[0], args[1:], parent)

        self._spec_trigger = list()
        if len(ann_list) > 2:
            a = ann_list[2]
            self._spec_trigger = ((a[1:-1]).replace(' ', '')).split(",")

    def update(self) -> None:
        """

        """
        super().update()
        spec = self.has_specific()
        if isinstance(spec, list):
            self._spec_trigger = [self._get_arg(tid) for tid in spec]

    def has_specific(self) -> Union[List[str], bool]:
        if self._spec_trigger:
            return self._spec_trigger
        return False


class Event(ArgsAnnotation):

    def __init__(self, ann_list: List[str], parent: 'Document') -> None:
        """
        Desc::
        
            E#    TYPE:ID *ARGS[ARG:TYPE; space-sep]
            -- e.g. --
            E1    Dose:T2 Dose-Arg:T1
        
        Desc
        
        :param ann_list: 
        :param parent: 
        """
        args = (ann_list[1]).split()
        etype = (args[0]).split(":")[0]
        super().__init__(ann_list[0], etype, args[1:], parent)

        self._trigger = (args[0]).split(":")[1]

    def get_trigger(self) -> 'Trigger':
        """

        :return: 
        """
        return self._parent.get_triggers()[self._trigger]


class Modification(Annotation):

    def __init__(self, ann_list: List[str], parent: 'Document') -> None:
        """
        Desc::
        
            M#    TYPE ID
            -- e.g. --
            M1    Speculation E42
    
        Desc
        
        :param ann_list: 
        :param parent: 
        """
        args = (ann_list[1]).split()
        super().__init__(ann_list[0], args[0], parent)

        self._argument_str = args[1]
        self._argument = None

    def _get_arg(self, tid: str) -> Union['Annotation', None]:
        """

        :param tid: 
        :return: 
        """
        parent = self._get_text_object()
        for arg_dict in [
            parent.get_triggers(),  # tid is a Trigger
            parent.get_events(),  # tid is an Event ?
            parent.get_relations(),  # tid is a Relation ?
            parent.get_modifications()  # tid is a Modification ?
        ]:
            arg = arg_dict.get(tid, None)
            if arg:
                return arg
        return None

    def update(self) -> None:
        """

        """
        self._argument = self._get_arg(self._argument_str)

    def get_argument(self) -> Union['Annotation', None]:
        return self._argument


class Attribute(Annotation):

    def __init__(self, ann_list: List[str], parent: 'Document') -> None:
        """
        Desc::
        
            A#    TYPE ID (VALUE)
            -- e.g. --
            A1    Source T7 (Text)
            
        Desc
    
        :param ann_list: 
        :param parent: 
        """
        args = (ann_list[1]).split()
        super().__init__(ann_list[0], args[0], parent)

        self._argument_str = args[1]
        self._argument = None

    def _get_arg(self, tid: str) -> Union['Annotation', None]:
        """

        :param tid: 
        :return: 
        """
        parent = self._get_text_object()
        for arg_dict in [
            parent.get_triggers(),  # tid is a Trigger
            parent.get_events(),  # tid is an Event ?
            parent.get_relations(),  # tid is a Relation ?
            parent.get_modifications()  # tid is a Modification ?
        ]:
            arg = arg_dict.get(tid, None)
            if arg:
                return arg
        return None

    def update(self) -> None:
        """

        """
        self._argument = self._get_arg(self._argument_str)

    def get_argument(self) -> 'Annotation':
        return self._argument


class Equivalence(Annotation):

    def __init__(self, ann_list: List[str], parent: 'Document', equiv_counter: int) -> None:
        """

        :param ann_list: 
        :param parent: 
        :param equiv_counter: 
        """
        args = (ann_list[1]).split()
        super().__init__(ann_list[0]+str(equiv_counter), args[0], parent)

        self._arguments = args[1:]


class Document(object):

    def __init__(self, docid: str, froot: str, dset: str, txt_end: str=".txt", ann_end: str=".ann",
                 excl_list: Union[List[str], None]=None) -> None:
        """

        :param docid: 
        :param froot: 
        :param dset: 
        :param txt_end: 
        :param ann_end: 
        :param excl_list: 
        """
        self._txt_end = txt_end
        self._ann_end = ann_end
        self._did = docid
        self._root = froot
        self._set = dset
        self._text = ""
        self._event_dict = dict()
        self._trig_dict = dict()
        self._mod_dict = dict()
        self._rel_dict = dict()
        self._attr_dict = dict()
        self._txt = None
        self._ann = None
        self._equiv_counter = 0
        self._active_ann_types = self._set_ann_types(excl_list)

        self._read_data()

    def _set_ann_types(self, excl_list: Union[List[str], None]) -> Set[str]:

        """

        :param excl_list: 
        :return: 
        """
        if excl_list is not None:
            _excl = {_e for _e in excl_list if _e in AnnotationTypes.all_annotations()}
            return AnnotationTypes.all_annotations().difference(_excl)
        return AnnotationTypes.all_annotations()

    def _read_data(self) -> None:
        """

        """
        self._txt = "{}{}".format(
            os.path.join(self._root, self._set, self._did),
            self._txt_end
        )
        self._ann = "{}{}".format(
            os.path.join(self._root, self._set, self._did),
            self._ann_end
        )
        self._read_txt()
        self._read_annotations()

    def _read_txt(self, no_newline: bool=False) -> None:
        """

        :param no_newline: 
        """
        with open(self._txt, 'r') as fi:
            lines = fi.readlines()
            if no_newline:
                t_list = [l.rstrip('\n') for l in lines]
                self._text = ' '.join(t_list)
            else:
                self._text = ''.join(lines)

    def _read_annotations(self) -> None:
        """

        """
        with open(self._ann, 'r') as fi:
            lines = fi.readlines()
            lines = [(l.rstrip('\n')).split('\t') for l in lines]
            anno_list = list()
            for line in lines:
                anno = None
                if len(line) <= 1:
                    print("DEBUG")
                if not len(line) <= 1:
                    eid = line[0]
                    if eid.startswith("T"):
                        anno = Trigger(line, self)
                        self._trig_dict[eid] = anno
                    elif eid.startswith("R"):
                        anno = Relation(line, self)
                        self._rel_dict[eid] = anno
                    elif eid.startswith("E"):
                        anno = Event(line, self)
                        self._event_dict[eid] = anno
                    elif eid.startswith("M"):
                        anno = Modification(line, self)
                        self._mod_dict[eid] = anno
                    elif eid.startswith("A"):
                        anno = Attribute(line, self)
                        if anno is not None:
                            self._attr_dict[eid] = anno
                    # TODO "* Relations"!!
                    elif eid.startswith("*"):
                        self._equiv_counter += 1
                        anno = Equivalence(line, self, self._equiv_counter)
                        self._rel_dict[eid+str(self._equiv_counter)] = anno

                if not (anno is None):
                    anno_list.append(anno)

            for anno in anno_list:
                anno.update()

    def get_id(self) -> str:
        """

        :return: 
        """
        return self._did

    def get_text(self) -> str:
        """

        :return: 
        """
        return self._text

    def get_triggers(self, trigger_type: str=None) -> Union[Dict[str, 'Trigger'], None]:
        """

        :param trigger_type: 
        :return: 
        """
        if trigger_type in AnnotationTypes.trigger_types():
            return {t: self._trig_dict[t] for t in self._trig_dict.keys()
                    if (self._trig_dict[t]).get_type() == trigger_type}
        elif trigger_type is None:
            return {t: self._trig_dict[t] for t in self._trig_dict.keys()}
        else:
            return None

    def get_relations(self, relation_type: str=None) -> Union[Dict[str, 'Relation'], None]:
        """

        :param relation_type: 
        :return: 
        """
        if relation_type in AnnotationTypes.relation_types():
            return {r: self._rel_dict[r] for r in self._rel_dict.keys()
                    if (self._rel_dict[r]).get_type() == relation_type}
        elif relation_type is None:
            return {r: self._rel_dict[r] for r in self._rel_dict.keys()}
        else:
            return None

    def get_events(self, event_type: str=None) -> Union[Dict[str, 'Event'], None]:
        """

        :param event_type: 
        :return: 
        """
        if event_type in AnnotationTypes.event_types():
            return {e: self._event_dict[e] for e in self._event_dict.keys()
                    if (self._event_dict[e]).get_type() == event_type}
        elif event_type is None:
            return {e: self._event_dict[e] for e in self._event_dict.keys()}
        else:
            return None

    def get_modifications(self, mod_type: str=None) -> Union[Dict[str, 'Modification'], None]:
        """

        :param mod_type: 
        :return: 
        """
        if True:
            return {m: self._mod_dict[m] for m in self._mod_dict.keys()
                    if (self._mod_dict[m]).get_type() == mod_type}
        elif mod_type is None:
            return {m: self._mod_dict[m] for m in self._mod_dict.keys()}
        else:
            return None
