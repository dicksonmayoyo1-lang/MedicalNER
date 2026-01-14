"""
Database connection and collection management
"""
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_DB_URI")
DATABASE_NAME = os.getenv("MONGO_DB_NAME", "medical_rag_db")

# Global database connection
mongo_client = None
mongo_db = None


def get_database():
    """Get database instance, creating connection if needed"""
    global mongo_client, mongo_db
    
    if mongo_db is not None:
        return mongo_db
    
    if not MONGO_URI:
        print("WARNING: MONGO_DB_URI not found in environment. Database disabled.")
        return None
    
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        mongo_client.server_info()
        mongo_db = mongo_client[DATABASE_NAME]
        print("✅ MongoDB connected successfully")
        return mongo_db
    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None
    except Exception as e:
        print(f"❌ MongoDB error: {e}")
        return None


def get_collection(collection_name: str):
    """Get a specific collection from the database"""
    db = get_database()
    if db is None:
        return None
    return db[collection_name]


def close_connection():
    """Close database connection"""
    global mongo_client, mongo_db
    if mongo_client:
        mongo_client.close()
        mongo_client = None
        mongo_db = None


# Collection names
COLLECTIONS = {
    "users": "users",
    "patient_records": "patient_records",
    "appointments": "appointments",
    "medications": "medications",
    "screening_results": "screening_results"
}

