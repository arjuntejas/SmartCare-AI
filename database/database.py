import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE = os.path.join(
    BASE_DIR,
    "database",
    "smartcare.db"
)


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def execute_query(query, parameters=(), fetch=False):
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(query, parameters)

    if fetch:
        result = cursor.fetchall()
        connection.close()
        return result

    connection.commit()
    connection.close()