from pydantic import BaseModel
from fastapi import APIRouter
from app.schemas.health_check import HiRequest, HiResponse

router = APIRouter()

@router.post('/')
def health_check(req: HiRequest) -> HiResponse:
    """Health check endpoint, that returns a string 'roi, [name]'.

    Args:
        req (HiRequest): the request with the name.

    Returns:
        HiResponse: the response.
    """
    response = f'roi, {req.message}!'
    return HiResponse(message=response)