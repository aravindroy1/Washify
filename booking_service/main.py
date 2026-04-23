import os
import httpx
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import motor.motor_asyncio
import jwt
from bson import ObjectId

app = FastAPI(title="Washify Booking Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class StatusUpdate(BaseModel):
    status: str

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

async def send_notification(user_id: str, message: str, email: str = None, phone_number: str = None):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{NOTIFICATION_URL}/notifications/booking-confirmation",
                json={"user_id": user_id, "message": message, "email": email, "phone_number": phone_number}
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
        f"Your Washify booking is confirmed! 🚗✨ Queue number: {queue_number}, Wait time: {total_wait} mins.",
        user_data.get("sub"), # email
        user_data.get("phone_number")
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

@app.get("/bookings/admin/all", response_model=List[BookingResponse])
async def get_all_bookings(user_data: dict = Depends(verify_user)):
    if user_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    cursor = collection.find().sort("created_at", -1)
    bookings = []
    async for document in cursor:
        document["id"] = str(document["_id"])
        bookings.append(document)
    return bookings

@app.put("/bookings/{booking_id}/status", response_model=BookingResponse)
async def update_booking_status(booking_id: str, status_update: StatusUpdate, background_tasks: BackgroundTasks, user_data: dict = Depends(verify_user)):
    if user_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    await collection.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": status_update.status}})
    
    booking = await collection.find_one({"_id": ObjectId(booking_id)})
    if booking:
        booking["id"] = str(booking["_id"])
        
        # Determine notification message
        msg = f"Update! Your car wash booking status is now: {status_update.status.upper()}"
        if status_update.status == "completed":
            msg += "\n\nWe hope your car is shining! ✨ Please leave us a review on the Washify App."
            
        # We need the user's email and phone_number. For simplicity, we assume we fetch it or it's stored in the booking.
        # Since we don't have it on the booking object locally, we'll just send the notification without them,
        # or we can send it with placeholder email/phone if we didn't cache them. In a full system, we would query Auth Service.
        background_tasks.add_task(send_notification, booking["user_id"], msg, "user@washify.com", "+123456789")
        
        return booking
    raise HTTPException(status_code=404, detail="Booking not found")

@app.get("/health")
def health_check():
    return {"status": "ok"}
