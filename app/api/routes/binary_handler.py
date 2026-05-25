from pydantic import BaseModel
from fastapi import APIRouter
from app.modules.binary_handler import BinaryHandler
from app.schemas.binary_handler_models import EncodeIntRequest, EncodeIntResponse

router = APIRouter()

@router.post('/encode_int')
def encode_int(encode_int_request: EncodeIntRequest) -> EncodeIntResponse:
    """Encodes a given input int in to bytes, as an integer of 64 bits by default. 

    Args:
        encode_int_request (EncodeIntRequest): the input integer

    Returns:
        EncodeIntResponse: the output integer, encoded
    """
    encoded_int = BinaryHandler.get_hex_str_from_bytes(BinaryHandler.encode_int(encode_int_request.raw_int))
    response = f'{encoded_int}'.strip()
    response = EncodeIntResponse(encoded_int=response)
    return response