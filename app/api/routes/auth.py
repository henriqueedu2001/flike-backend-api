from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.auth_models import *
from app.database.database_manager import *
from app.database.repositories import *
from app.modules.auth.jwt_token import *
from http import HTTPStatus

router = APIRouter()

security = HTTPBearer(auto_error=False)

def _validated_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]):
    if credentials is None or not validate_jwt_token(credentials.credentials):
        raise HTTPException(status_code=401, detail='Sessão inválida ou expirada.', headers={'WWW-Authenticate': 'Bearer'})
    return credentials.credentials


def verify_token(
    token: Annotated[str, Depends(_validated_token)],
    db: Database = Depends(get_database),
):
    try:
        UserRepository(db).get_user(get_user_id_from_token(token))
    except UserNotFound:
        raise HTTPException(status_code=401, detail='Sessão inválida ou expirada.', headers={'WWW-Authenticate': 'Bearer'}) from None
    return token


@router.post('/auth/user')
def auth_user(user_credentials: AuthUserRequest, db: Database = Depends(get_database)) -> AuthUserResponse:
    repo = UserRepository(db)

    email = user_credentials.email
    password = user_credentials.password

    auth_status = False

    try:
        auth_status = repo.authenticate_user(email, password)
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
def auth_token(jwt_token: Annotated[str, Body(embed=True)]) -> bool:
    valid_token = validate_jwt_token(jwt_token)
    return valid_token


@router.get('/auth/request')
def auth_request(token: Annotated[str, Depends(verify_token)]):
    return {"message": "Access granted!"}