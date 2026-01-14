"""
Doctor routes for patient management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from models.schemas import User
from dependencies import require_role
from services.auth import AuthService
from services.patient import PatientService

router = APIRouter(prefix="/doctor", tags=["doctor"])


@router.get("/patients", response_model=List[User])
async def get_all_patients(
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: User = Depends(require_role("doctor"))
):
    """Get all patients (for doctors to manage)"""
    patients = AuthService.get_all_users(role="patient", search=search)
    return patients


@router.get("/patients/{patient_id}", response_model=User)
async def get_patient_details(
    patient_id: str,
    current_user: User = Depends(require_role("doctor"))
):
    """Get details of a specific patient"""
    patient = AuthService.get_user_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    if patient.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a patient"
        )
    return patient


@router.get("/patients/{patient_id}/records", response_model=List[dict])
async def get_patient_records(
    patient_id: str,
    current_user: User = Depends(require_role("doctor"))
):
    """Get all records for a specific patient (doctor view)"""
    # Verify patient exists and is actually a patient
    patient = AuthService.get_user_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    if patient.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a patient"
        )
    
    records = PatientService.get_patient_records(patient_id)
    return records


@router.get("/patients/{patient_id}/records/{record_id}", response_model=dict)
async def get_patient_record(
    patient_id: str,
    record_id: str,
    current_user: User = Depends(require_role("doctor"))
):
    """Get a specific record for a patient (doctor view)"""
    # Verify patient exists and is actually a patient
    patient = AuthService.get_user_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    if patient.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a patient"
        )
    
    record = PatientService.get_patient_record(patient_id, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found"
        )
    return record

