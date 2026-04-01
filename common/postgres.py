import time

from psycopg import connect
from psycopg.rows import dict_row


def create_connection(db_url: str):
    return connect(db_url, autocommit=True)


def wait_for_connection(db_url: str, retries: int = 30, delay: float = 2.0):
    redacted_url = db_url
    if "@" in db_url and "://" in db_url:
        scheme, rest = db_url.split("://", 1)
        redacted_url = f"{scheme}://***@{rest.split('@', 1)[1]}"

    last_error = RuntimeError(f"Failed to connect to database: {redacted_url}")
    attempts = max(1, retries)
    for _ in range(attempts):
        try:
            return create_connection(db_url)
        except Exception as error:
            last_error = error
            time.sleep(delay)
    raise RuntimeError(
        f"Failed to connect after {attempts} attempts with {delay}s delay ({redacted_url}): {last_error}"
    ) from last_error


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
