import jwt
import datetime
from app.services.env import get_env_variables

env_vars = get_env_variables()

JWT_SECRET = env_vars.JWT_SECRET

def generate_jwt_token(user_id: int):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token


def validate_jwt_token(token: str):
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False
    return True