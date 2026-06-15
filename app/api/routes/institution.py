from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.institution_models import *
from http import HTTPStatus

router = APIRouter()

@router.get('/institution/all')
def get_all_institution(db: Database = Depends(get_database)):
    repo = InstitutionRepository(db)
    institutions = repo.get_all_institutions()
    return institutions


@router.post('/institution/new')
def create_institution(user_id: int, building_name: str, db: Database = Depends(get_database)):
    repo = InstitutionRepository(db)

    try:
        institution_id, created_at = repo.create_institution(user_id, building_name)
        return CreateInstitutionResponse(institution_id=institution_id, created_at=created_at)
    except EmailAlreadyInUse as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))