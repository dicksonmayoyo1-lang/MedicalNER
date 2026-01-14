"""
Pydantic models/schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List, Any
from datetime import datetime


# ==================== Auth Models ====================
class User(BaseModel):
    id: str
    username: str
    email: str
    role: str  # "doctor", "patient", "admin"
    full_name: Optional[str] = None
    created_at: str
    is_active: bool = True


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "patient"
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


# ==================== Medical Record Models ====================
class Entity(BaseModel):
    text: str
    start: int
    end: int
    entity_type: str
    icd_code: Optional[str] = None
    confidence: float
    value: Optional[str] = None
    unit: Optional[str] = None
    normal_range: Optional[str] = None


class CombinedNERResponse(BaseModel):
    metadata: Optional[Dict[str, Any]] = None
    text: str
    diseases: List[Entity]
    lab_results: List[Entity]
    summary: Optional[Dict[str, str]] = None


class TextRequest(BaseModel):
    text: str
    icd_map: bool = False


class StoredRecord(BaseModel):
    id: str
    patient_id: str
    original_filename: str
    upload_timestamp: str
    diseases_count: int
    labs_count: int
    summary_preview: str


class RecordDetail(StoredRecord):
    extracted_text: str
    diseases: List[Entity]
    lab_results: List[Entity]
    summary: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchQuery(BaseModel):
    disease_name: Optional[str] = None
    lab_test: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 50


# ==================== Analytics Models ====================
class AnalyticsSummary(BaseModel):
    total_records: int
    total_diseases: int
    total_labs: int
    avg_diseases_per_record: float
    avg_labs_per_record: float
    date_range: Optional[Dict[str, str]] = None


class DiseaseFrequency(BaseModel):
    disease_name: str
    count: int
    percentage: float


class LabFrequency(BaseModel):
    lab_name: str
    count: int
    percentage: float


class TimeSeriesPoint(BaseModel):
    date: str
    count: int


class AnalyticsResponse(BaseModel):
    summary: AnalyticsSummary
    top_diseases: List[DiseaseFrequency]
    top_labs: List[LabFrequency]
    upload_trend: List[TimeSeriesPoint]
    disease_trend: Optional[List[TimeSeriesPoint]] = None


# ==================== Screening Models ====================
class ScreeningRule(BaseModel):
    id: str
    name: str
    description: str
    conditions: List[Dict[str, Any]]
    risk_level: str  # LOW, MEDIUM, HIGH
    recommendation: str


class ScreeningResult(BaseModel):
    record_id: str
    patient_id: str
    original_filename: str
    screening_date: str
    risk_level: str
    triggered_rules: List[Dict[str, Any]]
    recommendations: List[str]
    diseases_found: List[str]
    labs_found: List[str]


class ScreeningRequest(BaseModel):
    record_id: Optional[str] = None
    patient_id: Optional[str] = None
    run_all: bool = False


# ==================== Appointment Models ====================
class AppointmentCreate(BaseModel):
    type: str  # consultation, follow-up, checkup, urgent
    preferred_date: str
    preferred_time: str
    reason: str
    patient_id: Optional[str] = None


class AppointmentUpdate(BaseModel):
    status: Optional[str] = None  # pending, confirmed, cancelled, completed
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    doctor_notes: Optional[str] = None


class AppointmentConfirm(BaseModel):
    scheduled_date: str
    scheduled_time: str
    doctor_notes: Optional[str] = None


class AppointmentCancel(BaseModel):
    reason: Optional[str] = None


class Appointment(BaseModel):
    id: str
    patient_id: str
    type: str
    preferred_date: str
    preferred_time: str
    reason: str
    status: str
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    doctor_id: Optional[str] = None
    doctor_notes: Optional[str] = None
    created_at: str
    updated_at: str


# ==================== Medication Models ====================
class MedicationCreate(BaseModel):
    name: str
    dosage: str
    frequency: str
    start_date: str
    end_date: Optional[str] = None
    prescribed_by: Optional[str] = None
    notes: Optional[str] = None


class MedicationUpdate(BaseModel):
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class Medication(BaseModel):
    id: str
    patient_id: str
    name: str
    dosage: str
    frequency: str
    start_date: str
    end_date: Optional[str] = None
    prescribed_by: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    created_at: str
    updated_at: str

