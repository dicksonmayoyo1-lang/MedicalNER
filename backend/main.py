"""
Main FastAPI application
"""
import time
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Import database connection to initialize
from database.connection import get_database
from services.auth import AuthService

# Import routes
from routes import auth, patient, appointments, medications

load_dotenv()

# Record import (service start) time
IMPORT_TIME_EPOCH = time.time()
IMPORT_TIME_ISO = datetime.utcfromtimestamp(IMPORT_TIME_EPOCH).isoformat() + "Z"

# Create FastAPI app
app = FastAPI(
    title="Medical RAG API",
    description="Medical Document Analysis and Patient Management API",
    version="1.0.0"
)

# CORS middleware
origins = ["http://localhost", "http://127.0.0.1:5500", "http://localhost:5500", "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database connection
@app.on_event("startup")
async def startup_event():
    """Initialize database and default users on startup"""
    db = get_database()
    if db is not None:
        print("✅ Database initialized")
        # Initialize default users
        AuthService.initialize_default_users()
    else:
        print("⚠️ Database not available - some features will be disabled")


# Include routers
app.include_router(auth.router)
app.include_router(patient.router)
app.include_router(appointments.router)
app.include_router(medications.router)

# Import doctor routes
try:
    from routes import doctor
    app.include_router(doctor.router)
    print("✅ Loaded doctor routes")
except ImportError as e:
    print(f"⚠️ Warning: Could not import doctor routes: {e}")

# Import doctor appointments routes
try:
    from routes import doctor_appointments
    app.include_router(doctor_appointments.router)
    print("✅ Loaded doctor appointments routes")
except ImportError as e:
    print(f"⚠️ Warning: Could not import doctor appointments routes: {e}")

# Import doctor medications routes
try:
    from routes import doctor_medications
    app.include_router(doctor_medications.router)
    print("✅ Loaded doctor medications routes")
except ImportError as e:
    print(f"⚠️ Warning: Could not import doctor medications routes: {e}")

# Import existing routes from rag.py (for backward compatibility)
# These will be refactored later but kept for now
try:
    # Import rag module to initialize ML models
    import rag
    
    # Add existing routes from rag.py
    app.add_api_route("/predict", rag.predict_combined_rag, methods=["POST"], tags=["ml"])
    app.add_api_route("/predict_pdf", rag.predict_combined_pdf, methods=["POST"], tags=["ml"])
    app.add_api_route("/predict_multiple_pdfs", rag.predict_multiple_pdfs, methods=["POST"], tags=["ml"])
    app.add_api_route("/predict_multiple_pdfs_summary", rag.predict_multiple_pdfs_consolidated, methods=["POST"], tags=["ml"])
    
    app.add_api_route("/records/stats", rag.get_storage_stats, methods=["GET"], tags=["records"])
    app.add_api_route("/records/search", rag.search_records, methods=["POST"], tags=["records"])
    app.add_api_route("/records", rag.get_all_records, methods=["GET"], tags=["records"])
    app.add_api_route("/records/{record_id}", rag.get_record, methods=["GET"], tags=["records"])
    
    app.add_api_route("/analytics/summary", rag.get_analytics_summary, methods=["GET"], tags=["analytics"])
    app.add_api_route("/analytics/top_entities", rag.get_top_entities, methods=["GET"], tags=["analytics"])
    app.add_api_route("/analytics/trends", rag.get_analytics_trends, methods=["GET"], tags=["analytics"])
    app.add_api_route("/analytics/outbreak_detection", rag.get_outbreak_detection, methods=["GET"], tags=["analytics"])
    
    app.add_api_route("/screening/rules", rag.get_screening_rules, methods=["GET"], tags=["screening"])
    app.add_api_route("/screening/analyze", rag.analyze_screening, methods=["POST"], tags=["screening"])
    app.add_api_route("/screening/analyze_record/{record_id}", rag.analyze_single_record, methods=["POST"], tags=["screening"])
    app.add_api_route("/screening/high_risk", rag.get_high_risk_records, methods=["GET"], tags=["screening"])
    
    app.add_api_route("/doctor/dashboard", rag.doctor_dashboard, methods=["GET"], tags=["doctor"])
    
    print("✅ Loaded ML processing and existing routes from rag.py")
    
except ImportError as e:
    print(f"⚠️ Warning: Could not import routes from rag.py: {e}")
    print("ML processing endpoints may not be available")
except Exception as e:
    print(f"⚠️ Warning: Error loading routes from rag.py: {e}")
    print("Some endpoints may not be available")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Medical RAG API running!",
        "service_start_time_iso": IMPORT_TIME_ISO,
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db = get_database()
    return {
        "status": "healthy",
        "database": "connected" if db is not None else "disconnected",
        "service_start_time_iso": IMPORT_TIME_ISO
    }

