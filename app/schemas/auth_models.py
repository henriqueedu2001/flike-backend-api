from pydantic import BaseModel, EmailStr, field_validator


class AuthUserRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class AuthUserResponse(BaseModel):
    token: str
