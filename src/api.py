from fastapi import FastAPI
from pydantic import BaseModel
from typing import *

app = FastAPI()

@app.get('/')
def read_root():
    return {'message': 'flike!'}