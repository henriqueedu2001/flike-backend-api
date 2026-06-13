from fastapi import APIRouter
from app.schemas.auth_models import *

router = APIRouter()

@router.get('/auth/user')
def auth_user(user_credentials: AuthUserRequest):
    return