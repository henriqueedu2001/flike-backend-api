from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user_models import *
from app.database.database_manager import *
from app.database.repositories import *
from app.modules.auth.jwt_token import get_user_id_from_token
from app.api.routes.auth import verify_token
from http import HTTPStatus

router = APIRouter()

@router.post('/user/new')
def create_user(user_data: CreateUserRequest, db: Database = Depends(get_database)) -> CreateUserResponse:
    repo = UserRepository(db)
    name = user_data.name
    email = user_data.email
    password = user_data.password

    try:
        id = repo.create_user(name, email, password)
        return CreateUserResponse(user_id=id)
    except EmailAlreadyInUse as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))


@router.get('/user/all')
def get_all_users(db: Database = Depends(get_database)):
    repo = UserRepository(db)
    users = repo.get_all_users()
    return users


@router.get('/user')
def get_user(id: int, db: Database = Depends(get_database)):
    repo = UserRepository(db)

    try:
        user = repo.get_user(id)
    except UserNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    return user


@router.get('/user/me')
def get_current_user(
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = UserRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        user = repo.get_user(user_id)
    except UserNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))

    return user


@router.put('/user/me')
def update_current_user(
    user_data: UpdateUserRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = UserRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        user = repo.update_user(user_id, name=user_data.name, email=user_data.email)
    except UserNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))
    except EmailAlreadyInUse as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))

    return user


@router.post('/user/change-password')
def change_password(
    password_data: ChangePasswordRequest,
    token: Annotated[str, Depends(verify_token)],
    db: Database = Depends(get_database)
):
    repo = UserRepository(db)
    user_id = get_user_id_from_token(token)

    try:
        repo.change_password(user_id, password_data.current_password, password_data.new_password)
    except (UserNotFound, CredentialsDontExist) as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))
    except WrongPassword:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail='current password is incorrect')

    return {"message": "password updated successfully"}