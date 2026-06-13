from pydantic import BaseModel

class AuthUserRequest(BaseModel):
    email: str
    password: str

class AuthUserResponse(BaseModel):
    token: str