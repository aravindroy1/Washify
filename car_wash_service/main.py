import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status, Depends, Header
from pydantic import BaseModel
import motor.motor_asyncio
import jwt
from bson import ObjectId

app = FastAPI(title="Washify Car Wash Service")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client.washify_car_washes
collection = db.get_collection("car_washes")

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_key_change_me_in_production")
ALGORITHM = "HS256"

# Pydantic Models
class ServiceItem(BaseModel):
    name: str
    price: float
    duration_minutes: int

class CarWashBase(BaseModel):
    name: str
    location: str
    services: List[ServiceItem] = []
    slot_capacity: int = 5
    rating: float = 0.0

class CarWashCreate(CarWashBase):
    pass

class CarWashResponse(CarWashBase):
    id: str

def verify_admin(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin privileges required")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/car_washes", response_model=CarWashResponse)
async def create_car_wash(car_wash: CarWashCreate, admin_data: dict = Depends(verify_admin)):
    car_wash_dict = car_wash.dict()
    result = await collection.insert_one(car_wash_dict)
    car_wash_dict["id"] = str(result.inserted_id)
    return car_wash_dict

@app.get("/car_washes", response_model=List[CarWashResponse])
async def list_car_washes():
    cursor = collection.find({})
    car_washes = []
    async for document in cursor:
        document["id"] = str(document["_id"])
        car_washes.append(document)
    return car_washes

@app.get("/car_washes/{car_wash_id}", response_model=CarWashResponse)
async def get_car_wash(car_wash_id: str):
    car_wash = await collection.find_one({"_id": ObjectId(car_wash_id)})
    if not car_wash:
        raise HTTPException(status_code=404, detail="Car wash not found")
    car_wash["id"] = str(car_wash["_id"])
    return car_wash

@app.get("/health")
def health_check():
    return {"status": "ok"}
