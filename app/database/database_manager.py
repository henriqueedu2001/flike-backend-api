from typing import *
from collections.abc import Generator
from mysql.connector import MySQLConnection
from mysql.connector.cursor import MySQLCursor
from app.database.pool import POOL


class Database:
    def __init__(self):
        self.connection: MySQLConnection = POOL.get_connection()
        self.cursor: MySQLCursor = self.connection.cursor(dictionary=True)


    def execute(self, query: str, params: Optional[tuple] = None) -> None:
        self.cursor.execute(query, params)
    

    def execute_many(self, query: str, params: Optional[List[tuple]] = None) -> None:
        self.cursor.executemany(query, params)


    def fetch_one(self) -> Optional[dict]:
        return self.cursor.fetchone()


    def fetch_all(self) -> list[dict]:
        return self.cursor.fetchall()


    def commit(self) -> None:
        self.connection.commit()


    def rollback(self) -> None:
        self.connection.rollback()


    def close(self) -> None:
        self.cursor.close()
        self.connection.close()


def get_database() -> Generator[Database, None, None]:
    db = Database()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()