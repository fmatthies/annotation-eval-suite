import sqlite3
from typing import Union
from collections import namedtuple, defaultdict
from itertools import combinations


class InstanceAgreement:
    def __init__(self, annotators: list, doc_id: str, db_connection: sqlite3.Connection):
        # ToDo: for larger processing: list of documents?
        self.db = db_connection
        self.annotators = sorted(annotators)
        self.all_instance_dict = defaultdict(dict)
        self.doc_id = doc_id

    def _instance_map_dict_key(self, annotators: list, instance_type: Union[str, list], table: str):
        # ToDo: make "table" dependent on instance type?!
        a_type = [instance_type] if isinstance(instance_type, str) else instance_type
        key = "ann:{}_inst:{}_table:{}".format("-".join(sorted(annotators)), "-".join(sorted(a_type)), table)
        if key not in self.all_instance_dict.keys():
            self.all_instance_dict[key]["instances"] = [m for m in self._all_instances(
                annotators[0], annotators[1], instance_type, table)]
        return key

    def _all_instances(self, a_id1: str, a_id2: str, instance_type: Union[str, list], table: str):
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
            """.format(table, a_id1, a_id2, self.doc_id, ",".join("'{0}'".format(t) for t in a_type))
        )
        return map(Instances._make, cursor.fetchall())

    def true_positives(self, instance_type: Union[str, list], annotators: list, table: str):
        """
        Returns the count of true positive annotations across all combinations of two annotators
         from the set of annotators for a given str/list of instance ids
        :param instance_type:
        :param annotators:
        :param table:
        :return:
        """
        tp_all = 0
        for comb in combinations(annotators, 2):
            tp_comb = 0
            key = self._instance_map_dict_key(comb, instance_type, table)
            if not self.all_instance_dict.get(key).get("tp", None):
                for _instance in self.all_instance_dict[key]["instances"]:
                    if _instance.count == 2:
                        tp_comb += 1
                self.all_instance_dict[key]["tp"] = tp_comb
                tp_all += tp_comb
            else:
                tp_all += self.all_instance_dict[key]["tp"]
        return tp_all

    def false_positives(self, instance_type: Union[str, list], annotators: list, table: str):
        fp_all = 0
        for comb in combinations(annotators, 2):
            fp_comb = 0
            key = self._instance_map_dict_key(comb, instance_type, table)
            if not self.all_instance_dict.get(key).get("fp", None):
                for _instance in self.all_instance_dict[key]["instances"]:
                    if _instance.count == 1 and _instance.annotators == comb[1]:
                        fp_comb += 1
                self.all_instance_dict[key]["fp"] = fp_comb
                fp_all += fp_comb
            else:
                fp_all += self.all_instance_dict[key]["fp"]
        return fp_all

    def false_negatives(self, instance_type: Union[str, list], annotators: list, table: str):
        fn_all = 0
        for comb in combinations(annotators, 2):
            fn_comb = 0
            key = self._instance_map_dict_key(comb, instance_type, table)
            if not self.all_instance_dict.get(key).get("fn", None):
                for _instance in self.all_instance_dict[key]["instances"]:
                    if _instance.count == 1 and _instance.annotators == comb[0]:
                        fn_comb += 1
                self.all_instance_dict[key]["fn"] = fn_comb
                fn_all += fn_comb
            else:
                fn_all += self.all_instance_dict[key]["fn"]
        return fn_all

    def agreement_fscore(self, instance_type: Union[str, list], annotators: list, table: str,
                         rounded: Union[int, None] = None):
        tp = self.true_positives(instance_type, annotators, table)
        fn = self.false_negatives(instance_type, annotators, table)
        fp = self.false_positives(instance_type, annotators, table)

        denominator = (2 * tp) + fn + fp
        if len(annotators) == 0 or denominator == 0:
            return 0.0
        res = 2 * tp / denominator / len(annotators)
        return round(res, rounded) if rounded is not None else res


class TokenAgreement:
    def __init__(self, annotators: list, doc_id: str, db_connection: sqlite3.Connection):
        # ToDo: for larger processing: list of documents?
        self.db = db_connection
        self.annotators = sorted(annotators)
        self.doc_id = doc_id
        self.all_token_dict = defaultdict(dict)
        self.same_sentence_token_ids = set()

    def _token_map_dict_key(self, annotators: list, instance_type: Union[str, list], table: str):
        # ToDo: make "table" dependent on instance type?!
        a_type = [instance_type] if isinstance(instance_type, str) else instance_type
        return "ann:{}_inst:{}_table:{}".format("-".join(sorted(annotators)), "-".join(sorted(a_type)), table)

    def _same_sentence_query(self, annotators: list, annotation_types: list, table: str, between: bool):
        return """
        SELECT a.id, b.id, a.begin, b.begin, a.end, b.end, a.text, b.text
        FROM {table} a
        INNER JOIN {table} b
        WHERE (a.type in ({annotation_types}) AND b.type in ({annotation_types}))
          AND (a.annotator = {annotator_a} AND b.annotator = {annotator_b})
          AND (a.document = {document_id} AND b.document = {document_id})
          AND (a.sentence = b.sentence)
          AND {between}(
            ((b.begin BETWEEN a.begin and a.end) AND
            (b.end BETWEEN a.begin and  a.end))
            OR
            ((a.begin BETWEEN b.begin and b.end) AND
            (a.end BETWEEN b.begin and  b.end))
          )
        """.format(annotation_types=",".join("'{0}'".format(t) for t in annotation_types), table=table,
                   document_id=self.doc_id, annotator_a=annotators[0], annotator_b=annotators[1],
                   between="" if between else "NOT")

    def _different_sentence_query(self, annotators: list, annotation_types: list, table: str):
        return """
        SELECT id
        FROM {table}
        WHERE id not in ({ids})
        AND document = {document_id}
        AND (annotator = {annotator_a} OR annotator = {annotator_b})
        AND type in ({annotation_types})
        """.format(annotation_types=",".join("'{0}'".format(t) for t in annotation_types), table=table,
                   document_id=self.doc_id, annotator_a=annotators[0], annotator_b=annotators[1],
                   ids=",".join("'{0}'".format(i) for i in self.same_sentence_token_ids))

    def true_positives(self, instance_type: Union[str, list], annotators: list, table: str):
        a_type = [instance_type] if isinstance(instance_type, str) else instance_type
        annotators = sorted(annotators)
        tp_all = 0
        for comb in combinations(annotators, 2):
            key = self._token_map_dict_key(comb, instance_type, table)
            if key not in self.all_token_dict.keys() or not self.all_token_dict[key].get('tp', None):
                Annotations = namedtuple("Annotations", "a_id, b_id, a_begin, b_begin, a_end, b_end, a_text, b_text")
                cursor = self.db.cursor()
                cursor.execute(self._same_sentence_query(comb, a_type, table, True))
                l_map = list(map(Annotations._make, cursor.fetchall()))
                self.all_token_dict[key]['tp'] = l_map
                for t in l_map:
                    self.same_sentence_token_ids.add(t.a_id)
                    self.same_sentence_token_ids.add(t.b_id)
            tp_all += len(self.all_token_dict[key]['tp'])
        return tp_all

    def false_same_sentence(self, instance_type: Union[str, list], annotators: list, table: str):
        a_type = [instance_type] if isinstance(instance_type, str) else instance_type
        annotators = sorted(annotators)
        fss_all = 0
        for comb in combinations(annotators, 2):
            key = self._token_map_dict_key(comb, instance_type, table)
            if key not in self.all_token_dict.keys() or not self.all_token_dict[key].get('fss', None):
                Annotations = namedtuple("Annotations", "a_id, b_id, a_begin, b_begin, a_end, b_end, a_text, b_text")
                cursor = self.db.cursor()
                cursor.execute(self._same_sentence_query(comb, a_type, table, False))
                l_map = list(map(Annotations._make, cursor.fetchall()))
                self.all_token_dict[key]['fss'] = l_map
                for t in l_map:
                    self.same_sentence_token_ids.add(t.a_id)
                    self.same_sentence_token_ids.add(t.b_id)
            fss_all += len(self.all_token_dict[key]['fss'])
        return fss_all

    def false_others(self, instance_type: Union[str, list], annotators: list, table: str):
        a_type = [instance_type] if isinstance(instance_type, str) else instance_type
        annotators = sorted(annotators)
        fo_all = 0
        self.true_positives(instance_type, annotators, table)
        self.false_same_sentence(instance_type, annotators, table)
        for comb in combinations(annotators, 2):
            key = self._token_map_dict_key(comb, instance_type, table)
            if key not in self.all_token_dict.keys() or not self.all_token_dict[key].get('fo', None):
                Annotations = namedtuple("Annotations", "id")
                cursor = self.db.cursor()
                cursor.execute(self._different_sentence_query(comb, a_type, table))
                l_map = list(map(Annotations._make, cursor.fetchall()))
                self.all_token_dict[key]['fo'] = l_map
            fo_all += len(self.all_token_dict[key]['fo'])
        return fo_all

    def agreement_fscore(self, instance_type: Union[str, list], annotators: list, table: str,
                         rounded: Union[int, None] = None):
        tp = self.true_positives(instance_type, annotators, table)
        fn_fp = (self.false_same_sentence(instance_type, annotators, table) +
                 self.false_others(instance_type, annotators, table))

        denominator = (2 * tp) + fn_fp
        if len(annotators) == 0 or denominator == 0:
            return 0.0
        res = 2 * tp / denominator / len(annotators)
        return round(res, rounded) if rounded is not None else res


if __name__ == "__main__":
    db_conn = sqlite3.connect("../test/test-resources/test_project.db", check_same_thread=False)

    # type_group = ["2", "0", "3", "5"]
    # table_type = "medication_entities"
    type_group = ["1", "4"]
    table_type = "medication_attributes"

    ia = InstanceAgreement(annotators=["0", "1", "2"], doc_id="2", db_connection=db_conn)

    print(ia.agreement_fscore(type_group, ["0", "1"], table_type))
    print(ia.agreement_fscore(type_group, ["0", "2"], table_type))
    print(ia.agreement_fscore(type_group, ["2", "1"], table_type))
    print(ia.agreement_fscore(type_group, ["0", "2", "1"], table_type))

    print()
    ta = TokenAgreement(annotators=["0", "1", "2"], doc_id="2", db_connection=db_conn)

    print(ta.agreement_fscore(type_group, ["0", "1"], table_type))
    print(ta.agreement_fscore(type_group, ["0", "2"], table_type))
    print(ta.agreement_fscore(type_group, ["1", "2"], table_type))
    print(ta.agreement_fscore(type_group, ["1", "2", "0"], table_type))
