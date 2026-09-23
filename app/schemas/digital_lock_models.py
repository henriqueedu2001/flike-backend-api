from pydantic import BaseModel, PositiveInt, StringConstraints
from typing import Annotated

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
from datetime import datetime

class CreateDigitalLockRequest(BaseModel):
    room_id: PositiveInt


class CreateDigitalLockResponse(BaseModel):
    digital_lock_id: int
    created_at: datetime


class UpdateDigitalLockRequest(BaseModel):
    room_id: PositiveInt