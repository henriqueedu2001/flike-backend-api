import os
from dotenv import load_dotenv

load_dotenv()

class EnvironmentVariables:
    def __init__(self):
        self.DB_HOST = os.getenv('DB_HOST')
        self.DB_USER = os.getenv('DB_USER')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD')
        self.DB_DATABASE = os.getenv('DB_DATABASE')
        self.DB_PORT = os.getenv('DB_PORT')
        pass


environment_variables = EnvironmentVariables()


def get_env_variables():
    return environment_variables