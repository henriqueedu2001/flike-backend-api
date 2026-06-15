from pydantic import BaseModel
from datetime import datetime

class CreateRoomRequest(BaseModel):
    building_id: int
    name: str
    number: str
    

class CreateRoomResponse(BaseModel):
    room_id: int
    created_at: datetime