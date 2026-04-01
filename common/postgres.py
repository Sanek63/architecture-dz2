from psycopg import connect
from psycopg.rows import dict_row


def create_connection(db_url: str):
    return connect(db_url, autocommit=True)


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
