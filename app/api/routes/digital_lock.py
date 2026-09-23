from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.digital_lock_models import *
from app.modules.utils.binary_handler import BinaryHandler
from http import HTTPStatus
from app.api.routes.auth import verify_token
from app.modules.auth.jwt_token import get_user_id_from_token

router = APIRouter(dependencies=[Depends(verify_token)])

def _serialize_digital_lock(lock: dict) -> dict:
    return {name: lock[name] for name in ('id', 'room_id', 'created_at')}


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
def create_digital_lock(digital_lock_data: CreateDigitalLockRequest,
                        token: Annotated[str, Depends(verify_token)],
                        db: Database = Depends(get_database)) -> CreateDigitalLockResponse:
    try:
        owner_id = RoomRepository(db).get_owner_id(digital_lock_data.room_id)
    except RoomNotFound as error:
        raise HTTPException(404, str(error)) from None
    if owner_id != get_user_id_from_token(token):
        raise HTTPException(403, 'Somente o responsável pela instituição pode cadastrar esta tranca.')
    digital_lock_id, created_at = DigitalLockRepository(db).create_digital_lock(digital_lock_data.room_id)
    return CreateDigitalLockResponse(digital_lock_id=digital_lock_id, created_at=created_at)
