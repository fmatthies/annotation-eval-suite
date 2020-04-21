import sqlite3
from typing import Union
from collections import namedtuple, defaultdict
from itertools import combinations


class InstanceAgreement:
    def __init__(self, annotators: list, db_connection: sqlite3.Connection):
        self.db = db_connection
        self.annotators = sorted(annotators)
        self.all_instance_map = {}

    def _instance_map_dict_key(self, annotators: list, instance_type: Union[str, list], table: str, doc_id: str):
        # ToDo: document id into the key?
        a_type = [instance_type] if isinstance(instance_type, str) else instance_type
        key = "ann:{}_inst:{}".format("-".join(sorted(annotators)), "-".join(sorted(a_type)))
        if key not in self.all_instance_map.keys():
            self.all_instance_map[key] = [m for m in
                                          self.all_instances(annotators[0], annotators[1], instance_type, table, doc_id)]
        return key

    def all_instances(self, a_id1: str, a_id2: str, instance_type: Union[str, list], table: str, doc_id: str):
        Instances = namedtuple("Instances", "annotators, instance_txt, count")
        a_type = [instance_type] if isinstance(instance_type, str) else instance_type
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT group_concat(annotator, "?"), group_concat(text, "?"), count(annotator)
            FROM {0}
            WHERE type in ({4})
             AND (annotator = '{1}' OR annotator = '{2}')
             AND document = '{3}'
            GROUP BY begin, end, sentence
            """.format(table, a_id1, a_id2, doc_id, ",".join("'{0}'".format(t) for t in a_type))
        )
        return map(Instances._make, cursor.fetchall())

    def true_positives(self, instance_type: Union[str, list], table: str, doc_id: str):
        tp = 0
        for comb in combinations(self.annotators, 2):
            key = self._instance_map_dict_key(comb, instance_type, table, doc_id)
            for _instance in self.all_instance_map[key]:
                if _instance.count == 2:
                    tp += 1
        return tp

    def false_positives(self, instance_type: Union[str, list], table: str, doc_id: str):
        fp = 0
        for comb in combinations(self.annotators, 2):
            key = self._instance_map_dict_key(comb, instance_type, table, doc_id)
            for _instance in self.all_instance_map[key]:
                if _instance.count == 1 and _instance.annotators == comb[1]:
                    fp += 1
        return fp

    def false_negatives(self, instance_type: Union[str, list], table: str, doc_id: str):
        fn = 0
        for comb in combinations(self.annotators, 2):
            key = self._instance_map_dict_key(comb, instance_type, table, doc_id)
            for _instance in self.all_instance_map[key]:
                if _instance.count == 1 and _instance.annotators == comb[0]:
                    fn += 1
        return fn

    def agreement_fscore(self, instance_type: Union[str, list], table: str, doc_id: str, rounded: int = 3):
        tp = self.true_positives(instance_type, table, doc_id)
        fn = self.false_negatives(instance_type, table, doc_id)
        fp = self.false_positives(instance_type, table, doc_id)

        return round(2*tp/(2*tp + fn + fp)/len(self.annotators), rounded)


if __name__ == "__main__":
    db_conn = sqlite3.connect("../test/test-resources/test_project.db", check_same_thread=False)
    type_group = ["2", "0", "3", "5"]

    ia = InstanceAgreement(annotators=["0", "1"], db_connection=db_conn)

    print(ia.agreement_fscore(type_group, "medication_entities", "2"))
