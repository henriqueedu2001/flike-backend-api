from typing import *
from collections.abc import Generator
from datetime import datetime
from app.database.pool import get_pool
from app.services.time import as_utc


class Database:
    def __init__(self):
        self.connection = get_pool().get_connection()
        self.cursor = self.connection.cursor(dictionary=True)
        self.cursor.execute("SET time_zone = '+00:00'")

    def execute(self, query: str, params: Optional[tuple] = None) -> None:
        self.cursor.execute(query, params)

    def execute_many(self, query: str, params: Optional[List[tuple]] = None) -> None:
        self.cursor.executemany(query, params)

    @staticmethod
    def _utc_row(row):
        if row is None:
            return None
        return {key: as_utc(value) if isinstance(value, datetime) else value
                for key, value in row.items()}

    def fetch_one(self) -> Optional[dict]:
        return self._utc_row(self.cursor.fetchone())

    def fetch_all(self) -> list[dict]:
        return [self._utc_row(row) for row in self.cursor.fetchall()]

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
        # Read-only requests may also have opened a transaction.
        db.rollback()
        db.close()
