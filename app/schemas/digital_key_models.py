from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CreateDigitalKeyRequest(BaseModel):
    user_id: int
    digital_lock_id: int
    expiration: datetime


class CreateDigitalKeyResponse(BaseModel):
    digital_key_id: int
    created_at: datetime


class RequestDigitalKeyRequest(BaseModel):
    lock_id: int


class RequestDigitalKeyResponse(BaseModel):
    request_id: int
    created_at: datetime


class IssueDigitalKeyRequest(BaseModel):
    user_id: int
    lock_id: int
    expires_at: Optional[datetime] = None


class IssueDigitalKeyResponse(BaseModel):
    digital_key_id: int
    created_at: datetime


class ApproveDigitalKeyRequestRequest(BaseModel):
    expires_at: Optional[datetime] = None


class ApproveDigitalKeyRequestResponse(BaseModel):
    request_id: int
    digital_key_id: int
    created_at: datetime