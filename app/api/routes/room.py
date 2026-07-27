from fastapi import APIRouter, Depends
from app.database.database_manager import *
from app.database.repositories import *
from app.schemas.room_models import *

router = APIRouter()

@router.get('/room/all')
def get_all_institution(db: Database = Depends(get_database)):
    repo = RoomRepository(db)
    rooms = repo.get_all_rooms()
    return rooms


@router.get('/rooms/search')
def search_rooms(q: str, building_id: Optional[int] = None, db: Database = Depends(get_database)):
    repo = RoomRepository(db)
    return repo.search_rooms(q, building_id)