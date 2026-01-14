"""
Appointments service for managing appointments
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from models.schemas import Appointment, AppointmentCreate, AppointmentUpdate
from database.models import AppointmentModel


class AppointmentService:
    """Service for appointment management"""
    
    @staticmethod
    def create_appointment(patient_id: str, appointment_data: AppointmentCreate) -> Optional[Appointment]:
        """Create a new appointment"""
        appointment_doc = {
            "patient_id": patient_id,
            "type": appointment_data.type,
            "preferred_date": appointment_data.preferred_date,
            "preferred_time": appointment_data.preferred_time,
            "reason": appointment_data.reason,
            "status": "pending"
        }
        
        appointment_id = AppointmentModel.create_appointment(appointment_doc)
        if not appointment_id:
            return None
        
        return AppointmentService.get_appointment_by_id(appointment_id)
    
    @staticmethod
    def get_appointment_by_id(appointment_id: str) -> Optional[Appointment]:
        """Get appointment by ID"""
        appointment_doc = AppointmentModel.find_by_id(appointment_id)
        if not appointment_doc:
            return None
        
        return AppointmentService._doc_to_appointment(appointment_doc)
    
    @staticmethod
    def get_patient_appointments(patient_id: str, limit: int = 50) -> List[Appointment]:
        """Get all appointments for a patient"""
        appointments_doc = AppointmentModel.find_by_patient(patient_id, limit)
        return [AppointmentService._doc_to_appointment(doc) for doc in appointments_doc]
    
    @staticmethod
    def update_appointment(appointment_id: str, patient_id: str, update_data: AppointmentUpdate) -> Optional[Appointment]:
        """Update an appointment (only if it belongs to the patient)"""
        appointment_doc = AppointmentModel.find_by_id(appointment_id)
        if not appointment_doc:
            return None
        
        # Verify ownership
        if appointment_doc.get("patient_id") != patient_id:
            return None
        
        update_dict = {}
        if update_data.status is not None:
            update_dict["status"] = update_data.status
        if update_data.scheduled_date is not None:
            update_dict["scheduled_date"] = update_data.scheduled_date
        if update_data.scheduled_time is not None:
            update_dict["scheduled_time"] = update_data.scheduled_time
        if update_data.doctor_notes is not None:
            update_dict["doctor_notes"] = update_data.doctor_notes
        
        if not update_dict:
            return None
        
        success = AppointmentModel.update_appointment(appointment_id, update_dict)
        if not success:
            return None
        
        return AppointmentService.get_appointment_by_id(appointment_id)
    
    @staticmethod
    def delete_appointment(appointment_id: str, patient_id: str) -> bool:
        """Delete an appointment (only if it belongs to the patient)"""
        appointment_doc = AppointmentModel.find_by_id(appointment_id)
        if not appointment_doc:
            return False
        
        # Verify ownership
        if appointment_doc.get("patient_id") != patient_id:
            return False
        
        return AppointmentModel.delete_appointment(appointment_id)
    
    @staticmethod
    def get_all_appointments(status: Optional[str] = None, limit: int = 100) -> List[Appointment]:
        """Get all appointments (for doctors/admins)"""
        collection = AppointmentModel.get_collection()
        if collection is None:
            return []
        
        query = {}
        if status:
            query["status"] = status
        
        appointments_doc = list(collection.find(query)
                               .sort("created_at", -1)
                               .limit(limit))
        return [AppointmentService._doc_to_appointment(doc) for doc in appointments_doc]
    
    @staticmethod
    def get_doctor_appointments(doctor_id: str, status: Optional[str] = None, limit: int = 50) -> List[Appointment]:
        """Get all appointments for a doctor"""
        collection = AppointmentModel.get_collection()
        if collection is None:
            return []
        
        query = {"doctor_id": doctor_id}
        if status:
            query["status"] = status
        
        appointments_doc = list(collection.find(query)
                               .sort("created_at", -1)
                               .limit(limit))
        return [AppointmentService._doc_to_appointment(doc) for doc in appointments_doc]
    
    @staticmethod
    def confirm_appointment(appointment_id: str, doctor_id: str, scheduled_date: str, scheduled_time: str, doctor_notes: Optional[str] = None) -> Optional[Appointment]:
        """Confirm an appointment and assign it to a doctor"""
        appointment_doc = AppointmentModel.find_by_id(appointment_id)
        if not appointment_doc:
            return None
        
        if appointment_doc.get("status") != "pending":
            return None  # Can only confirm pending appointments
        
        update_dict = {
            "status": "confirmed",
            "doctor_id": doctor_id,
            "scheduled_date": scheduled_date,
            "scheduled_time": scheduled_time
        }
        
        if doctor_notes:
            update_dict["doctor_notes"] = doctor_notes
        
        success = AppointmentModel.update_appointment(appointment_id, update_dict)
        if not success:
            return None
        
        return AppointmentService.get_appointment_by_id(appointment_id)
    
    @staticmethod
    def cancel_appointment(appointment_id: str, cancelled_by: str, reason: Optional[str] = None) -> Optional[Appointment]:
        """Cancel an appointment"""
        appointment_doc = AppointmentModel.find_by_id(appointment_id)
        if not appointment_doc:
            return None
        
        if appointment_doc.get("status") in ["cancelled", "completed"]:
            return None  # Can't cancel already cancelled/completed appointments
        
        update_dict = {
            "status": "cancelled"
        }
        
        if reason:
            update_dict["cancellation_reason"] = reason
            update_dict["cancelled_by"] = cancelled_by
        
        success = AppointmentModel.update_appointment(appointment_id, update_dict)
        if not success:
            return None
        
        return AppointmentService.get_appointment_by_id(appointment_id)
    
    @staticmethod
    def complete_appointment(appointment_id: str, doctor_id: str, notes: Optional[str] = None) -> Optional[Appointment]:
        """Mark an appointment as completed"""
        appointment_doc = AppointmentModel.find_by_id(appointment_id)
        if not appointment_doc:
            return None
        
        # Verify doctor ownership
        if appointment_doc.get("doctor_id") != doctor_id:
            return None
        
        if appointment_doc.get("status") != "confirmed":
            return None  # Can only complete confirmed appointments
        
        update_dict = {
            "status": "completed"
        }
        
        if notes:
            existing_notes = appointment_doc.get("doctor_notes", "")
            update_dict["doctor_notes"] = f"{existing_notes}\n\nCompletion Notes: {notes}".strip()
        
        success = AppointmentModel.update_appointment(appointment_id, update_dict)
        if not success:
            return None
        
        return AppointmentService.get_appointment_by_id(appointment_id)
    
    @staticmethod
    def _doc_to_appointment(doc: Dict[str, Any]) -> Appointment:
        """Convert MongoDB document to Appointment model"""
        return Appointment(
            id=str(doc["_id"]),
            patient_id=doc.get("patient_id", ""),
            type=doc.get("type", ""),
            preferred_date=doc.get("preferred_date", ""),
            preferred_time=doc.get("preferred_time", ""),
            reason=doc.get("reason", ""),
            status=doc.get("status", "pending"),
            scheduled_date=doc.get("scheduled_date"),
            scheduled_time=doc.get("scheduled_time"),
            doctor_id=doc.get("doctor_id"),
            doctor_notes=doc.get("doctor_notes"),
            created_at=doc.get("created_at", datetime.now().isoformat()),
            updated_at=doc.get("updated_at", datetime.now().isoformat())
        )

