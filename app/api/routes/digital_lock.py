from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.digital_lock_models import *
from app.modules.utils.binary_handler import BinaryHandler
from http import HTTPStatus

router = APIRouter()

def _serialize_digital_lock(lock: dict) -> dict:
    lock['secret_key'] = bytes(lock['secret_key']).hex()
    return lock


@router.get('/digital_lock/all')
def get_all_digital_locks(db: Database = Depends(get_database)):
    repo = DigitalLockRepository(db)
    digital_locks = repo.get_all_digital_locks()
    return [_serialize_digital_lock(lock) for lock in digital_locks]


@router.get('/digital_lock')
def get_digital_locks_by_room(room_id: int, db: Database = Depends(get_database)):
    repo = DigitalLockRepository(db)
    digital_locks = repo.get_locks_by_room(room_id)
    return [_serialize_digital_lock(lock) for lock in digital_locks]


@router.post('/digital_lock/new')
def create_digital_lock(digital_lock_data: CreateDigitalLockRequest, db: Database = Depends(get_database)) -> CreateDigitalLockResponse:
    repo = DigitalLockRepository(db)

    try:
        digital_lock_id, created_at = repo.create_digital_lock(room_id=digital_lock_data.room_id)
        
        return CreateDigitalLockResponse(digital_lock_id=digital_lock_id, created_at=created_at)
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))