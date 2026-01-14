"""
MongoDB document models and helpers
"""
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId
from database.connection import get_collection, COLLECTIONS


class UserModel:
    """User model for MongoDB operations"""
    
    @staticmethod
    def get_collection():
        return get_collection(COLLECTIONS["users"])
    
    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Optional[str]:
        """Create a new user and return user ID"""
        collection = UserModel.get_collection()
        if collection is None:
            return None
        
        user_data["created_at"] = datetime.now().isoformat()
        user_data["is_active"] = True
        
        result = collection.insert_one(user_data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Find user by username"""
        collection = UserModel.get_collection()
        if collection is None:
            return None
        return collection.find_one({"username": username})
    
    @staticmethod
    def find_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Find user by email"""
        collection = UserModel.get_collection()
        if collection is None:
            return None
        return collection.find_one({"email": email})
    
    @staticmethod
    def find_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Find user by ID"""
        collection = UserModel.get_collection()
        if collection is None:
            return None
        if not ObjectId.is_valid(user_id):
            return None
        return collection.find_one({"_id": ObjectId(user_id)})
    
    @staticmethod
    def update_user(user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user information"""
        collection = UserModel.get_collection()
        if collection is None:
            return False
        if not ObjectId.is_valid(user_id):
            return False
        
        update_data["updated_at"] = datetime.now().isoformat()
        result = collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0


class AppointmentModel:
    """Appointment model for MongoDB operations"""
    
    @staticmethod
    def get_collection():
        return get_collection(COLLECTIONS["appointments"])
    
    @staticmethod
    def create_appointment(appointment_data: Dict[str, Any]) -> Optional[str]:
        """Create a new appointment and return appointment ID"""
        collection = AppointmentModel.get_collection()
        if collection is None:
            return None
        
        appointment_data["created_at"] = datetime.now().isoformat()
        appointment_data["updated_at"] = datetime.now().isoformat()
        appointment_data["status"] = "pending"
        
        result = collection.insert_one(appointment_data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_id(appointment_id: str) -> Optional[Dict[str, Any]]:
        """Find appointment by ID"""
        collection = AppointmentModel.get_collection()
        if collection is None:
            return None
        if not ObjectId.is_valid(appointment_id):
            return None
        return collection.find_one({"_id": ObjectId(appointment_id)})
    
    @staticmethod
    def find_by_patient(patient_id: str, limit: int = 50) -> list:
        """Find appointments by patient ID"""
        collection = AppointmentModel.get_collection()
        if collection is None:
            return []
        return list(collection.find({"patient_id": patient_id})
                   .sort("created_at", -1)
                   .limit(limit))
    
    @staticmethod
    def update_appointment(appointment_id: str, update_data: Dict[str, Any]) -> bool:
        """Update appointment information"""
        collection = AppointmentModel.get_collection()
        if collection is None:
            return False
        if not ObjectId.is_valid(appointment_id):
            return False
        
        update_data["updated_at"] = datetime.now().isoformat()
        result = collection.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete_appointment(appointment_id: str) -> bool:
        """Delete an appointment"""
        collection = AppointmentModel.get_collection()
        if collection is None:
            return False
        if not ObjectId.is_valid(appointment_id):
            return False
        
        result = collection.delete_one({"_id": ObjectId(appointment_id)})
        return result.deleted_count > 0


class MedicationModel:
    """Medication model for MongoDB operations"""
    
    @staticmethod
    def get_collection():
        return get_collection(COLLECTIONS["medications"])
    
    @staticmethod
    def create_medication(medication_data: Dict[str, Any]) -> Optional[str]:
        """Create a new medication record and return medication ID"""
        collection = MedicationModel.get_collection()
        if collection is None:
            return None
        
        medication_data["created_at"] = datetime.now().isoformat()
        medication_data["updated_at"] = datetime.now().isoformat()
        medication_data["is_active"] = True
        
        result = collection.insert_one(medication_data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_id(medication_id: str) -> Optional[Dict[str, Any]]:
        """Find medication by ID"""
        collection = MedicationModel.get_collection()
        if collection is None:
            return None
        if not ObjectId.is_valid(medication_id):
            return None
        return collection.find_one({"_id": ObjectId(medication_id)})
    
    @staticmethod
    def find_by_patient(patient_id: str, active_only: bool = False) -> list:
        """Find medications by patient ID"""
        collection = MedicationModel.get_collection()
        if collection is None:
            return []
        
        query = {"patient_id": patient_id}
        if active_only:
            query["is_active"] = True
        
        return list(collection.find(query).sort("created_at", -1))
    
    @staticmethod
    def update_medication(medication_id: str, update_data: Dict[str, Any]) -> bool:
        """Update medication information"""
        collection = MedicationModel.get_collection()
        if collection is None:
            return False
        if not ObjectId.is_valid(medication_id):
            return False
        
        update_data["updated_at"] = datetime.now().isoformat()
        result = collection.update_one(
            {"_id": ObjectId(medication_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete_medication(medication_id: str) -> bool:
        """Delete a medication record"""
        collection = MedicationModel.get_collection()
        if collection is None:
            return False
        if not ObjectId.is_valid(medication_id):
            return False
        
        result = collection.delete_one({"_id": ObjectId(medication_id)})
        return result.deleted_count > 0

