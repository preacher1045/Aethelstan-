import psycopg2
from psycopg2.extras import RealDictCursor

from backend.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER


def db_connection():
    if not DB_NAME or not DB_USER:
        raise ValueError("DB_NAME and DB_USER must be set in the environment.")

    conn_params = {
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "host": DB_HOST,
        "cursor_factory": RealDictCursor,
    }
    if DB_PORT:
        conn_params["port"] = int(DB_PORT)

    return psycopg2.connect(**conn_params)
    


