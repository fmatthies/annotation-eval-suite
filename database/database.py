import os
import sys
import logging
import sqlite3
from sqlite3 import Error
from typing import Union
from collections.abc import Iterable

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

    def store_into_table(self, table_name: str, columns: Union[list, set] = None, **kwargs) -> None:
        """
        Either put a single row into the table `table_name` where you specify the column and values as
        keyword argument pairs: `store_into_table(table_name, col1=val1, col2=val2, ...)`.
        Or you can store multiple rows, specifying the param `columns` and providing an `Iterable`:
        `store_into_table(table_name, columns=(col1, col2), iter_arg=[(val1-1, val2-1), (val1-2, val2-2)])`

        :param table_name: name of the reference table
        :param columns:
        :param kwargs:
        :return:
        """
        if len(kwargs) == 1 and isinstance(list(kwargs.values())[0], Iterable):
            iterable = list(kwargs.values())[0]
            logging.info("Populating table '{0}' with values from iterable".format(table_name))
            self.db_cursor.executemany(
                "INSERT OR IGNORE INTO {0}({1}) VALUES ({2})".format(
                    table_name, ",".join(columns), ",".join(["?"]*len(columns))),
                iterable
            )
        else:
            cols, row = kwargs.keys(), [str(v) if isinstance(v, int) else v for v in kwargs.values()]
            # ToDo: better log
            logging.info("Populating columns '{0}' of table '{1}'".format(", ".join(cols), table_name))
            self.db_cursor.execute(
                "INSERT OR IGNORE INTO {0} ({1}) VALUES ({2})".format(
                    table_name, ",".join(cols), ",".join(["?"]*len(cols))
                ),
                row
            )
