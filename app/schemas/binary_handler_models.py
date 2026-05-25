from pydantic import BaseModel

class EncodeIntRequest(BaseModel):
    raw_int: int


class EncodeIntResponse(BaseModel):
    encoded_int: str