import mysql.connector
from typing import *
from datetime import datetime
from collections.abc import Callable
from mysql.connector.cursor import MySQLCursor
from mysql.connector import MySQLConnection

DB_CONFIG = {
    'host': 'localhost',
    'user': 'admin',
    'password': 'admin123',
    'database': 'flike',
    'port': '5469'
}

def main():
    """Runs the retrieval and storing routine with MySQL and external APIs.
    """
    log_message("Trying to connect to the MySQL Database...")
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            log_message('Connection with the MySQL Database was successful!')
            with conn.cursor() as cursor:
                try:
                    drop_database(cursor)
                except Exception as error:
                    log_message(f'Error: {error}')
                    conn.rollback()
                finally:
                    conn.close()
    except Exception as error:
        log_message(f'Error: {error}')
    finally:
        cursor.close()
        log_message('Connection closed')
    log_message('Application finished')
    return

def drop_database(cursor: MySQLCursor):
    drop_table(cursor, 'auth')
    drop_table(cursor, 'event_log')
    drop_table(cursor, 'digital_key')
    drop_table(cursor, 'digital_lock')
    drop_table(cursor, 'room')
    drop_table(cursor, 'building')
    drop_table(cursor, 'institution')
    drop_table(cursor, 'user')
    return


def drop_table(cursor: MySQLCursor, table_name: str):
    drop_table = f'DROP TABLE {table_name};'
    cursor.execute(drop_table)
    return


def log_message(message: str):
    """Logs the message, by printing it with the current timestamp.

    Args:
        message (str): the log message
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


if __name__ == "__main__":
    main()