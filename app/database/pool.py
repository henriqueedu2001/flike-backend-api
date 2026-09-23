"""Create the connection pool on first use, not while importing the API."""
from threading import Lock
from mysql.connector.pooling import MySQLConnectionPool
from app.services.env import get_env_variables

_pool = None
_pool_lock = Lock()


def get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                env = get_env_variables()
                _pool = MySQLConnectionPool(
                    pool_name='flike', pool_size=16, pool_reset_session=True,
                    host=env.DB_HOST, port=int(env.DB_PORT or 3306),
                    user=env.DB_USER, password=env.DB_PASSWORD,
                    database=env.DB_DATABASE, time_zone='+00:00',
                    autocommit=False,
                )
    return _pool
