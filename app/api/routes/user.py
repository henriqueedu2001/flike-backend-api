from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user_models import *
from app.database.database_manager import *
from app.database.repositories import *
from http import HTTPStatus

router = APIRouter()

@router.post('/user/new')
def create_user(user_data: CreateUserRequest, db: Database = Depends(get_database)) -> CreateUserResponse:
    repo = Repository(db)
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
    repo = Repository(db)
    users = repo.get_all_users()
    return users


@router.get('/user')
def get_all_users(id: int, db: Database = Depends(get_database)):
    repo = Repository(db)

    try:
        user = repo.get_user(id)
    except UserNotFound as error:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(error))
    
    return user