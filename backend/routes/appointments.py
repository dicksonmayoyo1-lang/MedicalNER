"""
Appointments routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models.schemas import Appointment, AppointmentCreate, AppointmentUpdate, User
from services.appointments import AppointmentService
from dependencies import get_current_active_user, require_role

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=Appointment, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(require_role("patient"))
):
    """Create a new appointment request"""
    appointment = AppointmentService.create_appointment(current_user.id, appointment_data)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create appointment"
        )
    return appointment


@router.get("", response_model=List[Appointment])
async def get_patient_appointments(
    current_user: User = Depends(require_role("patient"))
):
    """Get all appointments for the current patient"""
    appointments = AppointmentService.get_patient_appointments(current_user.id)
    return appointments


@router.get("/{appointment_id}", response_model=Appointment)
async def get_appointment(
    appointment_id: str,
    current_user: User = Depends(require_role("patient"))
):
    """Get a specific appointment"""
    appointment = AppointmentService.get_appointment_by_id(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Verify ownership
    if appointment.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this appointment"
        )
    
    return appointment


@router.put("/{appointment_id}", response_model=Appointment)
async def update_appointment(
    appointment_id: str,
    update_data: AppointmentUpdate,
    current_user: User = Depends(require_role("patient"))
):
    """Update an appointment"""
    appointment = AppointmentService.update_appointment(
        appointment_id,
        current_user.id,
        update_data
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or not authorized"
        )
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: str,
    current_user: User = Depends(require_role("patient"))
):
    """Delete an appointment"""
    success = AppointmentService.delete_appointment(appointment_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or not authorized"
        )
    return None

