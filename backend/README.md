# Medical RAG Backend

## Project Structure

The backend has been refactored with proper separation of concerns:

```
backend/
├── main.py                 # Main FastAPI application entry point
├── rag.py                  # Legacy file with ML processing (to be refactored)
├── models/
│   └── schemas.py          # Pydantic models for request/response validation
├── database/
│   ├── connection.py       # MongoDB connection management
│   └── models.py           # MongoDB document models (UserModel, AppointmentModel, etc.)
├── services/
│   ├── auth.py             # Authentication service with MongoDB
│   ├── patient.py           # Patient-related operations
│   ├── appointments.py      # Appointment management
│   └── medications.py       # Medication management
├── routes/
│   ├── auth.py             # Authentication routes
│   ├── patient.py           # Patient routes
│   ├── appointments.py      # Appointment routes
│   └── medications.py       # Medication routes
└── dependencies.py         # FastAPI dependencies (auth middleware)
```

## Features

### 1. Separation of Concerns
- **Models**: Pydantic schemas for data validation
- **Database**: MongoDB connection and document models
- **Services**: Business logic layer
- **Routes**: API endpoints
- **Dependencies**: Reusable FastAPI dependencies

### 2. MongoDB Authentication
- Users are now stored in MongoDB instead of hardcoded dictionary
- Password hashing using bcrypt
- JWT token-based authentication
- Default users (doctor1, patient1) are auto-created on startup

### 3. New Patient Modules

#### Appointments
- `POST /appointments` - Create appointment request
- `GET /appointments` - Get patient's appointments
- `GET /appointments/{id}` - Get specific appointment
- `PUT /appointments/{id}` - Update appointment
- `DELETE /appointments/{id}` - Delete appointment

#### Medications
- `POST /medications` - Add medication
- `GET /medications` - Get patient's medications
- `GET /medications/{id}` - Get specific medication
- `PUT /medications/{id}` - Update medication
- `DELETE /medications/{id}` - Delete medication

#### Patient Profile
- `GET /patient/dashboard` - Get dashboard data
- `GET /patient/records` - Get patient's medical records
- `GET /patient/records/{id}` - Get specific record
- `PUT /patient/profile` - Update profile information

## Running the Application

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export MONGO_DB_URI="your_mongodb_connection_string"
export JWT_SECRET_KEY="your_secret_key"
export GOOGLE_API_KEY="your_gemini_api_key"
```

3. Run the application:
```bash
# Using the new main.py
uvicorn main:app --reload

# Or using the legacy rag.py (still works)
uvicorn rag:app --reload
```

## Database Collections

- `users` - User accounts
- `patient_records` - Medical records
- `appointments` - Appointment requests
- `medications` - Patient medications
- `screening_results` - Screening analysis results

## Authentication

All protected routes require a JWT token in the Authorization header:
```
Authorization: Bearer <token>
```

Tokens are obtained via `/auth/login` endpoint.

## Migration Notes

- The old hardcoded `users_db` dictionary has been replaced with MongoDB
- Default users are automatically created on first startup
- Existing endpoints in `rag.py` still work but now use MongoDB auth when available
- New endpoints use the refactored structure with proper separation of concerns

