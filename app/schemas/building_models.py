from pydantic import BaseModel
from datetime import datetime

class CreateBuildingRequest(BaseModel):
    institution_id: int
    name: str
    address_line_1: str
    address_line_2: str
    city: str
    state: str
    zip_code: str
    country: str


class CreateBuildingResponse(BaseModel):
    building_id: int
    created_at: datetime