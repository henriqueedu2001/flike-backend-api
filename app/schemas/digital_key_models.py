from pydantic import BaseModel
from datetime import datetime

class CreateDigitalKeyRequest(BaseModel):
    user_id: int
    digital_lock_id: int
    expiration: datetime


class CreateDigitalKeyResponse(BaseModel):
    digital_key_id: int
    created_at: datetime