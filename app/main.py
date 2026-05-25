from fastapi import FastAPI
from app.api.routes import health_check, binary_handler

app = FastAPI()

app.include_router(health_check.router)
app.include_router(binary_handler.router)