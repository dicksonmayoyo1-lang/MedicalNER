"""
Patient routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models.schemas import User, UserUpdate
from services.patient import PatientService
from services.appointments import AppointmentService
from dependencies import get_current_active_user, require_role

router = APIRouter(prefix="/patient", tags=["patient"])


@router.get("/dashboard")
async def patient_dashboard(current_user: User = Depends(require_role("patient"))):
    """Get patient dashboard data"""
    dashboard_data = PatientService.get_patient_dashboard_data(current_user.id)
    return dashboard_data


@router.get("/records", response_model=List[dict])
async def get_patient_records(current_user: User = Depends(require_role("patient"))):
    """Get all records for the current patient"""
    records = PatientService.get_patient_records(current_user.id)
    return records


@router.get("/records/{record_id}", response_model=dict)
async def get_patient_record(
    record_id: str,
    current_user: User = Depends(require_role("patient"))
):
    """Get a specific record for the current patient"""
    record = PatientService.get_patient_record(current_user.id, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found"
        )
    return record


@router.put("/profile", response_model=User)
async def update_patient_profile(
    update_data: UserUpdate,
    current_user: User = Depends(require_role("patient"))
):
    """Update patient profile information"""
    updated_user = PatientService.update_patient_profile(current_user.id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update profile"
        )
    
    # Convert to User model
    from services.auth import AuthService
    return AuthService.get_user_by_id(current_user.id)

