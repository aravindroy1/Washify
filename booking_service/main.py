import os
import httpx
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status, Depends, Header, BackgroundTasks
from pydantic import BaseModel
import motor.motor_asyncio
import jwt
from bson import ObjectId

app = FastAPI(title="Washify Booking Service")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client.washify_bookings
collection = db.get_collection("bookings")

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_key_change_me_in_production")
ALGORITHM = "HS256"
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://localhost:8005")

# Models
class BookingCreate(BaseModel):
    car_wash_id: str
    service_name: str
    duration_minutes: int

class BookingResponse(BaseModel):
    id: str
    user_id: str
    car_wash_id: str
    service_name: str
    status: str
    queue_number: int
    estimated_wait_time_minutes: int
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

async def send_notification(user_id: str, message: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{NOTIFICATION_URL}/notifications/booking-confirmation",
                json={"user_id": user_id, "message": message}
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")

@app.post("/bookings", response_model=BookingResponse)
async def create_booking(
    booking: BookingCreate, 
    background_tasks: BackgroundTasks,
    user_data: dict = Depends(verify_user)
):
    user_id = user_data["id"]
    
    # Calculate queue number and wait time
    # For simplicity, we just count existing pending/in-progress bookings for this car wash
    pipeline = [
        {"$match": {"car_wash_id": booking.car_wash_id, "status": {"$in": ["pending", "in-progress"]}}},
        {"$group": {"_id": None, "total_wait": {"$sum": "$duration_minutes"}, "count": {"$sum": 1}}}
    ]
    cursor = collection.aggregate(pipeline)
    aggr_result = await cursor.to_list(length=1)
    
    total_wait = 0
    queue_number = 1
    if aggr_result:
        total_wait = aggr_result[0]["total_wait"]
        queue_number = aggr_result[0]["count"] + 1

    booking_dict = {
        "user_id": user_id,
        "car_wash_id": booking.car_wash_id,
        "service_name": booking.service_name,
        "duration_minutes": booking.duration_minutes,
        "status": "pending",
        "queue_number": queue_number,
        "estimated_wait_time_minutes": total_wait,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = await collection.insert_one(booking_dict)
    booking_dict["id"] = str(result.inserted_id)
    
    background_tasks.add_task(
        send_notification, 
        user_id, 
        f"Your Washify booking is confirmed! 🚗✨ Queue number: {queue_number}, Wait time: {total_wait} mins."
    )
    
    return booking_dict

@app.get("/bookings/my", response_model=List[BookingResponse])
async def get_my_bookings(user_data: dict = Depends(verify_user)):
    user_id = user_data["id"]
    cursor = collection.find({"user_id": user_id}).sort("created_at", -1)
    bookings = []
    async for document in cursor:
        document["id"] = str(document["_id"])
        bookings.append(document)
    return bookings

@app.get("/health")
def health_check():
    return {"status": "ok"}
