from fastapi import FastAPI
from app.api.routes import health_check, auth, user, institution, building, room, digital_lock

app = FastAPI()

app.include_router(health_check.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(institution.router)
app.include_router(building.router)
app.include_router(room.router)
app.include_router(digital_lock.router)