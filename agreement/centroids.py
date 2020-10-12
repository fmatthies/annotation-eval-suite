# -*- coding: utf-8 -*-

import re
import sqlite3

from typing import Dict, List, Tuple, Union
from numpy import zeros
from numpy import array
from collections import defaultdict


class CentroidObject(object):
    # TODO: _borders has unnecessary many entries: e.g. _borders[3] also has information about 0,1 & 2!
    # TODO: fix it in _get_centroid_distribution
    def __init__(self, parent: 'Centroids', plateau: Tuple, trigger: str, rm_whitespace: bool = True,
                 sets: List[int] = None) -> None:
        """

        :param parent:
        :param plateau:
        :param trigger:
        :param rm_whitespace:
        """
        self._centroid_parent = parent
        self._local_maximum = plateau
        self._trigger = trigger
        self._no_whitespace = True if rm_whitespace else False
        self._text = self._centroid_parent.get_text(rm_whitespace)[plateau[0]:plateau[1] + 1]
        self._max_agreement = None
        self._borders = dict()
        self._sets = sorted(sets)
        # first init #TODO: but this way I get all information for all boundaries
        self._get_centroid_distribution()

    def _get_centroid_distribution(self, _boundary: int = 0) -> None:
        """

        :param _boundary: value at which to cut off the distribution, that is, the number of agreements that
        shouldn't be taken as inside of the "right" annotation
        :return:
        """
        if _boundary in self._borders.keys():
            return
        _borders = {'left': list(), 'right': list()}
        _distr = self._centroid_parent.get_anno_distribution(self._trigger, self._no_whitespace, self._sets)
        if self._max_agreement is None:
            self._max_agreement = int(_distr[self._local_maximum[0]])
        # goes left from centroid
        _count = 0
        _value = int(_distr[self._local_maximum[0]])
        _pos_value = _value
        _distance = 0
        while True:
            _count -= 1
            _pos = self._local_maximum[0] + _count
            if _pos < 0:
                (_borders['left']).append((_distance, _value))
                break
            if _distr[_pos] <= _boundary:
                _value = _pos_value - int(_distr[_pos])
                (_borders['left']).append((_distance, _value))
                break
            if _distr[_pos] != _pos_value:
                _value = _pos_value - int(_distr[_pos])
                _pos_value = int(_distr[_pos])
                (_borders['left']).append((_distance, _value))
            _distance += 1
        # goes right from centroid
        _count = 0
        _value = int(_distr[self._local_maximum[1]])
        _pos_value = _value
        _distance = 0
        while True:
            _count += 1
            _pos = self._local_maximum[1] + _count
            if _pos >= len(_distr):
                (_borders['right']).append((_distance, _value))
                break
            if _distr[_pos] <= _boundary:
                _value = _pos_value - int(_distr[_pos])
                (_borders['right']).append((_distance, _value))
                break
            if _distr[_pos] != _pos_value:
                _value = _pos_value - int(_distr[_pos])
                _pos_value = int(_distr[_pos])
                (_borders['right']).append((_distance, _value))
            _distance += 1
        self._borders[_boundary] = _borders

    def _check_threshold_cache(self, _boundary: int = 0):
        """

        :param _boundary: value at which to cut off the distribution, that is, the number of agreements that
        shouldn't be taken as inside of the "right" annotation
        :return:
        """
        if self._borders.get(_boundary, None) is None:
            return False
        else:
            return True

    def local_maximum(self) -> Tuple[int]:
        """
        
        :return: 
        """
        return self._local_maximum

    def left_extend(self, boundary: int = 0) -> int:
        """
        
        :param boundary: 
        :return: position in the array where the last character of this centroid (given its boundaries) lies 
        """
        if not self._check_threshold_cache(boundary):
            self._get_centroid_distribution(boundary)
        return self._local_maximum[0] - self._borders[boundary]['left'][-1][0]

    def right_extend(self, boundary: int = 0) -> int:
        """

        :param boundary: 
        :return: position in the array where the last character of this centroid (given its boundaries) lies 
        """
        if not self._check_threshold_cache(boundary):
            self._get_centroid_distribution(boundary)
        return self._local_maximum[1] + self._borders[boundary]['right'][-1][0]

    def return_self(self, threshold: int, boundary: int = 0) -> Union['CentroidObject', None]:
        """
        
        :param threshold: value for the agreement count, that the local maximum of the centroid should be at least 
        :param boundary: value at which to cut off the distribution , that is, the number of agreements that
        shouldn't be taken as inside of the "right" annotation
        :return:
        """
        if not self._check_threshold_cache(boundary):
            self._get_centroid_distribution(boundary)
        if self._max_agreement < threshold:
            return
        return self

    def print_self(self, boundary: int = 0) -> None:
        """

        :param boundary: value at which to cut off the distribution , that is, the number of agreements that
        shouldn't be taken as inside of the "right" annotation
        :return:
        """
        _left = self.left_extend(boundary)
        _right = self.right_extend(boundary)
        _array = self._centroid_parent.get_anno_distribution(self._trigger, self._no_whitespace, self._sets)
        print("Centroid( {} ): '{}' -- Borders: {}".format(
            [self._centroid_parent._comp_obj._sets[_i][0] for _i in self._sets],
            self._text, self._borders[boundary]))
        print(_array[_left:_right + 1])


class Centroids(object):
    # TODO: thresholding

    def __init__(self, text: str, annotators: list):
        """
        Short description and reference to Centroids algorithm

        """
        self._centroid_matrices = dict()
        self._white_space_mask = None
        self._text_wo_whitespace = None
        self._centroid_objects_dict = defaultdict(list)
        self._text = text
        self._annotators = sorted(annotators)

    def _create_trigger_matrix(self, _trigger: str) -> None:
        """
        Desc

        :param _trigger: One of properties.trigger_types()
        :type _trigger: str
        :return: None
        """
        if _trigger in self._centroid_matrices.keys():
            return
        _matrix = zeros(shape=(len(self._annotators), len(self._text)))
        for i in range(len(self._annotators)):
            _doc_obj = self._comp_obj.get_set_document(self._sets[i])
            _trigger_dict = _doc_obj.get_triggers(_trigger)
            self._add_spans_to_array(_trigger_dict, _matrix, i)
        self._centroid_matrices[_trigger] = _matrix

    def _discount_whitespace(self, _anno_array: array) -> array:
        """
        Creates an internal, reusable whitespace mask if it's not already there and returns the input _anno_array
        with all whitespace positions removed

        :param _anno_array: array that represents annotation counts for all sets
        :return: array with all positions removed that contained whitespace
        """
        if self._white_space_mask is None:
            _text = self._comp_obj.get_text()
            self._white_space_mask = zeros(len(_anno_array), dtype=bool)
            for _ws in re.finditer("\s+", _text):
                for _pos in range(_ws.start(), _ws.end()):
                    self._white_space_mask[_pos] = True
        return _anno_array[~self._white_space_mask]

    def _get_text_wo_whitespace(self) -> str:
        if self._white_space_mask is None:
            self._discount_whitespace(self._get_centroid_array('Medication'))
        if self._text_wo_whitespace is None:
            self._text_wo_whitespace = \
                "".join([_w for _w in array(list(self._comp_obj.get_text()), dtype=str)[~self._white_space_mask]])
        return self._text_wo_whitespace

    def _add_spans_to_array(self, _trigger_dict: Dict[str, 'annotationobjects.Trigger'],
                            _matrix: array, _m_position: int) -> None:
        """
        Iterates all Triggers in _trigger_dict and populates row _m_position of _matrix with occurrence counts

        :param _trigger_dict: the trigger dictionary to iterate
        :param _matrix: the matrix of type numpy.array to populate
        :param _m_position: number of row; in accordance with position of the specific set in the set_list
        :return: None
        """
        # goes through all triggers of type 'trigger'
        for _id, _trigger in _trigger_dict.items():
            _spans = _trigger.get_span()  # Tuple(List[Begin], List[End])
            # lists all spans if the 'trigger' covers multiple separated tokens
            for _span in zip(_spans[0], _spans[1]):
                _matrix[_m_position, _span[0]:_span[1]] += 1

    def _get_centroid_array(self, _trigger: str, _sets: List[int] = None) -> array:
        if self._centroid_matrices.get(_trigger, None) is None:
            self._create_trigger_matrix(_trigger)
        if (_sets is None) or (not isinstance(_sets, list)):
            return self._centroid_matrices.get(_trigger).sum(axis=0)
        if max(_sets) >= len(self._comp_obj.get_sets()):
            raise ValueError('You provided "{}" in your set list, but "{}" is the maximum allowed number!'
                             .format(str(max(_sets)), len(self._comp_obj.get_sets()) - 1))
        return (self._centroid_matrices.get(_trigger))[_sets].sum(axis=0)

    def _correct_plateau(self, _plateau: List[int]) -> Tuple[int]:
        _new_plateau = list()
        if len(_plateau) == 1:
            _new_plateau = tuple((_plateau[0], _plateau[0]))
        else:
            _plateau.reverse()
            for i in range(len(_plateau)):
                _new_plateau.insert(0, _plateau[i])
                if (i + 1 < len(_plateau)) and (_plateau[i + 1] == _plateau[i] - 1):
                    continue
                break
        return tuple([_new_plateau[0], _new_plateau[-1]])

    def _find_local_plateaus(self, _anno_array: array, _rm_whitespace: bool = True) -> List[Tuple]:
        """
        Attention: local plateaus are not ranges, that can be used in slicing directly.
        The second element is exactly the last character!

        :param _anno_array:
        :param _rm_whitespace:
        :return:
        """
        _plateau_list = list()
        _plateau = list()
        _prev = 0
        _declining = False
        _rising = False
        if _rm_whitespace:
            _anno_array = self._discount_whitespace(_anno_array)
        for i in range(len(_anno_array)):
            if _anno_array[i] > _prev:
                _rising = True
                _declining = False
                _prev = _anno_array[i]
            elif (_anno_array[i] == _prev) and (_prev != 0) and not _declining:
                _plateau.append(i - 1)
                _prev = _anno_array[i]
            elif (_anno_array[i] < _prev) and not _declining:
                _declining = True
                _rising = False
                _plateau.append(i - 1)
                _plateau_list.append(self._correct_plateau(_plateau))
                del _plateau[:]
                _prev = _anno_array[i]
        return _plateau_list

    def get_text(self, no_whitespace: bool = True):
        if no_whitespace:
            return self._get_text_wo_whitespace()
        else:
            return self._comp_obj.get_text()

    def get_anno_distribution(self, trigger: str, no_whitespace: bool = True, sets: List[int] = None) -> array:
        """

        :param trigger:
        :param no_whitespace:
        :param sets:
        :return: numpy.arrray
        """
        _array = None
        if no_whitespace:
            _array = self._discount_whitespace(self._get_centroid_array(trigger.title(), sets))
        else:
            _array = self._get_centroid_array(trigger.title(), sets)
        return _array

    def get_centroid_objects(self, trigger: str, rm_whitespace: bool = True, sets: List[int] = None) \
            -> List['CentroidObject']:
        # TODO: change to generator
        """

        :param trigger:
        :param rm_whitespace:
        :param sets:
        :return: List of all Centroids of trigger type 'trigger'
        """
        _sets = "_".join([str(_set) for _set in sorted(sets)]) if sets is not None else "all"
        _trigger = trigger.title()
        if _trigger in self._comp_obj.get_trigger_set().keys():  # AnnotationTypes.trigger_types():
            _key = _trigger + "-" + _sets
            if self._centroid_objects_dict.get(_key, None) is None:
                for _pl in self._find_local_plateaus(self._get_centroid_array(_trigger, sets),
                                                     _rm_whitespace=rm_whitespace):
                    c_obj = CentroidObject(self, _pl, _trigger, rm_whitespace, sets)
                    self._centroid_objects_dict[_key].append(c_obj)
            return self._centroid_objects_dict[_key]
        else:
            return None



