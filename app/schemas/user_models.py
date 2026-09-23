from typing import Annotated
from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class UserIdentity(BaseModel):
    name: Name
    email: EmailStr

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class CreateUserRequest(UserIdentity):
    password: Password


class CreateUserResponse(BaseModel):
    user_id: int


class UpdateUserRequest(UserIdentity):
    pass


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: Password
