import time

from psycopg import connect
from psycopg.rows import dict_row


def create_connection(db_url: str):
    return connect(db_url, autocommit=True)


def wait_for_connection(db_url: str, retries: int = 30, delay: float = 2.0):
    last_error = None
    for _ in range(retries):
        try:
            return create_connection(db_url)
        except Exception as error:
            last_error = error
            time.sleep(delay)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Failed to connect to database")


def query_one(conn, query: str, params: tuple = ()):
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def query_all(conn, query: str, params: tuple = ()):
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def execute(conn, query: str, params: tuple = ()):
    with conn.cursor() as cursor:
        cursor.execute(query, params)
