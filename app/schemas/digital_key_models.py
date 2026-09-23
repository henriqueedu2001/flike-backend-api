from pydantic import AwareDatetime, BaseModel, PositiveInt, field_validator
from datetime import datetime
from typing import Literal, Optional
from app.services.time import as_utc, utc_now

RequestStatus = Literal['pending', 'approved', 'rejected']


class ExpirationRequest(BaseModel):
    expires_at: Optional[AwareDatetime] = None

    @field_validator('expires_at')
    @classmethod
    def valid_expiration(cls, value):
        if value is not None:
            value = as_utc(value).replace(microsecond=0)
            if value <= utc_now():
                raise ValueError('A expiração deve ser posterior ao instante atual.')
        return value


class RequestDigitalKeyRequest(BaseModel):
    lock_id: PositiveInt


class RequestDigitalKeyResponse(BaseModel):
    request_id: int
    created_at: datetime


class ApproveDigitalKeyRequestRequest(ExpirationRequest):
    pass


class ApproveDigitalKeyRequestResponse(BaseModel):
    request_id: int
    digital_key_id: int
    created_at: datetime
