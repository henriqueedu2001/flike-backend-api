from pydantic import BaseModel, PositiveInt, StringConstraints
from typing import Annotated

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
from datetime import datetime

class CreateRoomRequest(BaseModel):
    building_id: PositiveInt
    name: Text
    number: Text
    

class CreateRoomResponse(BaseModel):
    room_id: PositiveInt
    created_at: datetime


class UpdateRoomRequest(BaseModel):
    building_id: PositiveInt
    name: Text
    number: Text