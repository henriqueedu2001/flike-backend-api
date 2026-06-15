from fastapi import FastAPI
from app.api.routes import health_check, auth, user, institution, building

app = FastAPI()

app.include_router(health_check.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(institution.router)
app.include_router(building.router)