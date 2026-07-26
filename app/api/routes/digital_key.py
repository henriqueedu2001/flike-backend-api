from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.digital_key_models import *
from app.modules.utils.binary_handler import BinaryHandler
from app.modules.auth.jwt_token import get_user_id_from_token
from app.api.routes.auth import verify_token
from http import HTTPStatus

router = APIRouter()

def _serialize_digital_key(digital_key: dict) -> dict:
    payload = digital_key['payload']
    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    digital_key['payload'] = BinaryHandler.get_hex_str_from_bytes(payload)
    return digital_key


@router.get('/digital_key/all')
def get_all_digital_locks(db: Database = Depends(get_database)):
    repo = DigitalKeyRepository(db)
    digital_keys = repo.get_all_digital_keys()
    return [_serialize_digital_key(digital_key) for digital_key in digital_keys]


@router.get('/digital_key')
def get_digital_key(
    id: Optional[int] = None,
    key_id: Optional[int] = None,
    db: Database = Depends(get_database)
):
    repo = DigitalKeyRepository(db)

    if key_id is not None:
        try:
            digital_key = repo.get_digital_key(key_id)
        except DigitalKeyNotFound as error:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))
        return _serialize_digital_key(digital_key)

    if id is not None:
        digital_keys = repo.get_digital_keys_by_user(id)
        return [_serialize_digital_key(digital_key) for digital_key in digital_keys]

    raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='either id or key_id must be provided')


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


@router.post('/digital_key/request')
def request_digital_key(
    request_data: RequestDigitalKeyRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
) -> RequestDigitalKeyResponse:
    repo = DigitalKeyRequestRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        request_id, created_at = repo.create_request(user_id=user_id, digital_lock_id=request_data.lock_id)
        return RequestDigitalKeyResponse(request_id=request_id, created_at=created_at)
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))