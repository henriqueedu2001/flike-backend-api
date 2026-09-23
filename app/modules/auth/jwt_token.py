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
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], options={"require": ["exp", "user_id"]})
        if type(payload["user_id"]) is not int or payload["user_id"] <= 0:
            return False
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False
    return True


def get_user_id_from_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], options={"require": ["exp", "user_id"]})
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    return payload.get('user_id')