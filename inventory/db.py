"""Thin DB wrapper so the same code runs on MySQL or SQLite."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from . import config

ROOT = Path(__file__).resolve().parent.parent


class Database:
    def __init__(self, backend=None, sqlite_path=None):
        self.backend = backend or config.DB_BACKEND
        if self.backend == "mysql":
            import mysql.connector
            self.conn = mysql.connector.connect(**config.MYSQL)
        else:
            self.conn = sqlite3.connect(sqlite_path or config.SQLITE_PATH)
            self.conn.row_factory = sqlite3.Row
            self.conn.isolation_level = None          # manual transaction control
            self.conn.execute("PRAGMA foreign_keys = ON")
        self._in_tx = False

    def _sql(self, sql):
        return sql.replace("?", "%s") if self.backend == "mysql" else sql

    def _cursor(self):
        return self.conn.cursor(dictionary=True) if self.backend == "mysql" else self.conn.cursor()

    def execute(self, sql, params=()):
        cur = self._cursor()
        cur.execute(self._sql(sql), tuple(params))
        if self.backend == "mysql" and not self._in_tx:
            self.conn.commit()
        return cur.lastrowid

    def query(self, sql, params=()):
        cur = self._cursor()
        cur.execute(self._sql(sql), tuple(params))
        return [dict(r) for r in cur.fetchall()]

    @contextmanager
    def transaction(self):
        """Atomic block: everything commits together or rolls back together."""
        self._in_tx = True
        try:
            if self.backend == "mysql":
                self.conn.start_transaction()
            else:
                self.conn.execute("BEGIN IMMEDIATE")
            yield
            self.conn.commit() if self.backend == "mysql" else self.conn.execute("COMMIT")
        except Exception:
            self.conn.rollback() if self.backend == "mysql" else self.conn.execute("ROLLBACK")
            raise
        finally:
            self._in_tx = False

    def init_schema(self):
        f = ROOT / ("schema_mysql.sql" if self.backend == "mysql" else "schema_sqlite.sql")
        for stmt in f.read_text().split(";"):
            if stmt.strip():
                cur = self._cursor()
                cur.execute(stmt)
        if self.backend == "mysql":
            self.conn.commit()

    def close(self):
        self.conn.close()
