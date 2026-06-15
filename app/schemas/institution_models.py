from pydantic import BaseModel
from datetime import datetime

class CreateInstitutionRequest(BaseModel):
    user_id: str
    building_name: str


class CreateInstitutionResponse(BaseModel):
    institution_id: int
    created_at: datetime