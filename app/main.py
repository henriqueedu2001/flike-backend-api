from fastapi import FastAPI
from app.api.routes import health_check, auth, user, institution, building, room, digital_lock, digital_key
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_check.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(institution.router)
app.include_router(building.router)
app.include_router(room.router)
app.include_router(digital_lock.router)
app.include_router(digital_key.router)