from fastapi import APIRouter, Depends
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.institution_models import *

router = APIRouter()

@router.get('/institution/all')
def get_all_institution(db: Database = Depends(get_database)):
    repo = InstitutionRepository(db)
    institutions = repo.get_all_institutions()
    return institutions


@router.get('/institutions/search')
def search_institutions(q: str, db: Database = Depends(get_database)):
    repo = InstitutionRepository(db)
    return repo.search_institutions(q)