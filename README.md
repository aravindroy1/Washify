# Washify - Skip the Queue, Get the Shine 🚗✨

Washify is a full-stack car wash booking application based on a microservices architecture. It allows users to browse car washes, book slots with a queue management system, and receive smart, weather-based notifications.

## Project Architecture
- **Backend:** Python (FastAPI)
- **Database:** MongoDB
- **Architecture:** 5 Microservices (Auth, Car Wash, Booking, Review, Notification)
- **API Type:** REST
- **Authentication:** JWT (Roles: User, Admin)

## Microservices
1. **Auth Service (`:8001`)**: Handles user registration, login, and JWT token generation. Roles include `user` and `admin`.
2. **Car Wash Service (`:8002`)**: Manages car wash profiles, services, and availability. Admin restricted for modifications.
3. **Booking Service (`:8003`)**: Core engine. Manages booking slots, calculates waiting time, handles queue numbers.
4. **Review Service (`:8004`)**: Handles ratings and reviews for completed bookings.
5. **Notification Service (`:8005`)**: Real-time notifications for booking confirmations, queue reminders, and smart weather-based promotions.

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Python 3.9+ (if running locally without Docker)

### Run with Docker Compose
1. Clone the repository or navigate to the project directory:
   ```bash
   cd Washify
   ```
2. Build and start all services using Docker Compose:
   ```bash
   docker-compose up --build -d
   ```
3. The services will be available at the following ports:
   - MongoDB: `localhost:27017`
   - Auth Service: `http://localhost:8001`
   - Car Wash Service: `http://localhost:8002`
   - Booking Service: `http://localhost:8003`
   - Review Service: `http://localhost:8004`
   - Notification Service: `http://localhost:8005`

Each FastAPI service provides interactive Swagger documentation at `http://localhost:<PORT>/docs`.

## Sample API Responses

### 1. Auth Service - Login
**POST** `http://localhost:8001/login`
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "user": {
    "id": "64b0f1...",
    "email": "user@washify.com",
    "role": "user"
  }
}
```

### 2. Car Wash Service - List Car Washes
**GET** `http://localhost:8002/car_washes`
```json
[
  {
    "id": "64b0f2...",
    "name": "Sparkle Auto Wash",
    "location": "Downtown",
    "rating": 4.8,
    "services": [
      {"name": "Exterior Wash", "price": 15, "duration_minutes": 20},
      {"name": "Full Detail", "price": 50, "duration_minutes": 60}
    ]
  }
]
```

### 3. Booking Service - Create Booking
**POST** `http://localhost:8003/bookings`
```json
{
  "id": "64b0f3...",
  "user_id": "64b0f1...",
  "car_wash_id": "64b0f2...",
  "service_name": "Full Detail",
  "status": "pending",
  "queue_number": 5,
  "estimated_wait_time_minutes": 45
}
```

### 4. Notification Service - Trigger Smart Weather Notification
**POST** `http://localhost:8005/notifications/weather-trigger`
```json
{
  "message": "It rained today 🌧️ — your car might be dirty! Book a wash tomorrow and bring back the shine 🚗✨",
  "users_notified": 120
}
```

## Smart Weather Notifications Idea
The **Notification Service** uses a background scheduler (e.g., `APScheduler`) to fetch weather data. If it detects rain today and clear skies tomorrow, it dispatches push notifications (or mock email/SMS logs) to all active users reminding them to get a wash.
