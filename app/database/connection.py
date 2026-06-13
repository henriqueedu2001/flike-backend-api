import mysql.connector
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

def create_connection() -> MySQLConnection:
    return mysql.connector.connect(**DB_CONFIG)