from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.digital_lock_models import *
from app.modules.utils.binary_handler import BinaryHandler
from http import HTTPStatus

router = APIRouter()

@router.get('/digital_lock/all')
def get_all_digital_locks(db: Database = Depends(get_database)):
    repo = DigitalLockRepository(db)
    digital_locks = repo.get_all_digital_locks()
    for lock in digital_locks:
        lock['secret_key'] = BinaryHandler.get_hex_str_from_bytes(lock['secret_key'])
    return digital_locks


@router.post('/digital_lock/new')
def create_digital_lock(digital_lock_data: CreateDigitalLockRequest, db: Database = Depends(get_database)) -> CreateDigitalLockResponse:
    repo = DigitalLockRepository(db)

    try:
        digital_lock_id, created_at = repo.create_digital_lock(room_id=digital_lock_data.room_id)
        
        return CreateDigitalLockResponse(digital_lock_id=digital_lock_id, created_at=created_at)
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))