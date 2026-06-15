from fastapi import APIRouter, Depends, HTTPException
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.room_models import *
from http import HTTPStatus

router = APIRouter()

@router.get('/room/all')
def get_all_institution(db: Database = Depends(get_database)):
    repo = RoomRepository(db)
    rooms = repo.get_all_rooms()
    return rooms


@router.post('/room/new')
def create_room(room_data: CreateRoomRequest, db: Database = Depends(get_database)) -> CreateRoomResponse:
    repo = RoomRepository(db)

    try:
        room_id, created_at = repo.create_room(
            building_id=room_data.building_id,
            name=room_data.name,
            number=room_data.number
        )
        
        return CreateRoomResponse(room_id=room_id, created_at=created_at)
    except Exception as error:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(error))