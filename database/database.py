import os
import sys
import logging
import sqlite3
import pathlib
import time
from collections import namedtuple, defaultdict
from functools import partial
from sqlite3 import Error
from typing import Union, Tuple, List
from collections.abc import Iterable

import tqdm
from cassis import Cas, load_typesystem, load_cas_from_xmi

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import uima
from app_constants import database_info, db_construction, layers, DefaultTableNames
from app_constants.base_config import DatabaseCategories
from bratsubset.annotation import Annotations
from bratsubset.projectconfig import ProjectConfiguration
from config.webanno_config_medication import layers as user_layers

logging.basicConfig(level=logging.WARNING)


class DBUtils:
    def __init__(self, in_memory: bool = True, db_file: str = 'sqlite.db') -> None:
        self._in_memory = in_memory
        self._db_file = os.path.abspath(db_file)
        self._connection = None

    def __del__(self) -> None:
        self.close_connection()

    @property
    def in_memory(self) -> bool:
        return self._in_memory

    @property
    def db_file(self) -> str:
        return self._db_file

    @property
    def connection(self) -> sqlite3.Connection:
        if not self._connection:
            logging.warning("There is no active connection {0}!".format(
                "in memory" if self.in_memory else "for the file {0}".format(self.db_file)))
        return self._connection

    def create_connection(self) -> Union[sqlite3.Connection, None]:
        try:
            self._connection = sqlite3.connect(':memory:' if self.in_memory else self.db_file)
            return self.connection
        except Error as e:
            logging.error(e)
            return None

    def close_connection(self) -> None:
        if self._connection:
            self._connection.commit()
            self._connection.close()
            self._connection = None


class DataSaver:
    def __init__(self, db: DBUtils, db_structure: dict, reset_db: bool = False) -> None:
        """

        :param db:
        :param db_structure: A dictionary of table creation instructions:
         `dict(table_name: dict("stm": str, "idx": list(str)))` where the "stm" string is what follows after
         `CREATE TABLE table_name` and the "idx" list is a list of indices to be declared (must conform with the
         column names in "stm"). Key names "stm" & "idx" are mandatory and can't be chosen freely
         e.g.: db_structure = {"table1": {"stm": "(id txt PRIMARY KEY, type txt NOT NULL);", "idx": ["type"]}}
        :param reset_db:
        """
        logging.info("Init database {0}".format(
            "in memory" if db.in_memory else "for the file {0}".format(db.db_file)))
        self._db = db
        self._db_struc = self._validate_structure_dict(db_structure)
        if not db.connection:
            logging.error("db not instantiated")  # ToDo: better log
            sys.exit(-1)
        if reset_db or db.in_memory:
            self._init_database()

    @property
    def db_connection(self):
        return self._db.connection

    @property
    def db_cursor(self):
        return self.db_connection.cursor()

    @staticmethod
    def _validate_structure_dict(db_structure) -> dict:
        # ToDo implement specific error not TypeError
        for key, value in db_structure.items():
            if not isinstance(key, str):
                logging.error("")
                raise TypeError
            if not isinstance(value, dict):
                logging.error("")
                raise TypeError
            if "stm" not in value.keys() or "idx" not in value.keys():
                logging.error("")
                raise TypeError
            if not isinstance(value.get("stm"), str):
                logging.error("")
            if not isinstance(value.get("idx"), list):
                logging.error("")
                raise TypeError
            if not all(isinstance(e, str) for e in value.get("idx")):
                logging.error("")
                raise TypeError
        return db_structure

    def _init_database(self) -> None:
        logging.info("Reset database {}".format(
            "in memory" if self._db.in_memory else "for the file '{0}'".format(self._db.db_file)))
        for table_name, table_dict in self._db_struc.items():
            self._drop_table_exec(table_name)
            self._create_table_exec(table_name, table_dict.get("stm"))
            for idx in table_dict.get("idx"):
                idx_name = "idx_{0}_{1}".format(table_name.split("_")[-1], idx)
                self._drop_index_exec(idx_name)
                self._create_index_exec(idx_name, table_name, idx)

    def _drop_table_exec(self, table_name: str) -> None:
        logging.info("Dropping old table '{0}'".format(table_name))
        self.db_cursor.execute(
            "DROP TABLE IF EXISTS {0}".format(table_name.lower())
        )

    def _create_table_exec(self, table_name: str, stm: str) -> None:
        logging.info("Creating table '{0}'".format(table_name))
        self.db_cursor.execute(
            "CREATE TABLE IF NOT EXISTS {0} {1}".format(table_name.lower(), stm)
        )

    def _drop_index_exec(self, idx_name: str) -> None:
        logging.info("Dropping old index '{0}'".format(idx_name))
        self.db_cursor.execute(
            "DROP INDEX IF EXISTS {0}".format(idx_name.lower())
        )

    def _create_index_exec(self, idx_name: str, table_name: str, col_name: str) -> None:
        logging.info("Creating index '{0}'".format(idx_name))
        self.db_cursor.execute(
            "CREATE INDEX {0} ON {1}({2})".format(idx_name.lower(), table_name.lower(), col_name)
        )

    def commit(self) -> None:
        """
        Calls commit on the sqlite3 connection. This will also be done when the connection is closed,
        but if you want to save your database changes midway through call this.

        :return:
        """
        self.db_connection.commit()

    def store_into_table(self, table_name: str, columns: Union[list, set] = None, ignore_duplicates: bool = False,
                         **kwargs) -> None:
        """
        Either put a single row into the table `table_name` where you specify the column and values as
        keyword argument pairs: `store_into_table(table_name, col1=val1, col2=val2, ...)`.
        Or you can store multiple rows, specifying the param `columns` and providing an `Iterable`:
        `store_into_table(table_name, columns=(col1, col2), iter_arg=[(val1-1, val2-1), (val1-2, val2-2)])`

        :param ignore_duplicates:
        :param table_name: name of the reference table
        :param columns:
        :param kwargs:
        :return:
        """
        insert_stm = " OR IGNORE" if ignore_duplicates else ""
        if len(kwargs) == 1 and isinstance(list(kwargs.values())[0], Iterable):
            iterable = list(kwargs.values())[0]
            logging.info("Populating table '{0}' with values from iterable".format(table_name))
            self.db_cursor.executemany(
                "INSERT{3} INTO {0}({1}) VALUES ({2})".format(
                    table_name, ",".join(columns), ",".join(["?"] * len(columns)), insert_stm),
                iterable
            )
        else:
            cols, row = kwargs.keys(), [str(v) if isinstance(v, int) else v for v in kwargs.values()]
            # ToDo: better log
            logging.info("Populating columns '{0}' of table '{1}'".format(", ".join(cols), table_name))
            self.db_cursor.execute(
                "INSERT{3} INTO {0} ({1}) VALUES ({2})".format(
                    table_name, ",".join(cols), ",".join(["?"] * len(cols)), insert_stm),
                row
            )

    def update_row_of_table(self, table_name: str, where_cols: List[Tuple[str, str]], **kwargs):
        cols, row = list(kwargs.keys()), [str(v) if isinstance(v, int) else v for v in kwargs.values()]
        self.db_cursor.execute(
            """
            UPDATE {0}
            SET {1}
            WHERE {2}
            """.format(
                table_name, ",\n".join(["{} = ?".format(cols[i]) for i in range(len(cols))]),
                "".join(["{} = '{}'".format(t[0], t[1]) for t in where_cols])
            ),
            row
        )


def get_anno_type_id(anno_types: list, anno_type: str, layer_id: str, ds: DataSaver):
    store_into_db = False
    anno_type = anno_type.lower()  # ToDo: to lower or not?
    if anno_type not in anno_types:
        anno_types.append(anno_type)
        store_into_db = True
    anno_type_id = str(anno_types.index(anno_type))
    if store_into_db:
        ds.store_into_table(DefaultTableNames.annotation_types, id=anno_type_id, type=anno_type, layer=layer_id)
    return anno_type_id


def get_layer_id(l_types: list, layer: str, ds: DataSaver):
    store_into_db = False
    layer = layer.lower()  # ToDo: to lower or not?
    if layer not in l_types:
        l_types.append(layer)
        store_into_db = True
    layer_id = str(l_types.index(layer))
    if store_into_db:
        ds.store_into_table(DefaultTableNames.layers, id=layer_id, layer=layer)
    return layer_id


def store_xmi_in_db(cas: Cas, annotator: str, annotator_id: str, document: str, document_id: str,
                    anno_types: list, l_types: list, s_list: set, ds: DataSaver, layer_info: dict):
    # ToDo: right now ds.store_into_table IGNOREs duplicate sentence ids, but it would be better if I catch the sen-
    # ToDo: tences in each following cas (after the first one) and don't try to put them into the db in the first place
    # ToDo: (as well as annotators and documents)
    # ToDo: --> only true for annotators and documents; do I need to change this?
    ds.store_into_table(DefaultTableNames.annotators, ignore_duplicates=True, id=annotator_id, annotator=annotator)
    ds.store_into_table(DefaultTableNames.documents, ignore_duplicates=True, id=document_id, document=document)
    for sentence in cas.select(layers.get(DefaultTableNames.sentences)):
        has_annotation = False
        sentence_id = "{}-{}".format(document_id, str(sentence.xmiID))
        for layer, layer_obj in layer_info.get("annotations").items():
            for entity in cas.select_covered(layer, sentence):
                uima
        # layer = const.LayerTypes.MEDICATION_ENTITY
        # for entity in cas.select_covered(const.LayerTypes.MEDICATION_ENTITY, sentence):
        #     ent = uima.LAYER_DICT.get(const.LayerTypes.MEDICATION_ENTITY)(entity, cas)
        #     anno_type = ent.get_fs_property(const.LayerProperties.MEDICATION_ENTITY_TYPE)
        #     entity_id = "{}-{}".format(annotator_id, str(ent.xmi_id))
        #     ds.store_into_table(const.LAYER_TNAME_DICT.get(const.LayerTypes.MEDICATION_ENTITY),
        #                         id=entity_id, annotator=annotator_id,
        #                         begin=(int(ent.begin) - int(sentence.begin)), end=(int(ent.end) - int(sentence.begin)),
        #                         text=ent.covered_text, sentence=sentence_id, document=document_id,
        #                         type=get_anno_type_id(anno_types, anno_type, get_layer_id(l_types, layer, ds), ds),
        #                         list=1 if ent.get_fs_property(const.LayerProperties.MEDICATION_ENTITY_IS_LIST) else 0,
        #                         recommendation=1 if ent.get_fs_property(
        #                             const.LayerProperties.MEDICATION_ENTITY_IS_RECOMMENDATION) else 0)
        #     has_annotation = True
        # layer = const.LayerTypes.MEDICATION_ATTRIBUTE
        # for attribute in cas.select_covered(const.LayerTypes.MEDICATION_ATTRIBUTE, sentence):
        #     attr = uima.LAYER_DICT.get(const.LayerTypes.MEDICATION_ATTRIBUTE)(attribute, cas)
        #     anno_type = attr.get_fs_property(const.LayerProperties.MEDICATION_ATTRIBUTE_TYPE)
        #     attribute_id = "{}-{}".format(annotator_id, str(attr.xmi_id))
        #     ds.store_into_table(const.LAYER_TNAME_DICT.get(const.LayerTypes.MEDICATION_ATTRIBUTE),
        #                         id=attribute_id, annotator=annotator_id,
        #                         begin=(int(attr.begin) - int(sentence.begin)),
        #                         end=(int(attr.end) - int(sentence.begin)),
        #                         text=attr.covered_text, sentence=sentence_id, document=document_id,
        #                         type=get_anno_type_id(anno_types, anno_type, get_layer_id(l_types, layer, ds), ds))
        #     has_annotation = True
        #     for rel_ent in attr.get_fs_property(const.LayerProperties.MEDICATION_ATTRIBUTE_RELATION):
        #         rel_id = rel_ent[0]
        #         rel_target = rel_ent[1]
        #         relation_id = "{}-{}".format(annotator_id, str(rel_id))
        #         ds.store_into_table(const.LAYER_TNAME_DICT.get(const.LayerTypes.RELATION),
        #                             id=relation_id, annotator=annotator_id,
        #                             entity="{}-{}".format(annotator_id, str(rel_target.xmi_id)),
        #                             attribute=attribute_id)
        for layer_name, layer_fqn in user_layers.items():
            for anno_fs in cas.select_covered(layer_fqn, sentence):
                annotation = uima.WebAnnoLayer(layer_fqn, )
        if sentence_id not in s_list:
            s_list.add(sentence_id)
            ds.store_into_table(const.LAYER_TNAME_DICT.get(const.LayerTypes.SENTENCE),
                                id=sentence_id, document=document_id, begin=sentence.begin, end=sentence.end,
                                text=sentence.get_covered_text(), has_annotation=1 if has_annotation else 0)
        elif sentence_id in s_list and has_annotation:
            ds.update_row_of_table(const.LAYER_TNAME_DICT.get(const.LayerTypes.SENTENCE),
                                   [("id", sentence_id)],
                                   has_annotation=1
                                   )
    return True


def store_brat_in_db(ds: DataSaver, annotators: dict, documents: dict, config: ProjectConfiguration,
                     type_reference: dict, allow_disp_sent: bool = False, drop_annotations: list = []):
    brat2table = {}
    type2table = {}
    for cat, _dict in database_info.items():
        cat = cat.lower()
        if cat in [DatabaseCategories.entities.lower(), DatabaseCategories.relations.lower()]:
            brat2table.update({y['type'].lower(): x.lower() for x, y in _dict.items()})
    for x, y in {'entities': [a for a in config.get_entity_types() if a not in drop_annotations],
                 'events': [a for a in config.get_event_types() if a not in drop_annotations],
                 'relations': [a for a in config.get_relation_types() if a not in drop_annotations]}.items():
        type2table.update({z.lower(): brat2table[x] for z in y})
    annotators_stored = False
    for doc_id, doc_name in documents.items():
        ds.store_into_table(DefaultTableNames.documents, ignore_duplicates=True, id=doc_id, document=doc_name)
        txt = []
        ann_objects = dict()
        for a_id, annotator in annotators.items():
            if not annotators_stored:
                ds.store_into_table(DefaultTableNames.annotators, ignore_duplicates=True, id=a_id, annotator=annotator)
            txt.append(
                (a_id, pathlib.Path(config.directory, annotator, f"{doc_name}.txt").read_text(encoding='utf-8'))
            )
            ann_objects[a_id] = Annotations(pathlib.Path(config.directory, annotator, doc_name).as_posix(), True)
        annotators_stored = True
        sentences = None
        for t_aid, _txt in txt:
            if not allow_disp_sent and sentences is None:
                sentences = [s for s in _get_sentences(txt=_txt)]
            elif allow_disp_sent:
                sentences = _get_sentences(txt=_txt)
            for sentence in sentences:
                has_annotations = False
                for t in ann_objects.get(t_aid).get_textbounds():
                    if t.type.lower() in drop_annotations:
                        continue
                    begin = t.get_start()
                    end = t.get_end()
                    if begin > sentence.end or end < sentence.begin:
                        continue
                    has_annotations = True
                    ds.store_into_table(type2table[t.type.lower()], ignore_duplicates=True,
                                        id=f"{doc_id}-{t_aid}-{t.id}", annotator=str(t_aid),
                                        begin=str(begin - sentence.begin), end=str(end - sentence.begin),
                                        text=_txt[begin:end], document=str(doc_id),
                                        sentence=f"{doc_id}-{sentence.id}{'-' + str(t_aid) if allow_disp_sent else ''}",
                                        type=type_reference[t.type.lower()]["type-id"])
                ds.store_into_table(DefaultTableNames.sentences, ignore_duplicates=True,
                                    id=f"{doc_id}-{sentence.id}{'-' + str(t_aid) if allow_disp_sent else ''}",
                                    begin=sentence.begin, end=sentence.end, document=str(doc_id),
                                    text=_txt[sentence.begin:sentence.end], has_annotation=1 if has_annotations else 0)


def store_xmi():
    project_file = os.path.abspath(
        "../test/uima-test-resources/test_project.zip" if len(sys.argv) <= 1 else sys.argv[1])
    in_memory = False if len(sys.argv) <= 2 else sys.argv[2].lower() in ["true", "t", "yes", "y"]
    db_file = os.path.abspath("../test/uima-test-resources/test_project.db" if len(sys.argv) <= 3 else sys.argv[3])
    reset_db = not (False if len(sys.argv) <= 4 else sys.argv[4].lower() in ["false", "f", "no", "n"])
    ts_string_key = "TypeSystem.xml"

    print("""
        Starting with these options:
        zip file:       {}
        db file:        {}
        db in memory:   {}
        reset db:       {}
        """.format(project_file, db_file, in_memory, reset_db))

    xmi_dict = uima.get_project_files(project_file, ts_string_key)
    ts_string = xmi_dict.get(ts_string_key).read().decode('utf-8')
    typesystem = load_typesystem(ts_string)
    l_info = uima.get_layer_information_from_type_system(ts_string, user_layers)

    db_util = DBUtils(in_memory=in_memory, db_file=db_file)
    db_util.create_connection()
    data_saver = DataSaver(db_util, db_construction, reset_db=reset_db)
    pbar = tqdm.tqdm(total=(len(xmi_dict.get("documents")) * len(xmi_dict.get("annotators"))))

    annotation_types = list()
    layer_types = list()
    sentence_list = set()
    for doc, d_id in xmi_dict.get("documents").items():
        for anno, a_id in xmi_dict.get("annotators").items():
            updated = False
            xmi = xmi_dict.get(doc).get(anno, None)
            if xmi:
                anno_cas = load_cas_from_xmi(xmi, typesystem=typesystem)
                updated = store_xmi_in_db(anno_cas, anno, a_id, doc, d_id,
                                          annotation_types, layer_types, sentence_list, data_saver, l_info)
            if updated:
                pbar.update(1)
    db_util.close_connection()


### from kldtz/bratiaa ###
AnnFile = namedtuple('AnnFile', ['annotator_id', 'ann_path'])


class Document:
    __slots__ = ['ann_files', 'txt_path', 'doc_id']

    def __init__(self, txt_path, doc_id=None):
        self.txt_path = txt_path
        if doc_id:
            self.doc_id = doc_id
        else:
            self.doc_id = txt_path
        self.ann_files = []


def input_generator(root):
    """
    Yields Document objects. Assumes that each first-level subdirectory of the
    annotation project corresponds to one annotator.
    """
    root = pathlib.Path(root)
    annotators = [subdir.parts[-1] for subdir in root.glob('*/') if subdir.is_dir()]
    assert len(annotators) > 1, 'At least two annotators are necessary to compute agreement!'
    for rel_path in sorted(collect_redundant_files(root, annotators)):
        document = Document((root / annotators[0] / rel_path).as_posix()[:-3] + 'txt', doc_id=rel_path)
        for annotator in annotators:
            ann_path = root / annotator / rel_path
            document.ann_files.append(AnnFile(annotator, ann_path))
        yield document


def collect_redundant_files(root, annotators):
    intersection = None
    for annotator in annotators:
        subdir_path = root / annotator
        relative_paths = {path.relative_to(subdir_path).as_posix() for path in subdir_path.glob('**/*.ann')}
        if not intersection:
            intersection = relative_paths
        else:
            intersection = intersection.intersection(relative_paths)
    return intersection


def _collect_annotators_and_documents(input_gen):
    annotators, documents = set(), []
    for document in input_gen():
        for ann_file in document.ann_files:
            annotators.add(ann_file.annotator_id)
        documents.append(document.doc_id)
    return list(annotators), documents


#######################


def _get_sentences(txt: str, split_on: str = '\n'):
    Sentence = namedtuple('Sentence', ['id', 'begin', 'end'])
    sentences = txt.split(split_on)
    index = txt.index
    _len = len
    running_offset = 0
    for sid, sentence in enumerate(sentences):
        if len(sentence.split()) == 0:
            continue
        sentence_offset = index(sentence, running_offset)
        sentence_len = _len(sentence)
        running_offset = sentence_offset + sentence_len
        yield Sentence(id=sid, begin=sentence_offset, end=running_offset)


def store_brat():
    project_root = pathlib.Path(
        "../test/brat-test-resources/test-resources" if len(sys.argv) <= 1 else sys.argv[1]).resolve()
    in_memory = False if len(sys.argv) <= 2 else sys.argv[2].lower() in ["true", "t", "yes", "y"]
    db_file = os.path.abspath("../test/brat-test-resources/test_project.db" if len(sys.argv) <= 3 else sys.argv[3])
    reset_db = not (False if len(sys.argv) <= 4 else sys.argv[4].lower() in ["false", "f", "no", "n"])
    allow_disp_sent = False if len(sys.argv) <= 5 else sys.argv[5].lower() in ["true", "t", "yes", "y"]
    drop_annotations = [x.lower() for x in sys.argv[6].split(",")] if len(sys.argv) >= 7 else []

    config = ProjectConfiguration(str(project_root))
    input_gen = partial(input_generator, project_root)
    annotators, documents = _collect_annotators_and_documents(input_gen)

    print("""
        Starting with these options:
        project root:           {}
        db file:                {}
        db in memory:           {}
        reset db:               {}
        allow disp. sentences:  {}
        drop annotations:       {}
        """.format(str(project_root), db_file, in_memory, reset_db, allow_disp_sent, drop_annotations))

    time.sleep(2)

    db_util = DBUtils(in_memory=in_memory, db_file=db_file)
    db_util.create_connection()
    data_saver = DataSaver(db_util, db_construction, reset_db=reset_db)

    # populate db
    type_reference = defaultdict(dict)
    type_id = 0
    for layer_id, layer in enumerate([("entities", config.get_entity_types()), ("events", config.get_event_types())]):
        data_saver.store_into_table(DefaultTableNames.layers, ignore_duplicates=True,
                                    id=layer_id, layer=layer[0].lower())
        for typee in layer[1]:
            typee = typee.lower()
            if typee in drop_annotations:
                continue
            type_reference[typee]["layer-id"] = layer_id
            type_reference[typee]["type-id"] = type_id
            data_saver.store_into_table(DefaultTableNames.annotation_types, ignore_duplicates=True,
                                        id=type_id, type=typee, layer=layer_id)
            type_id += 1
    store_brat_in_db(ds=data_saver, annotators={_id: _name.lower() for _id, _name in enumerate(annotators)},
                     documents={_id: "".join(_name.split(".")[:-1]) for _id, _name in enumerate(documents)},
                     config=config, type_reference=type_reference, allow_disp_sent=allow_disp_sent,
                     drop_annotations=drop_annotations)


if __name__ == '__main__':
    # store_xmi()
    store_brat()
    # pass
