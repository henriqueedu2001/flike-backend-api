from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import Database, get_database
from app.database.repositories import (
    DigitalKeyRepository, DigitalKeyRequestRepository, DigitalLockRepository,
    DigitalKeyNotFound, DigitalLockNotFound,
)
from app.schemas.digital_key_models import RequestDigitalKeyRequest, RequestDigitalKeyResponse, RequestStatus
from app.modules.auth.jwt_token import get_user_id_from_token
from app.api.routes.auth import verify_token

router = APIRouter(dependencies=[Depends(verify_token)])


def _serialize_digital_key(key: dict) -> dict:
    return {**key, 'payload': bytes(key['payload']).hex()}


@router.get('/digital_key/all')
def get_all_digital_keys(token: Annotated[str, Depends(verify_token)], db: Database = Depends(get_database)):
    return [_serialize_digital_key(key) for key in DigitalKeyRepository(db).get_digital_keys_by_user(get_user_id_from_token(token))]


@router.get('/digital_key')
def get_digital_key(token: Annotated[str, Depends(verify_token)], id: Optional[int] = None,
                    key_id: Optional[int] = None, db: Database = Depends(get_database)):
    user_id = get_user_id_from_token(token)
    repo = DigitalKeyRepository(db)
    if id is not None and key_id is not None:
        raise HTTPException(400, 'Informe somente id ou key_id.')
    if key_id is not None:
        try:
            key = repo.get_digital_key(key_id)
            owner_id = DigitalLockRepository(db).get_institution_owner(key['digital_lock_id'])
        except (DigitalKeyNotFound, DigitalLockNotFound) as error:
            raise HTTPException(404, str(error)) from None
        if key['user_id'] != user_id and owner_id != user_id:
            raise HTTPException(403, 'Você não pode consultar esta chave digital.')
        return _serialize_digital_key(key)
    if id is not None and id != user_id:
        raise HTTPException(403, 'Você só pode consultar sua própria lista de chaves.')
    return [_serialize_digital_key(key) for key in repo.get_digital_keys_by_user(user_id)]


@router.post('/digital_key/new', deprecated=True)
@router.post('/digital_key/use', deprecated=True)
def retired_key_operation():
    raise HTTPException(410, 'Chaves são emitidas pela aprovação de pedidos e permanecem reutilizáveis até expirar.')


@router.get('/digital_key/requests')
def get_my_digital_key_requests(token: Annotated[str, Depends(verify_token)],
                                status: Optional[RequestStatus] = None,
                                db: Database = Depends(get_database)):
    return DigitalKeyRequestRepository(db).get_requests_by_user(get_user_id_from_token(token), status)


@router.post('/digital_key/request')
def request_digital_key(request_data: RequestDigitalKeyRequest,
                        token: Annotated[str, Depends(verify_token)],
                        db: Database = Depends(get_database)) -> RequestDigitalKeyResponse:
    try:
        request_id, created_at = DigitalKeyRequestRepository(db).create_request(
            user_id=get_user_id_from_token(token), digital_lock_id=request_data.lock_id)
    except DigitalLockNotFound as error:
        raise HTTPException(404, str(error)) from None
    return RequestDigitalKeyResponse(request_id=request_id, created_at=created_at)
