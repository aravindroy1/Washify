import os
import random
from datetime import datetime
from typing import List
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import motor.motor_asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

app = FastAPI(title="Washify Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client.washify_notifications
collection = db.get_collection("notifications")

# Scheduler for smart background tasks
scheduler = AsyncIOScheduler()

class NotificationRequest(BaseModel):
    user_id: str
    message: str

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    message: str
    type: str # 'booking', 'queue', 'weather', 'promotion'
    created_at: str

@app.post("/notifications/booking-confirmation", response_model=NotificationResponse)
async def booking_confirmation(req: NotificationRequest):
    notif_dict = {
        "user_id": req.user_id,
        "message": req.message,
        "type": "booking",
        "created_at": datetime.utcnow().isoformat()
    }
    result = await collection.insert_one(notif_dict)
    notif_dict["id"] = str(result.inserted_id)
    
    # In a real app, send FCM / Email / SMS here
    print(f"[NOTIFICATION SENT] To {req.user_id}: {req.message}")
    return notif_dict

@app.post("/notifications/weather-trigger")
async def trigger_weather_notifications(background_tasks: BackgroundTasks):
    """
    Manually trigger the weather-based notification for testing purposes.
    """
    # Logic: If today = rainy AND tomorrow = clear -> Send notification
    is_rainy_today = True # Mocking weather API
    is_clear_tomorrow = True
    
    if is_rainy_today and is_clear_tomorrow:
        msg = "It rained today 🌧️ — your car might be dirty! Book a wash tomorrow and bring back the shine 🚗✨"
        
        # We would typically fetch all active users from the Auth service or Users DB.
        # For this demo, we'll just log that we sent a blast.
        background_tasks.add_task(send_blast_notification, msg, "weather")
        
        return {"message": msg, "users_notified": 120} # 120 is a mock number
    return {"message": "No optimal weather condition met for promotions."}

async def send_blast_notification(message: str, notif_type: str):
    # Mocking a bulk insert and blast
    print(f"[BLAST NOTIFICATION] Type: {notif_type} | Message: {message}")

async def smart_weather_job():
    # This runs periodically via cron
    print("Running background smart weather check...")
    # Add real logic calling a Weather API here.
    pass

@app.on_event("startup")
async def startup_event():
    # Schedule the weather check every 24 hours (for example, at 6 PM)
    scheduler.add_job(smart_weather_job, 'cron', hour=18, minute=0)
    scheduler.start()

@app.get("/health")
def health_check():
    return {"status": "ok"}
