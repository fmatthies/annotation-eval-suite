# -*- coding: utf-8 -*-

import colorama

#TODO replace all occurences of specific trigger strings with global variables which are defined in here!


class AnnotationTypes(object):

    @staticmethod
    def entity_types():
        """  """
        return {'Anaphora', 'Medication', 'Sentence', 'Token'}

    @staticmethod
    def event_types():
        """  """
        return {'Dose', 'Modus', 'Reason', 'Frequency', 'Duration'}

    @staticmethod
    def trigger_types():
        """  """
        return AnnotationTypes.entity_types().union(AnnotationTypes.event_types())

    @staticmethod
    def relation_types():
        """ all relation annotations """
        return {'Equiv', 'Coreference'}

    @staticmethod
    def modification_types():
        """  """
        return set()

    @staticmethod
    def attribute_types():
        """  """
        return {'List_Source', 'Advice'}

    @staticmethod
    def mod_types():
        """ all annotation that modify other annotations"""
        return AnnotationTypes.modification_types().union(AnnotationTypes.attribute_types())

    @staticmethod
    def all_annotations():
        """ all annotations"""
        return (AnnotationTypes.trigger_types().union(AnnotationTypes.relation_types()))\
            .union(AnnotationTypes.mod_types())


class Colors:

    @staticmethod
    def color_map():
        return {
            'Anaphora': colorama.Fore.LIGHTGREEN_EX,
            'Medication': colorama.Fore.RED,
            'Dose': colorama.Fore.LIGHTCYAN_EX,
            'Modus': colorama.Fore.GREEN,
            'Reason': colorama.Fore.LIGHTMAGENTA_EX,
            'Frequency': colorama.Fore.YELLOW,
            'Duration': colorama.Fore.BLACK
        }
