import os
from fastapi.responses import JSONResponse
from mysql.connector import Error as DatabaseError
from fastapi import FastAPI
from app.api.routes import health_check, auth, user, institution, building, room, digital_lock, digital_key, admin
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",") if origin.strip()],
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
app.include_router(admin.router)

@app.exception_handler(DatabaseError)
async def database_error_handler(request, error):
    # Driver messages can contain SQL values. Never serialize them to API clients.
    return JSONResponse(status_code=503, content={"detail": "Banco de dados indisponível. Tente novamente."})
