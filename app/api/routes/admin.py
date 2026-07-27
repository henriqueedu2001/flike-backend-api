from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.institution_models import *
from app.schemas.building_models import *
from app.schemas.room_models import *
from app.schemas.digital_lock_models import *
from app.schemas.digital_key_models import *
from app.api.routes.auth import verify_token
from app.api.routes.digital_lock import _serialize_digital_lock
from app.modules.auth.jwt_token import get_user_id_from_token
from datetime import datetime, timedelta
from http import HTTPStatus

router = APIRouter(prefix='/admin', dependencies=[Depends(verify_token)])


# ---- Institutions ----

@router.get('/institutions')
def get_institutions(
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = InstitutionRepository(db)
    user_id = get_user_id_from_token(token)
    return repo.get_institutions_by_owner(user_id)


@router.post('/institutions')
def create_institution(
    institution_data: CreateInstitutionRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
) -> CreateInstitutionResponse:
    repo = InstitutionRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        institution_id, created_at = repo.create_institution(user_id, institution_data.name)
        return CreateInstitutionResponse(institution_id=institution_id, created_at=created_at)
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))


@router.put('/institutions/{id}')
def update_institution(
    id: int,
    institution_data: UpdateInstitutionRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = InstitutionRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        institution = repo.get_institution(id)
    except InstitutionNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if institution.get('owner_id') != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    return repo.update_institution(id, institution_data.name)


@router.delete('/institutions/{id}')
def delete_institution(
    id: int,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = InstitutionRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        institution = repo.get_institution(id)
    except InstitutionNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if institution.get('owner_id') != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        repo.delete_institution(id)
    except ResourceInUse as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))
    return {"message": "institution deleted successfully"}


# ---- Buildings ----

@router.get('/buildings')
def get_buildings(
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = BuildingRepository(db)
    user_id = get_user_id_from_token(token)
    return repo.get_buildings_by_owner(user_id)


@router.post('/buildings')
def create_building(
    building_data: CreateBuildingRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
) -> CreateBuildingResponse:
    institution_repo = InstitutionRepository(db)
    repo = BuildingRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        institution = institution_repo.get_institution(building_data.institution_id)
    except InstitutionNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if institution.get('owner_id') != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        building_id, created_at = repo.create_building(
            institution_id=building_data.institution_id,
            name=building_data.name,
            address_line_1=building_data.address_line_1,
            address_line_2=building_data.address_line_2,
            city=building_data.city,
            state=building_data.state,
            zip_code=building_data.zip_code,
            country=building_data.country,
        )
        return CreateBuildingResponse(building_id=building_id, created_at=created_at)
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))


@router.put('/buildings/{id}')
def update_building(
    id: int,
    building_data: UpdateBuildingRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = BuildingRepository(db)
    institution_repo = InstitutionRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        owner_id = repo.get_owner_id(id)
    except BuildingNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        target_institution = institution_repo.get_institution(building_data.institution_id)
    except InstitutionNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if target_institution.get('owner_id') != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='cannot move building to an institution you do not own')

    try:
        return repo.update_building(
            id,
            institution_id=building_data.institution_id,
            name=building_data.name,
            address_line_1=building_data.address_line_1,
            address_line_2=building_data.address_line_2,
            city=building_data.city,
            state=building_data.state,
            zip_code=building_data.zip_code,
            country=building_data.country,
        )
    except BuildingNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))


@router.delete('/buildings/{id}')
def delete_building(
    id: int,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = BuildingRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        owner_id = repo.get_owner_id(id)
    except BuildingNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        repo.delete_building(id)
    except BuildingNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))
    except ResourceInUse as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))
    return {"message": "building deleted successfully"}


# ---- Rooms ----

@router.get('/rooms')
def get_rooms(
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = RoomRepository(db)
    user_id = get_user_id_from_token(token)
    return repo.get_rooms_by_owner(user_id)


@router.post('/rooms')
def create_room(
    room_data: CreateRoomRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
) -> CreateRoomResponse:
    building_repo = BuildingRepository(db)
    repo = RoomRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        owner_id = building_repo.get_owner_id(room_data.building_id)
    except BuildingNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        room_id, created_at = repo.create_room(
            building_id=room_data.building_id,
            name=room_data.name,
            number=room_data.number
        )
        return CreateRoomResponse(room_id=room_id, created_at=created_at)
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))


@router.put('/rooms/{id}')
def update_room(
    id: int,
    room_data: UpdateRoomRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = RoomRepository(db)
    building_repo = BuildingRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        owner_id = repo.get_owner_id(id)
    except RoomNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        target_owner_id = building_repo.get_owner_id(room_data.building_id)
    except BuildingNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if target_owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='cannot move room to a building you do not own')

    try:
        return repo.update_room(id, building_id=room_data.building_id, name=room_data.name, number=room_data.number)
    except RoomNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))


@router.delete('/rooms/{id}')
def delete_room(
    id: int,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = RoomRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        owner_id = repo.get_owner_id(id)
    except RoomNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        repo.delete_room(id)
    except RoomNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))
    except ResourceInUse as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))
    return {"message": "room deleted successfully"}


@router.get('/rooms/{id}/key-holders')
def get_room_key_holders(
    id: int,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    room_repo = RoomRepository(db)
    key_repo = DigitalKeyRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        owner_id = room_repo.get_owner_id(id)
    except RoomNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    return key_repo.get_key_holders_by_room(id)


# ---- Digital Locks ----

@router.get('/locks')
def get_locks(
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = DigitalLockRepository(db)
    user_id = get_user_id_from_token(token)
    locks = repo.get_locks_by_owner(user_id)
    return [_serialize_digital_lock(lock) for lock in locks]


@router.post('/locks')
def create_lock(
    lock_data: CreateDigitalLockRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
) -> CreateDigitalLockResponse:
    room_repo = RoomRepository(db)
    repo = DigitalLockRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        owner_id = room_repo.get_owner_id(lock_data.room_id)
    except RoomNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        digital_lock_id, created_at = repo.create_digital_lock(room_id=lock_data.room_id)
        return CreateDigitalLockResponse(digital_lock_id=digital_lock_id, created_at=created_at)
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))


@router.put('/locks/{id}')
def update_lock(
    id: int,
    lock_data: UpdateDigitalLockRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = DigitalLockRepository(db)
    room_repo = RoomRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        owner_id = repo.get_institution_owner(id)
    except DigitalLockNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        target_owner_id = room_repo.get_owner_id(lock_data.room_id)
    except RoomNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if target_owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='cannot move digital lock to a room you do not own')

    try:
        lock = repo.update_digital_lock(id, room_id=lock_data.room_id)
    except DigitalLockNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    return _serialize_digital_lock(lock)


@router.delete('/locks/{id}')
def delete_lock(
    id: int,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = DigitalLockRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        owner_id = repo.get_institution_owner(id)
    except DigitalLockNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can perform this action')

    try:
        repo.delete_digital_lock(id)
    except DigitalLockNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))
    except ResourceInUse as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))
    return {"message": "digital lock deleted successfully"}


# ---- Digital Key issuance ----

DEFAULT_KEY_VALIDITY = timedelta(hours=24)


@router.post('/keys/issue')
def issue_digital_key(
    key_data: IssueDigitalKeyRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
) -> IssueDigitalKeyResponse:
    repo = DigitalKeyRepository(db)
    lock_repo = DigitalLockRepository(db)
    user_id = get_user_id_from_token(token)
    expires_at = key_data.expires_at or (datetime.now() + DEFAULT_KEY_VALIDITY)

    try:
        owner_id = lock_repo.get_institution_owner(key_data.lock_id)
    except DigitalLockNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can issue keys for this lock')

    try:
        digital_key_id, created_at = repo.create_digital_key(
            user_id=key_data.user_id,
            digital_lock_id=key_data.lock_id,
            expiration=expires_at
        )
        return IssueDigitalKeyResponse(digital_key_id=digital_key_id, created_at=created_at)
    except DigitalLockNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))


# ---- Digital Key requests ----

@router.get('/keys/requests')
def get_key_requests(
    token: Annotated[str, Depends(verify_token)],
    status: Optional[str] = None,
    db: Database = Depends(get_database)
):
    repo = DigitalKeyRequestRepository(db)
    user_id = get_user_id_from_token(token)
    return repo.get_requests_by_owner(user_id, status)


@router.post('/keys/requests/{id}/approve')
def approve_key_request(
    id: int,
    token: Annotated[str, Depends(verify_token)],
    approve_data: Optional[ApproveDigitalKeyRequestRequest] = None,
    db: Database = Depends(get_database)
) -> ApproveDigitalKeyRequestResponse:
    request_repo = DigitalKeyRequestRepository(db)
    key_repo = DigitalKeyRepository(db)
    lock_repo = DigitalLockRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        request = request_repo.get_request(id)
    except DigitalKeyRequestNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    try:
        owner_id = lock_repo.get_institution_owner(request['digital_lock_id'])
    except DigitalLockNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can approve this request')

    if request.get('status') != 'pending':
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=f"request already {request.get('status')}"
        )

    expires_at = (approve_data.expires_at if approve_data else None) or (datetime.now() + DEFAULT_KEY_VALIDITY)

    try:
        digital_key_id, created_at = key_repo.create_digital_key(
            user_id=request['user_id'],
            digital_lock_id=request['digital_lock_id'],
            expiration=expires_at
        )
    except DigitalLockNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    request_repo.update_status(id, 'approved')

    return ApproveDigitalKeyRequestResponse(request_id=id, digital_key_id=digital_key_id, created_at=created_at)


@router.post('/keys/requests/{id}/reject')
def reject_key_request(
    id: int,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = DigitalKeyRequestRepository(db)
    lock_repo = DigitalLockRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        request = repo.get_request(id)
    except DigitalKeyRequestNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    try:
        owner_id = lock_repo.get_institution_owner(request['digital_lock_id'])
    except DigitalLockNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    if owner_id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='only the institution owner can reject this request')

    if request.get('status') != 'pending':
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=f"request already {request.get('status')}"
        )

    repo.update_status(id, 'rejected')
    return {"message": "request rejected"}
