# -*- coding: utf-8 -*-

import operator
import os

from collections import Counter, defaultdict
from numpy import zeros, NaN
from pandas import DataFrame
from typing import Generator, List, Tuple, Union, Dict, Set
from re import compile as re_compile
from re import DOTALL, VERBOSE
from re import sub as re_sub
from spacy.lang.de import German

from . import annotationobjects
#from .properties import AnnotationTypes
from .centroids import Centroids


_match_types = ['strict', 'approximate', 'one_all']


class BratRegEx(object):
    """
    Class was adapted from the brat code
    """
    # TODO: add type annotations and docstrings

    def __init__(self) -> None:
        """

        """
        self._sentence_boundary_regex = re_compile(r'''
        # Require a leading non-whitespace character for the sentence
        \S
        # Then, anything goes, but don't be greedy
        .*?
        # Anchor the sentence at...
        (:?
            # One (or multiple) terminal character(s)
            #   followed by one (or multiple) whitespace
            (:?([.!?。！？])+(?=\s+))
        | # Or...
            # Newlines, to respect file formatting
            (:?(?=\n+))
        | # Or...
            # End-of-file, excluding whitespaces before it
            (:?(?=\s*$))
        )
    ''', DOTALL | VERBOSE)

        self.__initial = list()

        # TODO: some cases that heuristics could be improved on
        # - no split inside matched quotes
        # - "quoted." New sentence
        # - 1 mg .\nkg(-1) .

        # breaks sometimes missing after "?", "safe" cases
        self.__initial.append((re_compile(r'\b([a-z]+\?) ([A-Z][a-z]+)\b'), r'\1\n\2'))
        # breaks sometimes missing after "." separated with extra space, "safe" cases
        self.__initial.append((re_compile(r'\b([a-z]+ \.) ([A-Z][a-z]+)\b'), r'\1\n\2'))

        # join breaks creating lines that only contain sentence-ending punctuation
        self.__initial.append((re_compile(r'\n([.!?]+)\n'), r' \1\n'))

        # no breaks inside parens/brackets. (To protect against cases where a
        # pair of locally mismatched parentheses in different parts of a large
        # document happen to match, limit size of intervening context. As this
        # is not an issue in cases where there are no interveining brackets,
        # allow an unlimited length match in those cases.)

        self.__repeated = list()

        # unlimited length for no intevening parens/brackets
        self.__repeated.append((re_compile(r'(\([^\[\]\(\)]*)\n([^\[\]\(\)]*\))'), r'\1 \2'))
        self.__repeated.append((re_compile(r'(\[[^\[\]\(\)]*)\n([^\[\]\(\)]*\])'), r'\1 \2'))
        # standard mismatched with possible intervening
        self.__repeated.append((re_compile(r'(\([^\(\)]{0,250})\n([^\(\)]{0,250}\))'), r'\1 \2'))
        self.__repeated.append((re_compile(r'(\[[^\[\]]{0,250})\n([^\[\]]{0,250}\])'), r'\1 \2'))
        # nesting to depth one
        self.__repeated.append(
            (re_compile(r'(\((?:[^\(\)]|\([^\(\)]*\)){0,250})\n((?:[^\(\)]|\([^\(\)]*\)){0,250}\))'), r'\1 \2'))
        self.__repeated.append(
            (re_compile(r'(\[(?:[^\[\]]|\[[^\[\]]*\]){0,250})\n((?:[^\[\]]|\[[^\[\]]*\]){0,250}\])'), r'\1 \2'))

        self.__final = list()

        # no break after periods followed by a non-uppercase "normal word"
        # (i.e. token with only lowercase alpha and dashes, with a minimum
        # length of initial lowercase alpha).
        self.__final.append((re_compile(r'\.\n([a-z]{3}[a-z-]{0,}[ \.\:\,\;])'), r'. \1'))

        # no break in likely species names with abbreviated genus (e.g.
        # "S. cerevisiae"). Differs from above in being more liberal about
        # separation from following text.
        self.__final.append((re_compile(r'\b([A-Z]\.)\n([a-z]{3,})\b'), r'\1 \2'))

        # no break in likely person names with abbreviated middle name
        # (e.g. "Anton P. Chekhov", "A. P. Chekhov"). Note: Won't do
        # "A. Chekhov" as it yields too many false positives.
        self.__final.append((re_compile(r'\b((?:[A-Z]\.|[A-Z][a-z]{3,}) [A-Z]\.)\n([A-Z][a-z]{3,})\b'), r'\1 \2'))

        # no break before CC ..
        self.__final.append((re_compile(r'\n((?:and|or|but|nor|yet) )'), r' \1'))

        # or IN. (this is nothing like a "complete" list...)
        self.__final.append((re_compile(
            r'\n((?:of|in|by|as|on|at|to|via|for|with|that|than|from|into|upon|after|while|during|within|through|between|whereas|whether) )'),
                             r' \1'))

        # no sentence breaks in the middle of specific abbreviations
        self.__final.append((re_compile(r'\b(e\.)\n(g\.)'), r'\1 \2'))
        self.__final.append((re_compile(r'\b(i\.)\n(e\.)'), r'\1 \2'))
        self.__final.append((re_compile(r'\b(i\.)\n(v\.)'), r'\1 \2'))

        # no sentence break after specific abbreviations
        self.__final.append((re_compile(r'\b(e\. ?g\.|i\. ?e\.|i\. ?v\.|vs\.|cf\.|Dr\.|Mr\.|Ms\.|Mrs\.)\n'), r'\1 '))

        # or others taking a number after the abbrev
        self.__final.append((re_compile(r'\b([Aa]pprox\.|[Nn]o\.|[Ff]igs?\.)\n(\d+)'), r'\1 \2'))

        # no break before comma (e.g. Smith, A., Black, B., ...)
        self.__final.append((re_compile(r'(\.\s*)\n(\s*,)'), r'\1 \2'))

    def _further_refine_split(self, s: str) -> str:
        """
        Given a string with sentence splits as newlines, attempts to
        heuristically improve the splitting. Heuristics tuned for geniass
        sentence splitting errors.
        
        :param s: 
        :return: 
        """

        for r, t in self.__initial:
            s = r.sub(t, s)

        for r, t in self.__repeated:
            while True:
                n = r.sub(t, s)
                if n == s:
                    break
                s = n

        for r, t in self.__final:
            s = r.sub(t, s)

        return s

    def _refine_split(self, offsets, original_text):
        # Postprocessor expects newlines, so add. Also, replace
        # sentence-internal newlines with spaces not to confuse it.
        new_text = '\n'.join((original_text[o[0]:o[1]].replace('\n', ' ')
                              for o in offsets))

        output = self._further_refine_split(new_text)

        # Align the texts and see where our offsets don't match
        old_offsets = offsets[::-1]
        # Protect against edge case of single-line docs missing
        #   sentence-terminal newline
        if len(old_offsets) == 0:
            old_offsets.append((0, len(original_text),))
        new_offsets = []
        for refined_sentence in output.split('\n'):
            new_offset = old_offsets.pop()
            # Merge the offsets if we have received a corrected split
            while new_offset[1] - new_offset[0] < len(refined_sentence) - 1:
                _, next_end = old_offsets.pop()
                new_offset = (new_offset[0], next_end)
            new_offsets.append(new_offset)

        # Protect against missing document-final newline causing the last
        #   sentence to fall out of offset scope
        if len(new_offsets) != 0 and new_offsets[-1][1] != len(original_text) - 1:
            start = new_offsets[-1][1] + 1
            while start < len(original_text) and original_text[start].isspace():
                start += 1
            if start < len(original_text) - 1:
                new_offsets.append((start, len(original_text) - 1))

        # Finally, inject new-lines from the original document as to respect the
        #   original formatting where it is made explicit.
        last_newline = -1
        while True:
            try:
                orig_newline = original_text.index('\n', last_newline + 1)
            except ValueError:
                # No more newlines
                break

            for o_start, o_end in new_offsets:
                if o_start <= orig_newline < o_end:
                    # We need to split the existing offsets in two
                    new_offsets.remove((o_start, o_end))
                    new_offsets.extend(((o_start, orig_newline,),
                                        (orig_newline + 1, o_end),))
                    break
                elif o_end == orig_newline:
                    # We have already respected this newline
                    break
            else:
                # Stand-alone "null" sentence, just insert it
                new_offsets.append((orig_newline, orig_newline,))

            last_newline = orig_newline

        new_offsets.sort()
        return new_offsets

    def _sentence_boundary_gen(self, text, regex):
        for match in regex.finditer(text):
            yield match.span()

    def split_sentence(self, text):
        for o in self._refine_split([_o for _o in self._sentence_boundary_gen(
                text, self._sentence_boundary_regex)], text):
            yield o


class StringComposer(object):

    def __init__(self, sets: List[str], documents: Dict[str, 'annotationobjects.Document']) -> None:
        """

        :param sets: 
        :param documents: 
        """
        self._sets = sets
        self._documents = documents
        self._max_set_length = len(max(self._sets, key=len))

    def _get_statistics(self, ann_sets: Set[str], value_dict: Dict[str, Dict[str, int]]):

        """

        :param ann_sets: 
        :param value_dict: 
        :return: 
        """
        p1 = "{} | {}\n".format(" " * self._max_set_length, "  ".join(sorted(ann_sets)))
        p2 = "{}\n".format("-" * len(p1))

        pn = list()
        for s in sorted(self._documents.keys()):
            pn.append("{:>{width}} | ".format(s, width=self._max_set_length))
            for t in sorted(ann_sets):
                n = value_dict[s][t]
                pn.append((str(n)).center(len(t) + 2))
            pn.append("\n")

        return p1, p2, pn

    # def _get_entity_count(self) -> Tuple[Set[str], Dict[str, Dict[str, int]]]:
    #     """
    #
    #     :return:
    #     """
    #     ann_types = AnnotationTypes.entity_types()
    #     count_dict = {s: {t: len((self._documents[s]).get_triggers(t))
    #                       for t in ann_types} for s in self._sets}
    #     return ann_types, count_dict
    #
    # def _get_event_count(self) -> Tuple[Set[str], Dict[str, Dict[str, int]]]:
    #     """
    #
    #     :return:
    #     """
    #     ann_types = AnnotationTypes.event_types()
    #     count_dict = {s: {t: len((self._documents[s]).get_events(t))
    #                       for t in ann_types} for s in self._sets}
    #     return ann_types, count_dict
    #
    # def _get_relation_count(self) -> Tuple[Set[str], Dict[str, Dict[str, int]]]:
    #     """
    #
    #     :return:
    #     """
    #     ann_types = AnnotationTypes.relation_types()
    #     count_dict = {s: {t: len((self._documents[s]).get_relations(t))
    #                       for t in ann_types} for s in self._sets}
    #     return ann_types, count_dict

    def _print_out(self, ann_types: Set[str], count_dict: Dict[str, Dict[str, int]]) -> None:
        """

        :param ann_types: 
        :param count_dict: 
        """
        p1, p2, pn = self._get_statistics(ann_types, count_dict)
        print(p1 + p2 + "".join(pn))

    # def print_out(self, atype: str) -> None:
    #     """
    #
    #     :param atype:
    #     """
    #     if atype == "entities":
    #         self._print_out(*self._get_entity_count())
    #     elif atype == "events":
    #         self._print_out(*self._get_event_count())
    #     elif atype == "relations":
    #         self._print_out(*self._get_relation_count())
    #     else:
    #         self._print_out(*self._get_entity_count())
    #         self._print_out(*self._get_event_count())
    #         self._print_out(*self._get_relation_count())


class AgreementScores(object):
    # TODO: add functionality for approximate matching!
    # TODO: check if trigger is valid
    # TODO: add prec/rec to DataFrame
    """
    Agreement is calculated as the averaged pairwise F-Score metric, since negative entities
    (i.e. no annotation for any of the defined triggers) are large and basically unknown.
    """

    def __init__(self, comp_obj: 'Comparison', trigger: str) -> None:
        """

        :type trigger: object
        :type comp_obj: object
        """
        self._comparison = comp_obj
        self._trigger = None if (trigger.lower() == 'all') else trigger.title()
        _dim = len(self._comparison.get_sets())
        self._f1_score_strict = None
        self._f1_score_approx = dict()
        self._f1_score_one_all = None
        self._sets = [self._comparison.get_sets()[i] for i in range(_dim)]
        self._centroid_object = Centroids(self._comparison)
        self._general_dataframe = DataFrame(data=zeros((_dim, _dim*3)), index=self._sets,
                                            columns=[_s + '_' + _i for _s in self._sets
                                                     for _i in ['fscore', 'precision', 'recall']])
        self._last_centroid_values = None
        self._errors = {'strict': {'false_neg': [], 'false_pos': []},
                        'approximate': {'false_neg': [], 'false_pos': []},
                        'one_all': {'false_neg': defaultdict(list), 'false_pos': defaultdict(list)}}

        self._calc_scores()

    def _strict_matching(self, _doc1: annotationobjects.Document, _doc2: annotationobjects.Document):
        _t1 = set([str(_t.get_span()) for _t in _doc1.get_triggers(self._trigger).values()])
        _t2 = set([str(_t.get_span()) for _t in _doc2.get_triggers(self._trigger).values()])

        _precision = None
        _recall = None
        if len(_t1) > 0:
            _recall = len(_t1.intersection(_t2)) / len(_t1)
        if (len(_t1) + len(_t2)) > 0:
            _precision = len(_t1.intersection(_t2)) / len(_t2) if len(_t2) > 0 else 0.0

        return _precision, _recall

    def _approx_matching(self, _doc1: annotationobjects.Document, _doc2: annotationobjects.Document, _boundary: int=0):
        # TODO: account for multiple word span annotations
        # TODO: precision/recall values for no gold annos! (cf. strict and one_all)
        _mean_word_len = round(
            len(re_sub("\s+", "", self._comparison.get_text())) / len(self._comparison.get_text().split()))
        _approx = _mean_word_len + _boundary
        if _approx < 0:
            _approx = 0
        _matches = 0
        _t1_count = len(_doc1.get_triggers(self._trigger))
        _t2_count = len(_doc2.get_triggers(self._trigger))
        for _trigger1 in _doc1.get_triggers(self._trigger).values():
            for _t1_begin, _t1_end in zip(*_trigger1.get_span()):
                for _trigger2 in _doc2.get_triggers(self._trigger).values():
                    for _t2_begin, _t2_end in zip(*_trigger2.get_span()):
                        if ((_t2_begin in range(_t1_begin - _approx if (_t1_begin - _approx > 0) else 0, _t1_end)) and
                            (_t2_end in range(_t1_begin, _t1_end + _approx if (_t1_end + _approx < len(self._comparison.get_text())) else len(self._comparison.get_text()) + 1))) or\
                            ((_t1_begin in range(_t2_begin - _approx if (_t2_begin - _approx > 0) else 0, _t2_end)) and
                                (_t1_end in range(_t2_begin, _t2_end + _approx if (_t2_end + _approx < len(self._comparison.get_text())) else len(self._comparison.get_text()) + 1))):
                            _matches += 1
        _precision = _matches/_t2_count if _t2_count > 0 else 0.0
        _recall = _matches/_t1_count if _t1_count > 0 else 0.0
        return _precision, _recall

    def _one_vs_all_matching(self, _set: str, _threshold: int=0, _boundary: int=0, _rm_whitespace: bool=True)\
            -> Tuple[float, float]:
        # TODO: restrict _threshold/_boundary values to max values that make sense
        # TODO: e.g. _threshold max is 'number of sets/annotators - 1' (i.e. where all 'others' agree on an annotation)
        # TODO: e.g. _boundary max is '_threshold max - 1' (i.e. distribution of centr. is  min 1 lower than it itself)
        # using centroid for precision and recall
        _one = self._comparison.get_sets().index(_set)
        _other = self._comparison.get_sets().copy()
        _other.remove(_set)
        _all_list = [_obj.return_self(_threshold, _boundary) for _obj in self._centroid_object.get_centroid_objects(
            self._trigger, rm_whitespace=_rm_whitespace, sets=[self._comparison.get_sets().index(i) for i in _other]) if _obj is not None]
        _one_list = self._centroid_object.get_centroid_objects(
            self._trigger, rm_whitespace=_rm_whitespace, sets=[_one])

        _all_list = [_a for _a in _all_list if _a is not None]
        _one_list = [_o for _o in _one_list if _o is not None]
        _matches = 0
        _b = _boundary
        _cent_errors = {}
        _anno_errors = {}
        for _cent in _all_list:
            _cent_errors[_cent] = False
            for _anno in _one_list:
                if _anno_errors.get(_anno, None) is None:
                    _anno_errors[_anno] = False
                # annotation includes whole of centroid heart!
                if (_cent.local_maximum()[0] in range(_anno.left_extend(), _anno.right_extend() + 1)) and\
                        (_cent.local_maximum()[1] in range(_anno.left_extend(), _anno.right_extend() + 1)):
                    # neither annotation boundary may lie outside the distribution
                    if (_anno.left_extend() in range(_cent.left_extend(_b), _cent.right_extend(_b) + 1)) and \
                            (_anno.right_extend() in range(_cent.left_extend(_b), _cent.right_extend(_b) + 1)):
                        _matches += 1
                        _cent_errors[_cent] = True
                        _anno_errors[_anno] = True
        if len(_all_list) > 0:
            _precision = _matches / len(_one_list) if len(_one_list) > 0 else 0.0
            _recall = _matches / len(_all_list) if len(_all_list) > 0 else 0.0
        elif len(_all_list) == 0 and len(_one_list) > 0:
            _precision = 0.0
            _recall = None
        else:
            _precision = None
            _recall = None

        self._errors['one_all']['false_neg']['t{}_b{}'.format(_threshold, _boundary)] += \
            [_cent[0] for _cent in _cent_errors.items() if _cent[1] is False]
        self._errors['one_all']['false_pos']['t{}_b{}'.format(_threshold, _boundary)] += \
            [_anno[0] for _anno in _anno_errors.items() if _anno[1] is False]
        return _precision, _recall

    def _f_score(self, _sid1, _sid2, _match_type='strict', _threshold: int=0, _boundary: int=0,
                 _rm_whitespace: bool=True):
        _df = Union[None, DataFrame]
        if _match_type is 'strict':
            if self._f1_score_strict is None:
                self._f1_score_strict = self._general_dataframe.copy()
            _df = self._f1_score_strict
        elif _match_type is 'approximate':
            if self._f1_score_approx.get(_boundary, None) is None:
                self._f1_score_approx[_boundary] = self._general_dataframe.copy()
            _df = self._f1_score_approx[_boundary]
        elif _match_type is 'one_all':
            if self._f1_score_one_all is None:
                self._f1_score_one_all = \
                    DataFrame(data=zeros((len(self._sets), 3)), index=self._sets,
                              columns=['other_fscore', 'other_precision', 'other_recall'])
            _df = self._f1_score_one_all

        if _sid1 != _sid2:
            _precision, _recall = None, None
            if _match_type is not 'one_all':
                _doc1 = self._comparison.get_set_document(_sid1)
                _doc2 = self._comparison.get_set_document(_sid2)
                if _match_type is 'strict':
                    _precision, _recall = self._strict_matching(_doc2, _doc1)
                elif _match_type is 'approximate':
                    _precision, _recall = self._approx_matching(_doc2, _doc1, _boundary)
            else:
                _precision, _recall = self._one_vs_all_matching(_sid1, _threshold, _boundary,
                                                                _rm_whitespace=_rm_whitespace)
                _sid2 = _sid2[0]

            if _precision is None or _recall is None:
                _df.at[_sid1, _sid2 + "_fscore"] = NaN
                _df.at[_sid1, _sid2 + "_precision"] = round(_precision, 2) if _precision is not None else NaN
                _df.at[_sid1, _sid2 + "_recall"] = round(_recall, 2) if _recall is not None else NaN
            elif _precision + _recall > 0.0:
                _fscore = (2 * _precision * _recall) / (_precision + _recall)
                _df.at[_sid1, _sid2 + "_fscore"] = round(_fscore, 2)
                _df.at[_sid1, _sid2 + "_precision"] = round(_precision, 2)
                _df.at[_sid1, _sid2 + "_recall"] = round(_recall, 2)
            else:
                _df.at[_sid1, _sid2 + "_fscore"] = 0.0
                _df.at[_sid1, _sid2 + "_precision"] = round(_precision, 2)
                _df.at[_sid1, _sid2 + "_recall"] = round(_recall, 2)
        else:
            _df.at[_sid1, _sid2 + "_fscore"] = NaN
            _df.at[_sid1, _sid2 + "_precision"] = NaN
            _df.at[_sid1, _sid2 + "_recall"] = NaN

    def _calc_scores(self, _match_type='strict', _threshold: int=0, _boundary: int=0, _rm_whitespace: bool=True):
        # TODO: warning for unreasonable set threshold/boundary -> i.e. larger than sets
        # TODO: maybe even put check in centroids
        for _s1 in self._sets:
            if _match_type is 'one_all':
                _s2 = ['other']
                self._f_score(_s1, _s2, _match_type, _threshold, _boundary, _rm_whitespace=_rm_whitespace)
            else:
                _precision = 0.0
                _recall = 0.0
                for _s2 in self._sets:
                    self._f_score(_s1, _s2, _match_type, _threshold, _boundary)
                    if _match_type is 'strict':
                        _df = self._f1_score_strict
                    elif _match_type is 'approximate':
                        _df = self._f1_score_approx[_boundary]
                    if _s1 != _s2:
                        _precision += _df.at[_s1, _s2 + "_precision"]
                        _recall += _df.at[_s1, _s2 + "_recall"]
                _precision /= (len(self._sets) - 1)
                _recall /= (len(self._sets) - 1)
                _fscore = (2 * _precision * _recall) / (_precision + _recall)
                _df.at[_s1, "all_fscore"] = round(_fscore, 2)
                _df.at[_s1, "all_precision"] = round(_precision, 2)
                _df.at[_s1, "all_recall"] = round(_recall, 2)

    def return_errors(self, match_type='strict', error_type='both', threshold=0, boundary=0, rm_whitespace: bool=True,
                      focus_annotator=None):
        # TODO: something's wrong with this function (?)
        if match_type.lower() not in _match_types:
            raise ValueError("Invalid match type. Expected one of: {}".format(_match_types))
        _focus = None
        if type(focus_annotator) is str:
            if focus_annotator.lower() not in self._sets:
                print("Focus Annotator not in Annotator set; ignoring parameter")
            else:
                _focus = focus_annotator
        elif focus_annotator is not None:
            print("No suitable type of focus annotator; has to be of str")

        self._calc_scores(match_type, threshold, boundary, _rm_whitespace=rm_whitespace)
        _false_neg = set(self._errors.get(match_type).get('false_neg').get('t{}_b{}'.format(threshold, boundary)))
        _false_pos = set(self._errors.get(match_type).get('false_pos').get('t{}_b{}'.format(threshold, boundary)))
        if _focus:
            _focus_id = self._sets.index(_focus)
            _false_pos = {_cent for _cent in _false_pos if _focus_id in _cent._sets}
            _false_neg = {_cent for _cent in _false_neg if _focus_id not in _cent._sets}
        if error_type == 'both':
            return _false_neg.union(_false_pos)
        elif error_type == 'false_neg':
            return _false_neg
        elif error_type == 'false_pos':
            return _false_pos
        else:
            pass

    def get_dataframe(self, match_type='strict', threshold: int=0, boundary: int=0, rm_whitespace: bool=True):
        if match_type.lower() not in _match_types:
            raise ValueError("Invalid match type. Expected one of: {}".format(_match_types))

        if match_type == 'strict':
            if self._f1_score_strict is None:
                self._calc_scores('strict')
            return self._f1_score_strict
        elif match_type == 'approximate':
            if self._f1_score_approx.get(boundary, None) is None:
                self._calc_scores('approximate', _boundary=boundary)
            return self._f1_score_approx.get(boundary)
        elif match_type == 'one_all':
            if self._last_centroid_values is (threshold, boundary):
                pass
            else:
                self._calc_scores('one_all', threshold, boundary, _rm_whitespace=rm_whitespace)
                self._last_centroid_values = (threshold, boundary)
            return self._f1_score_one_all


class Comparison(object):
    def __init__(self, docid: str, slist: list, froot: str) -> None:
        """
        Creates a comparison object of multiple annotations for a specific document ('docid').
        The path to the document is given by 'froot' + 'slist[i]' + 'docid'.
        
        :param docid: id of a document
        :type docid: str
        :param slist: list of the different sets/annotators
        :type slist: list
        :param froot: path to the root of the document folder
        :type froot: str
        """

        self._id = docid
        self._sets = [_set.split("/") for _set in slist]
        self._root_dir = froot
        self._documents = dict()
        self._text = ""
        self._sent_splitter = BratRegEx() # ToDo: configurable Sentence Splitter
        self._max_set_length = len(max([_set[0] for _set in self._sets]))
        self._agreement_score_dict = dict()
        self._trigger_set = None

        self._load_documents()

    def _load_documents(self) -> None:
        """
        :return: None
        """
        doc = None
        for _sid in sorted(self._sets):
            doc = annotationobjects.Document(self._id, self._root_dir, os.path.join(*_sid))
            self._documents[_sid[0]] = doc
        if doc:
            self._text = doc.get_text()

    def _create_agreement_scores(self, trigger: str = 'All') -> bool:
        """
        Creates an AgreementScores object and stores it in a dictionary

        :param trigger: name of a specific trigger from properties.trigger_types() or 'All'
        :return: bool
        """
        if trigger.lower() == 'all':
            _trigger_list = list(self.get_trigger_set())
        elif trigger.lower() in [t.lower() for t in self.get_trigger_set()]:
            _trigger_list = [trigger.lower().title()]
        else:
            return False
        for _trigger in _trigger_list:
            if not self._agreement_score_dict.get(_trigger, None):
                self._agreement_score_dict[_trigger] = AgreementScores(self, _trigger)
        return True

    def get_id(self) -> str:
        """
        
        :return: 
        """
        return self._id

    def get_text(self) -> str:
        """
        :return: Text of the document as string
        """
        return self._text

    def get_set_document(self, dset: str) -> annotationobjects.Document:
        """
        :param dset: name of a set/annotator
        :return: annotationsobject.Document
        """
        return self._documents.get(dset, None)

    def get_trigger_set(self) -> Counter:
        if self._trigger_set is None:
            self._trigger_set = Counter()

            for _doc in self._documents.values():
                self._trigger_set += _doc.get_type_count_of('trigger')

        return self._trigger_set

    def return_agreement_scores(self, trigger: str, match_type: str = 'strict',
                                threshold: int=0, boundary: int=0, rm_whitespace: bool=True) -> Union[DataFrame, None]:
        """
        :param trigger: name of a specific trigger from properties.trigger_types() or 'All'
        :param match_type: 
        :param threshold:
        :param boundary: 
        :return: pandas.DataFrame
        """
        # TODO: some handling for 'All' triggers
        if trigger is not None and self._create_agreement_scores(trigger.title()):
            return self._agreement_score_dict[trigger.title()].get_dataframe(match_type, threshold, boundary,
                                                                             rm_whitespace=rm_whitespace)
        else:
            return DataFrame(data={'None': None})

    def return_errors(self, trigger, threshold=0, boundary=0, match_type='strict', error_type='both',
                      rm_whitespace=True, focus_annotator=None):
        if self._create_agreement_scores(trigger):
            _agreement = self._agreement_score_dict.get(trigger)
            if _agreement:
                return _agreement.return_errors(match_type, error_type, threshold, boundary,
                                                rm_whitespace=rm_whitespace, focus_annotator=focus_annotator)

    # Todo: yields only sentences that contain an annotation. Do I want that to be forced or should there be an arg?
    def sent_compare_generator(self) -> Generator:
        _sent_nr = 0
        for _offset in self._sent_splitter.split_sentence(self._text):
            _begin, _end = _offset
            _sent_nr += 1
            _contains_ann = False
            _sentence = self._text[_begin:_end]
            _triggers = {_a: [] for _a in self.get_sets()}

            for _id, _doc in sorted(self._documents.items(), key=operator.itemgetter(0)):
                _sent_vector = list()
                for _trigger in _doc.get_triggers().values():
                    _trig_span = _trigger.get_span()
                    for _frag in range(len(_trig_span[0])):
                        _trig_span_b = _trig_span[0][_frag]
                        _trig_span_e = _trig_span[1][_frag]
                        if _begin <= _trig_span_b <= _end:
                            _contains_ann = True
                            _sent_vector.append((_trig_span_b, _trig_span_e, _trigger))
                _sent_vector.sort()
                _tmp = _begin

                for _o in _sent_vector:
                    _s_begin = _o[0] - _begin
                    _s_end = _o[1] - _begin
                    _type = _o[2].get_type()
                    _tid = _o[2].get_id()

                    _triggers[_id].append([_tid, _type, [[_s_begin, _s_end]]])

                    _tmp = _o[1]

            if _contains_ann:
                yield (_sentence, _triggers)

    def print_general_statistics(self, atype: str = None) -> None:
        """
        Prints general statistics for the mentioned 'atype' or for all if none is given.

        :param atype: (optional) one of 'relations', 'events' or 'entities'
        :return: None
        """
        if type(atype) is str:
            atype = atype.lower()

        print("\n[Document] {} [Document]\n".format(self._id))
        sc = StringComposer([_set[0] for _set in self._sets], self._documents)
        sc.print_out(atype)

    def get_sets(self) -> List[str]:
        """
        :return: list of str
        """
        return sorted([_s[0] for _s in self._sets])

    def list_specific_trigger(self, trigger: str, _return: bool = False, counter: bool = False) -> Union[set, 'Counter']:
        """
        :param trigger: name of a specific trigger from properties.trigger_types() or 'All'
        :param _return: (optional) boolean whether to print results or return them
        :param counter: (optional) boolean whether to create a counter object or just a set
        :return: set of the specified triggers
        """
        _trigger_list = list()
        _ann_trig_dict = defaultdict(list)
        for _doc in self._documents.values():
            _triggers = _doc.get_triggers(trigger)
            if _triggers:
                for _t in _triggers.values():
                    if counter:
                        _text = _t.get_text() + "_" + str(_t.get_span())
                        _trigger_list.append(_text)
                        _ann_trig_dict[_text].append(_doc._set)
                    else:
                        _trigger_list.append(_t.get_text())
        if _return:
            if counter:
                return Counter(_trigger_list), _ann_trig_dict
            else:
                return set(sorted(_trigger_list))
        if counter:
            print(Counter(_trigger_list))
        else:
            print(set(sorted(_trigger_list)))

    def get_triggers_for_annotator(self, annotator) -> 'Counter':
        _doc = self.get_set_document(annotator)
        return _doc.get_type_count_of('trigger')


class BatchComparison(object):

    def __init__(self, index, set_list, root, init_comp=True):
        """
        :param index:
        :param set_list:
        :param root:
        """
        self._files = set()
        self._sets = set_list
        self._root = root
        self._comparison = dict()
        self._trigger_set = None
        self._init = False

        if isinstance(index, str):
            try:
                with open(index, 'r', encoding=annotationobjects.ENCODING) as ifile:
                    for _doc_id in ifile.readlines():
                        _doc_id = _doc_id.rstrip("\n")
                        self._files.add(_doc_id)
            except FileNotFoundError:
                print("[Error] There is no index file under root '{}' .".format(index))

        elif isinstance(index, list) or isinstance(index, set):
            self._files = set(index)

        if init_comp:
            self._load_comparison()

    def _load_comparison(self):
        if not self._init:
            for fi in self._files:
                comp = Comparison(fi, self._sets, self._root)
                self._comparison[fi] = comp
            self._init = True

    def init_comparison(self):
        self._load_comparison()

    def get_comparison_obj(self, document):
        self._load_comparison()
        if document in self._files:
            _comp_obj = self._comparison[document]
            return _comp_obj

    def doc_iterator(self):
        for _doc in self._files:
            # print("### Document: {} ###".format(_doc))
            yield _doc

    def doc_list(self):
        return self._files

    def compare_doc(self, document):
        self._load_comparison()
        if document in self._files:
            _comp_obj = self._comparison[document]
            return _comp_obj.sent_compare_generator()

    def print_statistics(self, document):
        self._load_comparison()
        if document in self._files:
            _comp_obj = self._comparison[document]
            _comp_obj.print_general_statistics()

    def return_agreement(self, trigger, document='All', match_type='strict', threshold=0, boundary=0,
                        rm_whitespace=True):
        self._load_comparison()
        _sets = [_set.split("/")[0] for _set in self._sets]
        if document.lower() != 'all':
            if document in self._files:
                _comp_obj = self._comparison[document]
                return _comp_obj.return_agreement_scores(trigger, match_type, threshold, boundary,
                                                         rm_whitespace=rm_whitespace)
        else:
            # TODO: cache the calculation
            _compl_df = None
            if match_type == 'one_all':
                _df_count = DataFrame(data=zeros((len(_sets), 3)), index=_sets,
                                      columns=['other_fscore', 'other_precision', 'other_recall'])
            else:
                _df_count = DataFrame(data=zeros((len(_sets), len(_sets)*3)), index=_sets, columns=[_s + '_' + _i for _s in _sets
                                                     for _i in ['fscore', 'precision', 'recall']])

            for _doc in self._files:
                _comp_obj = self._comparison[_doc]
                _df = _comp_obj.return_agreement_scores(trigger, match_type, threshold, boundary,
                                                        rm_whitespace=rm_whitespace)
                if _df is not None:
                    _df_count = _df_count.add(DataFrame(_df.notnull(), dtype="float64"), fill_value=0)
                    if _compl_df is None:
                        _compl_df = _df.copy()
                    else:
                        _compl_df = _compl_df.add(_df, fill_value=0)
            _compl_df = _compl_df / _df_count
            if match_type == 'one_all':
                for _row in range(_compl_df.shape[0]):
                    _precision = _compl_df.iloc[_row, 1]
                    _recall = _compl_df.iloc[_row, 2]
                    _compl_df.iloc[_row, 0] = (2 * _precision * _recall) / (_precision + _recall)
            else:
                for _row in range(_compl_df.shape[0]):
                    for _col in range(_compl_df.shape[0]):
                        if _row != _col:
                            _act_col = _col*3
                            _precision = _compl_df.iloc[_row, _act_col+1]
                            _recall = _compl_df.iloc[_row, _act_col+2]
                            _compl_df.iloc[_row, _act_col] = (2 * _precision * _recall) / (_precision + _recall)

            return _compl_df.round(2)

    def print_agreement(self, trigger, document='All', match_type='strict', threshold=0, boundary=0,
                        rm_whitespace=True):
        print()
        if document.lower() != "all":
            if document in self._files:
                print("### Document: {} ###".format(document))
            else:
                print("No such Document: '{}'".format(document))
                return
        else:
            print("### All Documents ###")
        print("### Entity/Event types: {}, Matching: {} ###".format(trigger.upper(), match_type))
        print(self.return_agreement(trigger, document, match_type, threshold, boundary, rm_whitespace))

    def list_specific_trigger(self, trigger, document, _return=False, counter=False):
        self._load_comparison()
        _comp = self._comparison.get(document, None)
        if _comp:
            if _return:
                return _comp.list_specific_trigger(trigger, _return, counter)
            _comp.list_specific_trigger(trigger, _return, counter)

    def get_sets(self) -> List[str]:
        """
        :return: list of str
        """
        return sorted([_s.split("/")[0] for _s in self._sets])

    def get_trigger_set(self):
        self._load_comparison()
        if self._trigger_set is None:
            self._trigger_set = Counter()
            for _comp in self._comparison.values():
                self._trigger_set.update(_comp.get_trigger_set())
        return self._trigger_set
