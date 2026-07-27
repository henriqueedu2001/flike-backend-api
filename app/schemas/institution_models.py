from pydantic import BaseModel
from datetime import datetime

class CreateInstitutionRequest(BaseModel):
    name: str


class CreateInstitutionResponse(BaseModel):
    institution_id: int
    created_at: datetime


class UpdateInstitutionRequest(BaseModel):
    name: str