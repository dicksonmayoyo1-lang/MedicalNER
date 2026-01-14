"""
Medications routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models.schemas import Medication, MedicationCreate, MedicationUpdate, User
from services.medications import MedicationService
from dependencies import get_current_active_user, require_role

router = APIRouter(prefix="/medications", tags=["medications"])


@router.post("", response_model=Medication, status_code=status.HTTP_201_CREATED)
async def create_medication(
    medication_data: MedicationCreate,
    current_user: User = Depends(require_role("patient"))
):
    """Create a new medication record"""
    medication = MedicationService.create_medication(current_user.id, medication_data)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create medication"
        )
    return medication


@router.get("", response_model=List[Medication])
async def get_patient_medications(
    active_only: bool = False,
    current_user: User = Depends(require_role("patient"))
):
    """Get all medications for the current patient"""
    medications = MedicationService.get_patient_medications(current_user.id, active_only)
    return medications


@router.get("/{medication_id}", response_model=Medication)
async def get_medication(
    medication_id: str,
    current_user: User = Depends(require_role("patient"))
):
    """Get a specific medication"""
    medication = MedicationService.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )
    
    # Verify ownership
    if medication.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this medication"
        )
    
    return medication


@router.put("/{medication_id}", response_model=Medication)
async def update_medication(
    medication_id: str,
    update_data: MedicationUpdate,
    current_user: User = Depends(require_role("patient"))
):
    """Update a medication"""
    medication = MedicationService.update_medication(
        medication_id,
        current_user.id,
        update_data
    )
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found or not authorized"
        )
    return medication


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: str,
    current_user: User = Depends(require_role("patient"))
):
    """Delete a medication"""
    success = MedicationService.delete_medication(medication_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found or not authorized"
        )
    return None

