import mysql.connector
from typing import *
from datetime import datetime
from collections.abc import Callable
from mysql.connector.cursor import MySQLCursor
from mysql.connector import MySQLConnection
from app.services.env import get_env_variables

env_vars = get_env_variables()

DB_CONFIG = {
    'host': env_vars.DB_HOST,
    'user': env_vars.DB_USER,
    'password': env_vars.DB_PASSWORD,
    'database': env_vars.DB_DATABASE,
    'port': env_vars.DB_PORT
}

class IncompatibleSchemaError(RuntimeError):
    """Existing data requires an explicit migration, never implicit schema changes."""


def validate_existing_schema(cursor: MySQLCursor, table_prefix: str = '') -> bool:
    """Accept an empty DB or the current schema; reject partial/legacy schemas.

    The prefix is used only by isolated migration tests. All metadata lookup
    values are parameters; no caller-provided identifier is interpolated in SQL.
    Returns True for a compatible existing schema and False for an empty one.
    """
    tables = ('auth', 'user', 'institution', 'building', 'room', 'digital_lock',
              'digital_key', 'digital_key_request', 'event_log')
    expected = {table_prefix + name for name in tables}
    cursor.execute(
        'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()'
    )
    present = {row[0] for row in cursor.fetchall()} & expected
    if not present:
        return False

    problems = []
    missing_tables = expected - present
    if missing_tables:
        problems.append('tabelas ausentes: ' + ', '.join(sorted(missing_tables)))

    cursor.execute(
        'SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()'
    )
    columns = {}
    for table, column in cursor.fetchall():
        columns.setdefault(table, set()).add(column)
    required_columns = {
        'user': {'id', 'email'},
        'digital_key': {'id', 'request_id', 'user_id', 'digital_lock_id', 'payload', 'created_at', 'expires_at'},
        'digital_key_request': {'id', 'user_id', 'digital_lock_id', 'status', 'created_at', 'decided_at'},
    }
    for table, required in required_columns.items():
        actual_table = table_prefix + table
        if actual_table in present:
            missing = required - columns.get(actual_table, set())
            if missing:
                problems.append(actual_table + ': colunas ausentes ' + ', '.join(sorted(missing)))

    cursor.execute("""
        SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND NON_UNIQUE = 0
        ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
    """)
    indexes = {}
    for table, index, column in cursor.fetchall():
        indexes.setdefault((table, index), []).append(column)
    for table, column in (('user', 'email'), ('digital_key', 'request_id')):
        actual_table = table_prefix + table
        if actual_table in present and not any(
            indexed_table == actual_table and indexed_columns == [column]
            for (indexed_table, _), indexed_columns in indexes.items()
        ):
            problems.append(f'{actual_table}.{column}: restrição UNIQUE ausente')

    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
    """)
    foreign_keys = set(cursor.fetchall())
    required_fk = (table_prefix + 'digital_key', 'request_id', table_prefix + 'digital_key_request', 'id')
    if table_prefix + 'digital_key' in present and required_fk not in foreign_keys:
        problems.append('vínculo FK de digital_key.request_id para digital_key_request.id ausente')

    if problems:
        raise IncompatibleSchemaError(
            'Schema existente incompatível ou incompleto; nenhuma tabela foi alterada. '
            + '; '.join(problems)
            + '. Faça backup e revise migrations/001_request_key_integrity.sql para uma migração manual, '
              'ou selecione um banco vazio de demonstração. Não há migração automática.'
        )
    return True


def main():
    """Create the schema in the explicitly configured database."""
    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            validate_existing_schema(cursor)
            cursor.execute("SET time_zone = '+00:00'")
            create_auth_table(cursor)
            create_user_table(cursor)
            create_institution_table(cursor)
            create_building_table(cursor)
            create_room_table(cursor)
            create_digital_lock_table(cursor)
            create_digital_key_request_table(cursor)
            create_digital_key_table(cursor)
            create_event_log_table(cursor)
        conn.commit()


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
            email VARCHAR(255) UNIQUE NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
            digital_lock_id INT NOT NULL,
            request_id INT NULL UNIQUE,
            payload BINARY(48) NOT NULL,
            expires_at DATETIME NULL,
            used BOOLEAN NOT NULL DEFAULT FALSE,
            used_at TIMESTAMP NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id),
            FOREIGN KEY (digital_lock_id) REFERENCES digital_lock(id),
            FOREIGN KEY (request_id) REFERENCES digital_key_request(id)
        );
    """
    create_table('digital_key', query=create_digital_key_table_query, cursor=cursor)
    return


def create_digital_key_request_table(cursor: MySQLCursor):
    create_digital_key_request_table_query = """
        CREATE TABLE IF NOT EXISTS digital_key_request (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            digital_lock_id INT NOT NULL,
            status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
            decided_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id),
            FOREIGN KEY (digital_lock_id) REFERENCES digital_lock(id)
        );
    """
    create_table('digital_key_request', query=create_digital_key_request_table_query, cursor=cursor)
    return


def create_event_log_table(cursor: MySQLCursor):
    create_event_log_table_query = """
        CREATE TABLE IF NOT EXISTS event_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            digital_lock_id INT NOT NULL,
            type VARCHAR(255) NOT NULL,
            log TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
    try:
        main()
    except IncompatibleSchemaError as error:
        raise SystemExit(str(error)) from None