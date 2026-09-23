from pydantic import BaseModel, PositiveInt, StringConstraints
from typing import Annotated

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
from datetime import datetime

class CreateBuildingRequest(BaseModel):
    institution_id: PositiveInt
    name: Text
    address_line_1: Text
    address_line_2: OptionalText = ""
    city: Text
    state: Text
    zip_code: Text
    country: Text


class CreateBuildingResponse(BaseModel):
    building_id: PositiveInt
    created_at: datetime


class UpdateBuildingRequest(BaseModel):
    institution_id: PositiveInt
    name: Text
    address_line_1: Text
    address_line_2: OptionalText = ""
    city: Text
    state: Text
    zip_code: Text
    country: Text