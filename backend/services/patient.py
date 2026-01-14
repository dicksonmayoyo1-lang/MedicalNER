"""
Patient service for patient-related operations
"""
from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime

from models.schemas import User, UserUpdate
from database.models import UserModel
from database.connection import get_collection, COLLECTIONS


class PatientService:
    """Service for patient-related operations"""
    
    @staticmethod
    def get_patient_records(patient_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all records for a patient"""
        collection = get_collection(COLLECTIONS["patient_records"])
        if collection is None:
            return []
        
        records = list(collection.find({"patient_id": patient_id})
                      .sort("upload_timestamp", -1)
                      .limit(limit))
        
        formatted_records = []
        for record in records:
            summary_preview = ""
            if record.get("summary") and isinstance(record["summary"], dict):
                summary_preview = record["summary"].get("clinical_summary", "")[:100] + "..."
            elif isinstance(record.get("summary"), str):
                summary_preview = record["summary"][:100] + "..."
            
            formatted_records.append({
                "id": str(record["_id"]),
                "patient_id": record.get("patient_id", "unknown"),
                "original_filename": record.get("original_filename", "unknown"),
                "upload_timestamp": record.get("upload_timestamp", ""),
                "diseases_count": record.get("diseases_count", 0),
                "labs_count": record.get("labs_count", 0),
                "summary_preview": summary_preview
            })
        
        return formatted_records
    
    @staticmethod
    def get_patient_record(patient_id: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific record for a patient"""
        collection = get_collection(COLLECTIONS["patient_records"])
        if collection is None:
            return None
        
        if not ObjectId.is_valid(record_id):
            return None
        
        record = collection.find_one({
            "_id": ObjectId(record_id),
            "patient_id": patient_id
        })
        
        if not record:
            return None
        
        # Convert entities back to proper format
        diseases = record.get("diseases", [])
        lab_results = record.get("lab_results", [])
        
        summary_preview = ""
        summary_obj = None
        if record.get("summary"):
            if isinstance(record["summary"], dict):
                summary_preview = record["summary"].get("clinical_summary", "")[:100] + "..."
                summary_obj = record["summary"]
            elif isinstance(record["summary"], str):
                summary_preview = record["summary"][:100] + "..."
                summary_obj = {"clinical_summary": record["summary"]}
        
        return {
            "id": str(record["_id"]),
            "patient_id": record.get("patient_id", "unknown"),
            "original_filename": record.get("original_filename", "unknown"),
            "upload_timestamp": record.get("upload_timestamp", ""),
            "diseases_count": record.get("diseases_count", 0),
            "labs_count": record.get("labs_count", 0),
            "summary_preview": summary_preview,
            "extracted_text": record.get("extracted_text", ""),
            "diseases": diseases,
            "lab_results": lab_results,
            "summary": summary_obj,
            "metadata": record.get("metadata", {})
        }
    
    @staticmethod
    def update_patient_profile(user_id: str, update_data: UserUpdate) -> Optional[User]:
        """Update patient profile information"""
        from services.auth import AuthService
        
        update_dict = {}
        if update_data.full_name is not None:
            update_dict["full_name"] = update_data.full_name
        if update_data.email is not None:
            update_dict["email"] = update_data.email
        
        if not update_dict:
            return None
        
        success = UserModel.update_user(user_id, update_dict)
        if not success:
            return None
        
        return AuthService.get_user_by_id(user_id)
    
    @staticmethod
    def get_patient_dashboard_data(patient_id: str) -> Dict[str, Any]:
        """Get dashboard data for a patient"""
        from services.appointments import AppointmentService
        
        records = PatientService.get_patient_records(patient_id, limit=5)
        appointments = AppointmentService.get_patient_appointments(patient_id, limit=5)
        
        # Format appointments for dashboard
        upcoming_appointments = []
        for apt in appointments:
            if apt.status in ["pending", "confirmed"]:
                # Get doctor name if assigned
                doctor_name = "TBD"
                if apt.doctor_id:
                    from services.auth import AuthService
                    doctor = AuthService.get_user_by_id(apt.doctor_id)
                    if doctor:
                        doctor_name = doctor.full_name or doctor.username
                
                upcoming_appointments.append({
                    "date": apt.scheduled_date or apt.preferred_date,
                    "doctor": doctor_name,
                    "type": apt.type
                })
        
        return {
            "recent_records": len(records),
            "upcoming_appointments": upcoming_appointments,
            "total_records": len(PatientService.get_patient_records(patient_id, limit=1000))
        }

