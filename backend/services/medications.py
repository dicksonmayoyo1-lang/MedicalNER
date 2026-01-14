"""
Medications service for managing patient medications
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from models.schemas import Medication, MedicationCreate, MedicationUpdate
from database.models import MedicationModel


class MedicationService:
    """Service for medication management"""
    
    @staticmethod
    def create_medication(patient_id: str, medication_data: MedicationCreate) -> Optional[Medication]:
        """Create a new medication record"""
        medication_doc = {
            "patient_id": patient_id,
            "name": medication_data.name,
            "dosage": medication_data.dosage,
            "frequency": medication_data.frequency,
            "start_date": medication_data.start_date,
            "end_date": medication_data.end_date,
            "prescribed_by": medication_data.prescribed_by,
            "notes": medication_data.notes,
            "is_active": True
        }
        
        medication_id = MedicationModel.create_medication(medication_doc)
        if not medication_id:
            return None
        
        return MedicationService.get_medication_by_id(medication_id)
    
    @staticmethod
    def get_medication_by_id(medication_id: str) -> Optional[Medication]:
        """Get medication by ID"""
        medication_doc = MedicationModel.find_by_id(medication_id)
        if not medication_doc:
            return None
        
        return MedicationService._doc_to_medication(medication_doc)
    
    @staticmethod
    def get_patient_medications(patient_id: str, active_only: bool = False) -> List[Medication]:
        """Get all medications for a patient"""
        medications_doc = MedicationModel.find_by_patient(patient_id, active_only)
        return [MedicationService._doc_to_medication(doc) for doc in medications_doc]
    
    @staticmethod
    def update_medication(medication_id: str, patient_id: str, update_data: MedicationUpdate) -> Optional[Medication]:
        """Update a medication (only if it belongs to the patient)"""
        medication_doc = MedicationModel.find_by_id(medication_id)
        if not medication_doc:
            return None
        
        # Verify ownership
        if medication_doc.get("patient_id") != patient_id:
            return None
        
        update_dict = {}
        if update_data.dosage is not None:
            update_dict["dosage"] = update_data.dosage
        if update_data.frequency is not None:
            update_dict["frequency"] = update_data.frequency
        if update_data.end_date is not None:
            update_dict["end_date"] = update_data.end_date
        if update_data.notes is not None:
            update_dict["notes"] = update_data.notes
        if update_data.is_active is not None:
            update_dict["is_active"] = update_data.is_active
        
        if not update_dict:
            return None
        
        success = MedicationModel.update_medication(medication_id, update_dict)
        if not success:
            return None
        
        return MedicationService.get_medication_by_id(medication_id)
    
    @staticmethod
    def delete_medication(medication_id: str, patient_id: str) -> bool:
        """Delete a medication (only if it belongs to the patient)"""
        medication_doc = MedicationModel.find_by_id(medication_id)
        if not medication_doc:
            return False
        
        # Verify ownership
        if medication_doc.get("patient_id") != patient_id:
            return False
        
        return MedicationModel.delete_medication(medication_id)
    
    @staticmethod
    def _doc_to_medication(doc: Dict[str, Any]) -> Medication:
        """Convert MongoDB document to Medication model"""
        return Medication(
            id=str(doc["_id"]),
            patient_id=doc.get("patient_id", ""),
            name=doc.get("name", ""),
            dosage=doc.get("dosage", ""),
            frequency=doc.get("frequency", ""),
            start_date=doc.get("start_date", ""),
            end_date=doc.get("end_date"),
            prescribed_by=doc.get("prescribed_by"),
            notes=doc.get("notes"),
            is_active=doc.get("is_active", True),
            created_at=doc.get("created_at", datetime.now().isoformat()),
            updated_at=doc.get("updated_at", datetime.now().isoformat())
        )

