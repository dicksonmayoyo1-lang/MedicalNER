"""
Doctor appointments routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import List, Optional
from pydantic import BaseModel
from models.schemas import Appointment, AppointmentConfirm, AppointmentCancel, User
from services.appointments import AppointmentService
from services.auth import AuthService
from dependencies import get_current_active_user, require_role


class CompleteRequest(BaseModel):
    notes: Optional[str] = None

router = APIRouter(prefix="/doctor/appointments", tags=["doctor-appointments"])


@router.get("", response_model=List[Appointment])
async def get_doctor_appointments(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_role("doctor"))
):
    """Get all appointments for the current doctor"""
    appointments = AppointmentService.get_doctor_appointments(
        current_user.id,
        status=status_filter,
        limit=100
    )
    return appointments


@router.get("/all", response_model=List[Appointment])
async def get_all_appointments(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_role("doctor"))
):
    """Get all appointments (for doctors to see unassigned ones)"""
    appointments = AppointmentService.get_all_appointments(
        status=status_filter,
        limit=100
    )
    return appointments


@router.get("/pending", response_model=List[Appointment])
async def get_pending_appointments(
    current_user: User = Depends(require_role("doctor"))
):
    """Get all pending appointments"""
    appointments = AppointmentService.get_all_appointments(status="pending", limit=50)
    return appointments


@router.get("/{appointment_id}", response_model=Appointment)
async def get_appointment(
    appointment_id: str,
    current_user: User = Depends(require_role("doctor"))
):
    """Get a specific appointment"""
    appointment = AppointmentService.get_appointment_by_id(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.post("/{appointment_id}/confirm", response_model=Appointment)
async def confirm_appointment(
    appointment_id: str,
    confirm_data: AppointmentConfirm,
    current_user: User = Depends(require_role("doctor"))
):
    """Confirm and schedule an appointment"""
    appointment = AppointmentService.confirm_appointment(
        appointment_id,
        current_user.id,
        confirm_data.scheduled_date,
        confirm_data.scheduled_time,
        confirm_data.doctor_notes
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to confirm appointment. It may already be confirmed or cancelled."
        )
    return appointment


@router.post("/{appointment_id}/cancel", response_model=Appointment)
async def cancel_appointment(
    appointment_id: str,
    cancel_data: AppointmentCancel,
    current_user: User = Depends(require_role("doctor"))
):
    """Cancel an appointment"""
    appointment = AppointmentService.cancel_appointment(
        appointment_id,
        current_user.id,
        cancel_data.reason
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel appointment. It may already be cancelled or completed."
        )
    return appointment


@router.post("/{appointment_id}/complete", response_model=Appointment)
async def complete_appointment(
    appointment_id: str,
    request: CompleteRequest = Body(None),
    current_user: User = Depends(require_role("doctor"))
):
    """Mark an appointment as completed"""
    notes = request.notes if request else None
    
    appointment = AppointmentService.complete_appointment(
        appointment_id,
        current_user.id,
        notes
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to complete appointment. It may not be confirmed or you may not be the assigned doctor."
        )
    return appointment


@router.put("/{appointment_id}", response_model=Appointment)
async def update_appointment(
    appointment_id: str,
    update_data: dict,
    current_user: User = Depends(require_role("doctor"))
):
    """Update appointment details (doctor can update notes, reschedule, etc.)"""
    from models.schemas import AppointmentUpdate
    
    update_schema = AppointmentUpdate(**update_data)
    appointment_doc = AppointmentService.get_appointment_by_id(appointment_id)
    if not appointment_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Verify doctor ownership or allow if unassigned
    if appointment_doc.doctor_id and appointment_doc.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this appointment"
        )
    
    appointment = AppointmentService.update_appointment(
        appointment_id,
        appointment_doc.patient_id,
        update_schema
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update appointment"
        )
    return appointment

