from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.building_models import *
from http import HTTPStatus

router = APIRouter()

@router.get('/building/all')
def get_all_institution(db: Database = Depends(get_database)):
    repo = BuildingRepository(db)
    buildings = repo.get_all_buildings()
    return buildings


@router.post('/building/new')
def create_institution(building_data: CreateBuildingRequest, db: Database = Depends(get_database)) -> CreateBuildingResponse:
    repo = BuildingRepository(db)

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
    except EmailAlreadyInUse as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))