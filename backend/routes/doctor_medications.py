"""
Doctor medications routes (prescribing & managing patient medications)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from models.schemas import Medication, MedicationCreate, MedicationUpdate, User
from services.medications import MedicationService
from services.auth import AuthService
from dependencies import require_role

router = APIRouter(prefix="/doctor/medications", tags=["doctor-medications"])


@router.get("/patients/{patient_id}", response_model=List[Medication])
async def get_patient_medications_for_doctor(
    patient_id: str,
    active_only: bool = Query(False),
    current_user: User = Depends(require_role("doctor")),
):
    """Doctor: view medications for a specific patient"""
    patient = AuthService.get_user_by_id(patient_id)
    if not patient or patient.role != "patient":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    return MedicationService.get_patient_medications(patient_id, active_only)


@router.post("/patients/{patient_id}", response_model=Medication, status_code=status.HTTP_201_CREATED)
async def prescribe_medication(
    patient_id: str,
    medication_data: MedicationCreate,
    current_user: User = Depends(require_role("doctor")),
):
    """Doctor: prescribe a medication for a patient"""
    patient = AuthService.get_user_by_id(patient_id)
    if not patient or patient.role != "patient":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Ensure "prescribed_by" is set to the current doctor (store id; UI can also show doctor name if desired)
    medication_data.prescribed_by = current_user.id
    medication = MedicationService.create_medication(patient_id, medication_data)
    if not medication:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to prescribe medication")
    return medication


@router.put("/{medication_id}", response_model=Medication)
async def update_medication_as_doctor(
    medication_id: str,
    update_data: MedicationUpdate,
    current_user: User = Depends(require_role("doctor")),
):
    """Doctor: update/deactivate a medication they prescribed"""
    medication = MedicationService.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")

    # Only allow the prescribing doctor to update if prescribed_by is set
    if medication.prescribed_by and medication.prescribed_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this medication")

    # Reuse patient-ownership update by passing the medication's patient_id
    updated = MedicationService.update_medication(medication_id, medication.patient_id, update_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update medication")
    return updated

