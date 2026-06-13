from mysql.connector.pooling import MySQLConnectionPool
from app.services.env import get_env_variables

env_vars = get_env_variables()

POOL = MySQLConnectionPool(
    pool_name='MySQLConnectionPool',
    pool_size=16,
    pool_reset_session=True,

    # env variables
    host=env_vars.DB_HOST,
    port=env_vars.DB_PORT,
    user=env_vars.DB_USER,
    password=env_vars.DB_PASSWORD,
    database=env_vars.DB_DATABASE
)