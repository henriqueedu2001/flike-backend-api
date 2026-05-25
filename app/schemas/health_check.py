from pydantic import BaseModel

class HiRequest(BaseModel):
    message: str


class HiResponse(BaseModel):
    message: str