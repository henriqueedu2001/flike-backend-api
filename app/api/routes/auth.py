from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.auth_models import *
from app.database.database_manager import *
from app.database.repositories import *
from app.modules.auth.jwt_token import *
from http import HTTPStatus

router = APIRouter()

security = HTTPBearer()

def verify_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    token = credentials.credentials
    
    if not validate_jwt_token(token):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="invalid or expired token",
        )
    return token


@router.post('/auth/user')
def auth_user(user_credentials: AuthUserRequest, db: Database = Depends(get_database)) -> AuthUserResponse:
    repo = Repository(db)

    email = user_credentials.email
    password = user_credentials.password

    auth_status = False

    try:
        auth_status = repo.authenticate(email, password)
    except CredentialsDontExist:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    
    if auth_status == True:
        user = repo.get_user_from_email(email)
        user_id = user.get('id')
        jwt_token = generate_jwt_token(user_id=user_id)
        return AuthUserResponse(token=jwt_token)
    else:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


@router.post('/auth/token')
def auth_token(jwt_token: str) -> bool:
    valid_token = validate_jwt_token(jwt_token)
    return valid_token


@router.get('/auth/request')
def auth_request(token: Annotated[str, Depends(verify_token)]):
    return {"message": "Access granted!", "token_used": token}