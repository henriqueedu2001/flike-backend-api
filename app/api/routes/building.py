from fastapi import APIRouter, Depends
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.building_models import *

router = APIRouter()

@router.get('/building/all')
def get_all_institution(db: Database = Depends(get_database)):
    repo = BuildingRepository(db)
    buildings = repo.get_all_buildings()
    return buildings


@router.get('/buildings/search')
def search_buildings(q: str, institution_id: Optional[int] = None, db: Database = Depends(get_database)):
    repo = BuildingRepository(db)
    return repo.search_buildings(q, institution_id)