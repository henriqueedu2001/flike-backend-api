from pydantic import BaseModel, PositiveInt, StringConstraints
from typing import Annotated

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
from datetime import datetime

class CreateInstitutionRequest(BaseModel):
    name: Text


class CreateInstitutionResponse(BaseModel):
    institution_id: int
    created_at: datetime


class UpdateInstitutionRequest(BaseModel):
    name: Text