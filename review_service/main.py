import os
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, status, Depends, Header
from pydantic import BaseModel
import motor.motor_asyncio
import jwt
from bson import ObjectId

app = FastAPI(title="Washify Review Service")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client.washify_reviews
collection = db.get_collection("reviews")

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_key_change_me_in_production")
ALGORITHM = "HS256"

# Models
class ReviewCreate(BaseModel):
    car_wash_id: str
    rating: int # 1 to 5
    comment: str

class ReviewResponse(BaseModel):
    id: str
    user_id: str
    car_wash_id: str
    rating: int
    comment: str
    created_at: str

def verify_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/reviews", response_model=ReviewResponse)
async def create_review(review: ReviewCreate, user_data: dict = Depends(verify_user)):
    if not (1 <= review.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    review_dict = {
        "user_id": user_data["id"],
        "car_wash_id": review.car_wash_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = await collection.insert_one(review_dict)
    review_dict["id"] = str(result.inserted_id)
    return review_dict

@app.get("/reviews/{car_wash_id}", response_model=List[ReviewResponse])
async def get_reviews(car_wash_id: str):
    cursor = collection.find({"car_wash_id": car_wash_id}).sort("created_at", -1)
    reviews = []
    async for document in cursor:
        document["id"] = str(document["_id"])
        reviews.append(document)
    return reviews

@app.get("/health")
def health_check():
    return {"status": "ok"}
