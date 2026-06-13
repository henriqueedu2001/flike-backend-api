from pydantic import BaseModel

class AuthUserRequest(BaseModel):
    email: str
    password: str