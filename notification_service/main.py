import os
import random
from datetime import datetime
from typing import List
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import motor.motor_asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import smtplib
from email.mime.text import MIMEText

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

# Email Config
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

def send_real_email(to_email, subject, body):
    if not SMTP_USER or not SMTP_PASS or SMTP_USER == "your_email@gmail.com":
        print(f"[SIMULATED EMAIL] To: {to_email}\nSubject: {subject}\nBody: {body}")
        return
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"[REAL EMAIL SENT SUCCESS] To: {to_email}")
    except Exception as e:
        print(f"[REAL EMAIL ERROR] Failed to send email: {e}")

# Scheduler for smart background tasks
scheduler = AsyncIOScheduler()

class NotificationRequest(BaseModel):
    user_id: str
    email: str = None
    phone_number: str = None
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
    
    # Process Real/Simulated Email
    if req.email:
        send_real_email(req.email, "Washify Update 🚗✨", req.message)
        
    # Process SMS (Twilio requires account, so we simulate in console for now)
    if req.phone_number:
        print(f"\n[SMS DISPATCHED] To: {req.phone_number} | Msg: {req.message}\n")
    
    return notif_dict

@app.get("/notifications/my", response_model=List[NotificationResponse])
async def get_my_notifications(user_id: str):
    cursor = collection.find({"user_id": user_id}).sort("created_at", -1)
    notifs = []
    async for document in cursor:
        document["id"] = str(document["_id"])
        notifs.append(document)
    return notifs

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
