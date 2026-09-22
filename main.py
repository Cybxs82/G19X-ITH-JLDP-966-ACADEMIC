from fastapi import FastAPI
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    edad: int

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.post("/items/")
async def create_item(item: Item):
    return {'item': item, 'name': item.name, 'edad': item.edad}