from pydantic import BaseModel
from datetime import datetime

class CreateDigitalLockRequest(BaseModel):
    room_id: int


class CreateDigitalLockResponse(BaseModel):
    digital_lock_id: int
    created_at: datetime