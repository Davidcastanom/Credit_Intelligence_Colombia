import os
import re
import logging

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    pass


class ConnectionError(DatabaseError):
    pass


class Row:
    """Fila con acceso por posición (row[0]) y por nombre (row['col'])."""
    def __init__(self, columns, values):
        self._columns = tuple(columns)
        self._values = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return self._values[key]
        return self._values[self._columns.index(key)]

    def __contains__(self, key):
        if isinstance(key, str):
            return key in self._columns
        return key in self._values

    def __iter__(self):
        return iter(self._columns)

    def __len__(self):
        return len(self._columns)

    def keys(self):
        return self._columns

    def values(self):
        return self._values

    def items(self):
        return zip(self._columns, self._values)

    def __repr__(self):
        return f"Row({dict(zip(self._columns, self._values))})"


def _translate_sql(sql):
    sql = sql.replace("?", "%s")
    if re.match(r"\s*INSERT\s+OR\s+IGNORE\s+INTO", sql, re.IGNORECASE):
        sql = re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", sql, flags=re.IGNORECASE)
        if "ON CONFLICT" not in sql.upper():
            sql += " ON CONFLICT DO NOTHING"
    sql = re.sub(r"\bexcluded\.", "EXCLUDED.", sql)
    sql = re.sub(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", "SERIAL PRIMARY KEY", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bDEFAULT\s*\(\s*date\s*\(\s*'now'\s*\)\s*\)", "DEFAULT CURRENT_DATE", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bDEFAULT\s*\(\s*datetime\s*\(\s*'now'\s*\)\s*\)", "DEFAULT NOW()", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bsqlite_master\b", "information_schema.tables", sql, flags=re.IGNORECASE)
    return sql


class CursorWrapper:
    def __init__(self, cursor, is_pg):
        self._cursor = cursor
        self._is_pg = is_pg

    def execute(self, sql, params=None):
        if self._is_pg:
            sql = _translate_sql(sql)
        if params is not None:
            self._cursor.execute(sql, params)
        else:
            self._cursor.execute(sql)
        return self

    def executemany(self, sql, seq_of_params):
        if self._is_pg:
            sql = _translate_sql(sql)
        self._cursor.executemany(sql, seq_of_params)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._is_pg:
            return Row([d[0] for d in self._cursor.description], row)
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if self._is_pg:
            cols = [d[0] for d in self._cursor.description]
            return [Row(cols, r) for r in rows]
        return rows

    @property
    def lastrowid(self):
        if self._is_pg:
            raw = self._cursor.connection.cursor()
            raw.execute("SELECT LASTVAL()")
            val = raw.fetchone()[0]
            raw.close()
            return val
        return self._cursor.lastrowid

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class Conexion:
    def __init__(self):
        self._conn = None
        self._is_pg = False
        self._conectar()

    def _conectar(self):
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            self._conectar_pg(database_url)
        else:
            self._conectar_sqlite()

    def _conectar_sqlite(self):
        import sqlite3
        try:
            self._conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "tasas.db"))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._is_pg = False
        except sqlite3.Error as e:
            raise ConnectionError(f"No se pudo conectar a SQLite: {e}")

    def _conectar_pg(self, dsn):
        try:
            import psycopg2
            self._conn = psycopg2.connect(dsn)
            self._conn.autocommit = False
            self._is_pg = True
        except ImportError:
            raise ConnectionError("psycopg2 no está instalado. Ejecute: pip install psycopg2-binary")
        except Exception as e:
            raise ConnectionError(f"No se pudo conectar a PostgreSQL: {e}")

    def cursor(self):
        raw = self._conn.cursor()
        return CursorWrapper(raw, self._is_pg)

    def commit(self):
        try:
            self._conn.commit()
        except Exception as e:
            raise DatabaseError(f"Error al hacer commit: {e}")

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception as e:
            raise DatabaseError(f"Error al hacer rollback: {e}")

    def close(self):
        try:
            self._conn.close()
        except Exception as e:
            logger.warning(f"Error al cerrar conexión: {e}")
