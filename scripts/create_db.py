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
                    create_auth_table(cursor)
                    create_user_table(cursor)
                    create_institution_table(cursor)
                    create_building_table(cursor)
                    create_room_table(cursor)
                    create_digital_lock_table(cursor)
                    create_digital_key_table(cursor)
                    create_digital_lock_table(cursor)
                    create_event_log_table(cursor)
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


def create_auth_table(cursor: MySQLCursor):
    create_auth_table_query = """
        CREATE TABLE IF NOT EXISTS auth (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hashed_email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            salt VARCHAR(255) NOT NULL
        );
    """
    create_table('auth', query=create_auth_table_query, cursor=cursor)
    return


def create_user_table(cursor: MySQLCursor):
    create_user_table_query = """
        CREATE TABLE IF NOT EXISTS user (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """
    create_table('user', query=create_user_table_query, cursor=cursor)
    return


def create_institution_table(cursor: MySQLCursor):
    create_institution_table_query = """
        CREATE TABLE IF NOT EXISTS institution (
            id INT AUTO_INCREMENT PRIMARY KEY,
            owner_id INT NOT NULL,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES user(id)
        );
    """
    create_table('institution', query=create_institution_table_query, cursor=cursor)
    return


def create_building_table(cursor: MySQLCursor):
    create_building_table_query = """
        CREATE TABLE IF NOT EXISTS building (
            id INT AUTO_INCREMENT PRIMARY KEY,
            institution_id INT NOT NULL,
            name VARCHAR(255) NOT NULL,
            address_line_1 VARCHAR(255) NOT NULL,
            address_line_2 VARCHAR(255) NULL,
            city VARCHAR(255) NOT NULL,
            state VARCHAR(255) NOT NULL,
            zip_code VARCHAR(255) NOT NULL,
            country VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (institution_id) REFERENCES institution(id)
        );
    """
    create_table('building', query=create_building_table_query, cursor=cursor)
    return


def create_room_table(cursor: MySQLCursor):
    create_room_table_query = """
        CREATE TABLE IF NOT EXISTS room (
            id INT AUTO_INCREMENT PRIMARY KEY,
            building_id INT NOT NULL,
            name VARCHAR(255) NOT NULL,
            number VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (building_id) REFERENCES building(id)
        );
    """
    create_table('room', query=create_room_table_query, cursor=cursor)
    return


def create_digital_lock_table(cursor: MySQLCursor):
    create_digital_lock_table_query = """
        CREATE TABLE IF NOT EXISTS digital_lock (
            id INT AUTO_INCREMENT PRIMARY KEY,
            room_id INT NOT NULL,
            secret_key BINARY(32) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES room(id)
        );
    """
    create_table('digital_lock', query=create_digital_lock_table_query, cursor=cursor)
    return


def create_digital_key_table(cursor: MySQLCursor):
    create_digital_key_table_query = """
        CREATE TABLE IF NOT EXISTS digital_key (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            room_id INT NOT NULL,
            secret_key BINARY(32) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id),
            FOREIGN KEY (room_id) REFERENCES room(id)
        );
    """
    create_table('digital_key', query=create_digital_key_table_query, cursor=cursor)
    return


def create_event_log_table(cursor: MySQLCursor):
    create_event_log_table_query = """
        CREATE TABLE IF NOT EXISTS event_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            digital_lock_id INT NOT NULL,
            type VARCHAR(255) NOT NULL,
            log TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (digital_lock_id) REFERENCES digital_lock(id)
        );
    """
    create_table('event_log', query=create_event_log_table_query, cursor=cursor)
    return


def create_table(table_name: str, query: str, cursor: MySQLCursor):
    try:
        log_message(f'Creating table \"{table_name}\"')
        cursor.execute(query)
        log_message(f'Table \"{table_name}\" created with success!')
    except Exception as error:
        raise error
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