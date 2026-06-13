from pydantic import BaseModel

class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str


class CreateUserResponse(BaseModel):
    user_id: int