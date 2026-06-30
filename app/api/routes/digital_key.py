from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.digital_key_models import *
from app.modules.utils.binary_handler import BinaryHandler
from http import HTTPStatus

router = APIRouter()

@router.get('/digital_key/all')
def get_all_digital_locks(db: Database = Depends(get_database)):
    repo = DigitalKeyRepository(db)
    digital_keys = repo.get_all_digital_keys()
    for digital_key in digital_keys:
        digital_key['payload'] = BinaryHandler.get_hex_str_from_bytes(digital_key['payload'])
    return digital_keys


@router.post('/digital_key/new')
def create_digital_lock(digital_key_data: CreateDigitalKeyRequest, db: Database = Depends(get_database)) -> CreateDigitalKeyResponse:
    repo = DigitalKeyRepository(db)

    try:
        digital_key_id, created_at = repo.create_digital_key(
            user_id=digital_key_data.user_id,
            digital_lock_id=digital_key_data.digital_lock_id,
            expiration=digital_key_data.expiration
        )
        return CreateDigitalKeyResponse(digital_key_id=digital_key_id, created_at=created_at)
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))