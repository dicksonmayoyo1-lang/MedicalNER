"""
Authentication service with MongoDB
"""
from datetime import datetime, timedelta
from typing import Optional, List
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
from dotenv import load_dotenv

from models.schemas import User, UserCreate, Token
from database.models import UserModel

load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service for user management"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and verify a JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def register_user(user_data: UserCreate) -> Optional[User]:
        """Register a new user"""
        # Check if username already exists
        existing_user = UserModel.find_by_username(user_data.username)
        if existing_user:
            return None
        
        # Check if email already exists
        existing_email = UserModel.find_by_email(user_data.email)
        if existing_email:
            return None
        
        # Validate role
        if user_data.role not in ["doctor", "patient", "admin"]:
            return None
        
        # Create user document
        user_doc = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": AuthService.get_password_hash(user_data.password),
            "role": user_data.role,
            "full_name": user_data.full_name,
            "is_active": True
        }
        
        user_id = UserModel.create_user(user_doc)
        if not user_id:
            return None
        
        # Return user without password
        user_doc["id"] = user_id
        user_doc["created_at"] = user_doc.get("created_at", datetime.now().isoformat())
        del user_doc["hashed_password"]
        
        return User(**{k: v for k, v in user_doc.items() if k != "_id"})
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """Authenticate a user and return user object if valid"""
        user_doc = UserModel.find_by_username(username)
        if not user_doc:
            return None
        
        if not AuthService.verify_password(password, user_doc.get("hashed_password", "")):
            return None
        
        if not user_doc.get("is_active", True):
            return None
        
        # Convert to User model
        user_data = {
            "id": str(user_doc["_id"]),
            "username": user_doc["username"],
            "email": user_doc["email"],
            "role": user_doc["role"],
            "full_name": user_doc.get("full_name"),
            "created_at": user_doc.get("created_at", datetime.now().isoformat()),
            "is_active": user_doc.get("is_active", True)
        }
        
        return User(**user_data)
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        """Get user by ID"""
        user_doc = UserModel.find_by_id(user_id)
        if not user_doc:
            return None
        
        user_data = {
            "id": str(user_doc["_id"]),
            "username": user_doc["username"],
            "email": user_doc["email"],
            "role": user_doc["role"],
            "full_name": user_doc.get("full_name"),
            "created_at": user_doc.get("created_at", datetime.now().isoformat()),
            "is_active": user_doc.get("is_active", True)
        }
        
        return User(**user_data)
    
    @staticmethod
    def get_all_users(role: Optional[str] = None, search: Optional[str] = None) -> List[User]:
        """Get all users, optionally filtered by role and search term"""
        from typing import List
        collection = UserModel.get_collection()
        if collection is None:
            return []
        
        query = {}
        if role:
            query["role"] = role
        if search:
            query["$or"] = [
                {"username": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"full_name": {"$regex": search, "$options": "i"}}
            ]
        
        users_doc = list(collection.find(query).sort("created_at", -1))
        users = []
        for user_doc in users_doc:
            user_data = {
                "id": str(user_doc["_id"]),
                "username": user_doc["username"],
                "email": user_doc["email"],
                "role": user_doc["role"],
                "full_name": user_doc.get("full_name"),
                "created_at": user_doc.get("created_at", datetime.now().isoformat()),
                "is_active": user_doc.get("is_active", True)
            }
            users.append(User(**user_data))
        
        return users
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get user by username"""
        user_doc = UserModel.find_by_username(username)
        if not user_doc:
            return None
        
        user_data = {
            "id": str(user_doc["_id"]),
            "username": user_doc["username"],
            "email": user_doc["email"],
            "role": user_doc["role"],
            "full_name": user_doc.get("full_name"),
            "created_at": user_doc.get("created_at", datetime.now().isoformat()),
            "is_active": user_doc.get("is_active", True)
        }
        
        return User(**user_data)
    
    @staticmethod
    def create_token_for_user(user: User) -> Token:
        """Create a token for a user"""
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={"sub": user.username, "role": user.role},
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
    
    @staticmethod
    def initialize_default_users():
        """Initialize default users if they don't exist"""
        # Check if default users exist
        doctor = UserModel.find_by_username("doctor1")
        patient = UserModel.find_by_username("patient1")
        
        if not doctor:
            doctor_data = UserCreate(
                username="doctor1",
                email="doctor@hospital.com",
                password="doctor123",
                role="doctor",
                full_name="Dr. John Smith"
            )
            AuthService.register_user(doctor_data)
            print("✅ Created default doctor user")
        
        if not patient:
            patient_data = UserCreate(
                username="patient1",
                email="patient@example.com",
                password="patient123",
                role="patient",
                full_name="Jane Doe"
            )
            AuthService.register_user(patient_data)
            print("✅ Created default patient user")

