# rag.py (modified to include import time in responses)
from fastapi import HTTPException
import re
import time
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from typing import Any, Dict, List, Optional, Annotated

from fastapi import FastAPI, UploadFile, File, Form, Depends
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import torch
import tempfile
import os
import numpy as np
from passlib.context import CryptContext
from jose import JWTError, jwt
import faiss
from sentence_transformers import SentenceTransformer
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from utils import extract_text_from_pdf, normalize_icd
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import uuid
from dotenv import load_dotenv

load_dotenv()

# ----------------------------
# Record import (service start) time
# ----------------------------
IMPORT_TIME_EPOCH = time.time()
IMPORT_TIME_ISO = datetime.utcfromtimestamp(
    IMPORT_TIME_EPOCH).isoformat() + "Z"

# ----------------------------
# Configure Gemini
# ----------------------------
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
print("GEMINI_API_KEY present:", bool(GEMINI_API_KEY))


# instantiate model (keep as you had)
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.7,
    google_api_key=GEMINI_API_KEY,
    max_tokens=1000,
    timeout=30
)

# ----------------------------
# API Setup
# ----------------------------
app = FastAPI(title="Disease + Lab RAG API")
origins = ["*", "http://localhost", "http://127.0.0.1:5500"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------
# Mongo Setup
# ---------------------------
MONGO_URI = os.getenv("MONGO_DB_URI")
if not MONGO_URI:
    print("WARNING: MONGO_DB_URI not found in environment. Storage disabled.")
    mongo_client = None
    mongo_db = None
    records_collection = None
else:
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        mongo_client.server_info()
        mongo_db = mongo_client["medical_rag_db"]
        records_collection = mongo_db["patient_records"]
        print("✅ MongoDB connected successfully")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        mongo_client = None
        mongo_db = None
        records_collection = None


# ----------------------------
# Device
# ----------------------------
if torch.cuda.is_available():
    device = torch.device("cuda:0")
else:
    device = torch.device("cpu")

# ----------------------------
# Disease NER Model
# ----------------------------
DISEASE_MODEL_DIR = "./diseases_model"
d_tokenizer = AutoTokenizer.from_pretrained(DISEASE_MODEL_DIR)
d_model = AutoModelForTokenClassification.from_pretrained(DISEASE_MODEL_DIR)
# move model once to device for manual inference
d_model.to(device)
d_label_map = {int(k): v for k, v in getattr(
    d_model.config, "id2label", {}).items()}

d_pipeline = pipeline(
    "token-classification",
    model=d_model,
    tokenizer=d_tokenizer,
    aggregation_strategy="simple",
    device=0 if torch.cuda.is_available() else -1,
)
DISEASE_MAX_LEN = min(getattr(d_tokenizer, "model_max_length", 512), 512)

# ----------------------------
# Lab RAG KB Setup
# ----------------------------
lab_dataset = [
    {"test": "Glucose", "description": "Measures blood sugar levels in the body",
        "unit": "mg/dL", "normal_range": "70-110"},
    {"test": "WBC", "description": "White blood cell count, indicating immune system status",
        "unit": "10^3/uL", "normal_range": "4-10"},
    {"test": "Hemoglobin", "description": "Measures the concentration of hemoglobin in red blood cells",
        "unit": "g/dL", "normal_range": "12-16"},
    {"test": "Creatinine", "description": "Indicator of kidney function",
        "unit": "mg/dL", "normal_range": "0.6-1.3"},
    {"test": "Platelets", "description": "Platelet count, important for blood clotting",
        "unit": "10^3/uL", "normal_range": "150-400"},
    {"test": "ALT", "description": "Alanine transaminase, a liver enzyme",
        "unit": "U/L", "normal_range": "7-56"},
    {"test": "AST", "description": "Aspartate transaminase, another liver enzyme",
        "unit": "U/L", "normal_range": "10-40"},
    {"test": "BUN", "description": "Blood urea nitrogen, kidney function indicator",
        "unit": "mg/dL", "normal_range": "7-20"},
    {"test": "Cholesterol", "description": "Total cholesterol in the blood",
        "unit": "mg/dL", "normal_range": "<200"},
    {"test": "Triglycerides", "description": "Fat in the blood, indicator of cardiovascular risk",
        "unit": "mg/dL", "normal_range": "<150"},
    # Add more tests as needed
]

# ----------------------------
# SentenceTransformer embeddings
# ----------------------------
# Use force_download=True to recover from any corrupted/cached files (e.g. vocab.txt)
embed_model = SentenceTransformer(
    'all-MiniLM-L6-v2',
    tokenizer_kwargs={"force_download": True},
)
lab_texts = [
    f"{entry['test']}: {entry['description']}. Unit: {entry['unit']}. Normal range: {entry['normal_range']}\."
    for entry in lab_dataset
]
lab_embeddings = embed_model.encode(lab_texts, convert_to_numpy=True)
embedding_dim = lab_embeddings.shape[1]

# Build FAISS index
index = faiss.IndexFlatL2(embedding_dim)
index.add(lab_embeddings)

# Map index -> lab doc
index_to_doc = {i: lab_dataset[i] for i in range(len(lab_dataset))}

# ----------------------------
# Pydantic Models
# ----------------------------

# Add Pydantic models for analytics


class AnalyticsSummary(BaseModel):
    total_records: int
    total_diseases: int
    total_labs: int
    avg_diseases_per_record: float
    avg_labs_per_record: float
    date_range: Optional[Dict[str, str]] = None


class DiseaseFrequency(BaseModel):
    disease_name: str
    count: int
    percentage: float


# JWT Configuration
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


class User(BaseModel):
    id: str
    username: str
    email: str
    role: str  # "doctor", "patient", "admin"
    full_name: Optional[str] = None
    created_at: str
    is_active: bool = True


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "patient"
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


# Mock Database (Replace with real DB in production)
users_db = {}
# Add some default users
users_db["doctor1"] = {
    "id": "user_001",
    "username": "doctor1",
    "email": "doctor@hospital.com",
    "role": "doctor",
    "full_name": "Dr. John Smith",
    "hashed_password": pwd_context.hash("doctor123"),
    "created_at": datetime.now().isoformat(),
    "is_active": True
}
users_db["patient1"] = {
    "id": "user_002",
    "username": "patient1",
    "email": "patient@example.com",
    "role": "patient",
    "full_name": "Jane Doe",
    "hashed_password": pwd_context.hash("patient123"),
    "created_at": datetime.now().isoformat(),
    "is_active": True
}


class User(BaseModel):
    id: str
    username: str
    email: str
    role: str  # "doctor", "patient", "admin"
    full_name: Optional[str] = None
    created_at: str
    is_active: bool = True


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "patient"
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


# Mock Database (Replace with real DB in production)
users_db = {}
# Add some default users
users_db["doctor1"] = {
    "id": "user_001",
    "username": "doctor1",
    "email": "doctor@hospital.com",
    "role": "doctor",
    "full_name": "Dr. John Smith",
    "hashed_password": pwd_context.hash("doctor123"),
    "created_at": datetime.now().isoformat(),
    "is_active": True
}
users_db["patient1"] = {
    "id": "user_002",
    "username": "patient1",
    "email": "patient@example.com",
    "role": "patient",
    "full_name": "Jane Doe",
    "hashed_password": pwd_context.hash("patient123"),
    "created_at": datetime.now().isoformat(),
    "is_active": True
}


class LabFrequency(BaseModel):
    lab_name: str
    count: int
    percentage: float


class TimeSeriesPoint(BaseModel):
    date: str
    count: int


class AnalyticsResponse(BaseModel):
    summary: AnalyticsSummary
    top_diseases: List[DiseaseFrequency]
    top_labs: List[LabFrequency]
    upload_trend: List[TimeSeriesPoint]
    disease_trend: Optional[List[TimeSeriesPoint]] = None


class Entity(BaseModel):
    text: str
    start: int
    end: int
    entity_type: str
    icd_code: Optional[str] = None
    confidence: float
    value: Optional[str] = None
    unit: Optional[str] = None
    normal_range: Optional[str] = None


class CombinedNERResponse(BaseModel):
    metadata: Optional[Dict[str, Any]] = None
    text: str
    diseases: List[Entity]
    lab_results: List[Entity]
    summary: Optional[Dict[str, str]] = None  # <-- new field


class TextRequest(BaseModel):
    text: str
    icd_map: bool = False


# -----Mongo pydantic models----------
class StoredRecord(BaseModel):
    id: str
    patient_id: str
    original_filename: str
    upload_timestamp: str
    diseases_count: int
    labs_count: int
    summary_preview: str


class RecordDetail(StoredRecord):
    extracted_text: str
    diseases: List[Entity]
    lab_results: List[Entity]
    summary: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchQuery(BaseModel):
    disease_name: Optional[str] = None
    lab_test: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 50

    # Add screening models


class ScreeningRule(BaseModel):
    id: str
    name: str
    description: str
    conditions: List[Dict[str, Any]]
    risk_level: str  # LOW, MEDIUM, HIGH
    recommendation: str


class ScreeningResult(BaseModel):
    record_id: str
    patient_id: str
    original_filename: str
    screening_date: str
    risk_level: str
    triggered_rules: List[Dict[str, Any]]
    recommendations: List[str]
    diseases_found: List[str]
    labs_found: List[str]


class ScreeningRequest(BaseModel):
    record_id: Optional[str] = None
    patient_id: Optional[str] = None
    run_all: bool = False


# Define screening rules
SCREENING_RULES = [
    {
        "id": "rule_001",
        "name": "Diabetes with High Glucose",
        "description": "Patient with diabetes and elevated glucose levels",
        "conditions": [
            {"type": "disease", "value": "diabetes", "operator": "contains"},
            {"type": "lab", "value": "glucose", "operator": "contains"},
            {"type": "lab_value", "value": 200,
                "operator": "greater_than", "unit": "mg/dL"}
        ],
        "risk_level": "HIGH",
        "recommendation": "Refer to endocrinology for diabetes management"
    },
    {
        "id": "rule_002",
        "name": "Hypertension with Chest Pain",
        "description": "Hypertensive patient presenting with chest pain",
        "conditions": [
            {"type": "disease", "value": "hypertension", "operator": "contains"},
            {"type": "disease", "value": "chest pain", "operator": "contains"}
        ],
        "risk_level": "HIGH",
        "recommendation": "Cardiac evaluation recommended. Monitor for angina symptoms."
    },
    {
        "id": "rule_003",
        "name": "Multiple Chronic Conditions",
        "description": "Patient with 3 or more chronic conditions",
        "conditions": [
            {"type": "disease_count", "value": 3, "operator": "greater_than_equal"}
        ],
        "risk_level": "MEDIUM",
        "recommendation": "Consider comprehensive care management"
    },
    {
        "id": "rule_004",
        "name": "Abnormal Liver Function",
        "description": "Elevated liver enzymes",
        "conditions": [
            {"type": "lab", "value": "ALT", "operator": "contains"},
            {"type": "lab_value", "value": 56,
                "operator": "greater_than", "unit": "U/L"}
        ],
        "risk_level": "MEDIUM",
        "recommendation": "Liver function tests and hepatology consult if persistent"
    },
    {
        "id": "rule_005",
        "name": "Anemia with Fatigue",
        "description": "Low hemoglobin with fatigue symptoms",
        "conditions": [
            {"type": "lab", "value": "hemoglobin", "operator": "contains"},
            {"type": "lab_value", "value": 12,
                "operator": "less_than", "unit": "g/dL"},
            {"type": "disease", "value": "fatigue", "operator": "contains"}
        ],
        "risk_level": "MEDIUM",
        "recommendation": "Complete blood count and iron studies recommended"
    },
    {
        "id": "rule_006",
        "name": "COPD with Dyspnea",
        "description": "COPD patient with shortness of breath",
        "conditions": [
            {"type": "disease", "value": "COPD", "operator": "contains"},
            {"type": "disease", "value": "dyspnea", "operator": "contains"}
        ],
        "risk_level": "MEDIUM",
        "recommendation": "Pulmonary function tests and inhaler assessment"
    },
    {
        "id": "rule_007",
        "name": "Renal Impairment",
        "description": "Elevated creatinine indicating kidney issues",
        "conditions": [
            {"type": "lab", "value": "creatinine", "operator": "contains"},
            {"type": "lab_value", "value": 1.3,
                "operator": "greater_than", "unit": "mg/dL"}
        ],
        "risk_level": "MEDIUM",
        "recommendation": "Renal function panel and nephrology consult"
    }
]

# ----------------------------
# Lab RAG Functions
# ----------------------------


def retrieve_lab_candidates(text: str, top_k: int = 5):
    query_emb = embed_model.encode([text], convert_to_numpy=True)
    D, I = index.search(query_emb, top_k)
    return [index_to_doc[i] for i in I[0]]

# _------------------------


# Common lab test names (whitelist for validation)
KNOWN_LAB_TESTS = {
    "glucose", "wbc", "rbc", "hemoglobin", "hgb", "hematocrit", "hct", "platelet", "creatinine",
    "bun", "alt", "ast", "cholesterol", "triglyceride", "albumin", "bilirubin", "sodium", "potassium",
    "calcium", "phosphorus", "magnesium", "tsh", "t4", "t3", "hba1c", "hba", "ldl", "hdl", "crp",
    "esr", "pt", "inr", "aptt", "psa", "vitamin d", "vitamin b12", "folate", "iron", "ferritin",
    "uric acid", "alkaline phosphatase", "alp", "ggt", "ldh", "ck", "troponin", "bnp", "nt-probnp",
    "d-dimer", "fibrinogen", "protein", "globulin", "a/g ratio", "bicarbonate", "co2", "chloride",
    "anion gap", "osmolality", "urea", "egfr", "gfr", "microalbumin", "urine protein", "urine glucose"
}

# Common false positive patterns to exclude
FALSE_POSITIVE_PATTERNS = [
    r"^page\s+\d+",
    r"^\d+\s+of\s+\d+",
    r"^ref\s*:?\s*\d+",
    r"^dob\s*:?",
    r"^age\s*:?\s*\d+",
    r"^collected\s*:?",
    r"^printed\s*:?",
    r"^referred\s*:?",
    r"^dept\s*",
    r"^no\s*\.?\s*",
    r"^source\s*",
    r"^type\s*\d+",
    r"^\d{4}\s*$",  # Years like 2020
    r"^[a-z]\s+\d+$",  # Single letter followed by number (like "A 1")
    r"^\d+\s*$",  # Just numbers
    r"^[a-z]{1,2}\s*$",  # Very short words (1-2 letters)
    r"^departments?$",
    r"^jalans?$",
    r"^sel\s*\d+",
    r"^kdigo",
    r"^thresholds?$",
    r"^values?$",
    r"^within\s+\d+",
    r"^least\s+\d+",
    r"^increased\s+\d+",
]

def is_valid_lab_result(lab_name: str, value: str = None) -> bool:
    """
    Validate if a potential lab result is actually a lab test.
    """
    if not lab_name:
        return False
    
    lab_lower = lab_name.lower().strip()
    
    # Check against false positive patterns
    for pattern in FALSE_POSITIVE_PATTERNS:
        if re.match(pattern, lab_lower, re.IGNORECASE):
            return False
    
    # Must have a numeric value
    if value:
        try:
            float(value)
        except (ValueError, TypeError):
            return False
    else:
        return False
    
    # Check if it's a known lab test
    if lab_lower in KNOWN_LAB_TESTS:
        return True
    
    # Check if it contains common lab test keywords
    lab_keywords = ["test", "level", "count", "concentration", "ratio", "index", "rate"]
    if any(keyword in lab_lower for keyword in lab_keywords):
        return True
    
    # Check if it's a reasonable length (not too short, not too long)
    if len(lab_name) < 3 or len(lab_name) > 50:
        return False
    
    # Exclude common non-lab words
    excluded_words = {"page", "of", "ref", "dob", "age", "no", "dept", "source", "type", 
                     "collected", "printed", "referred", "departments", "jalans", "sel",
                     "kdigo", "thresholds", "values", "within", "least", "increased", "a", 
                     "to", "the", "and", "or", "is", "are", "was", "were"}
    if lab_lower in excluded_words:
        return False
    
    # If it has a unit, it's more likely to be a lab test
    # This will be checked in the regex pattern
    
    return True

def extract_labs_with_regex(text: str):
    """
    Extract lab results using improved regex patterns.
    Only matches patterns that look like actual lab tests with values and units.
    """
    # More specific pattern: lab name (2+ chars, not just numbers) followed by value and optional unit
    # Pattern 1: "LabName: value unit" or "LabName value unit"
    pattern1 = r"([A-Za-z][A-Za-z0-9\s/&-]{2,30}?)\s*[:=]\s*([\d.,]+)\s*(mg/dL|mmol/L|g/dL|%|U/L|mEq/L|ng/mL|µg/dL|pg/mL|IU/L|mIU/L|×10[³⁹]|10\^3|10\^9)?"
    
    # Pattern 2: Common lab test names followed by value
    pattern2 = r"\b(Glucose|WBC|RBC|Hemoglobin|HGB|Hematocrit|HCT|Platelet|Creatinine|BUN|ALT|AST|Cholesterol|Triglyceride|Albumin|Bilirubin|Sodium|Potassium|Calcium|Phosphorus|Magnesium|TSH|T4|T3|HbA1c|HbA|LDL|HDL|CRP|ESR|PT|INR|APTT|PSA|Vitamin\s+D|Vitamin\s+B12|Folate|Iron|Ferritin|Uric\s+Acid|Alkaline\s+Phosphatase|ALP|GGT|LDH|CK|Troponin|BNP|NT-proBNP|D-dimer|Fibrinogen|Protein|Globulin|A/G\s+Ratio|Bicarbonate|CO2|Chloride|Anion\s+Gap|Osmolality|Urea|eGFR|GFR|Microalbumin|Urine\s+Protein|Urine\s+Glucose)\s*[:=]?\s*([\d.,]+)\s*(mg/dL|mmol/L|g/dL|%|U/L|mEq/L|ng/mL|µg/dL|pg/mL|IU/L|mIU/L|×10[³⁹]|10\^3|10\^9)?"
    
    labs = []
    seen = set()  # Track seen labs to avoid duplicates
    
    # Try pattern 1 (general pattern)
    for match in re.finditer(pattern1, text, re.IGNORECASE):
        lab_name = match.group(1).strip()
        value = match.group(2).strip()
        unit = match.group(3) if match.lastindex >= 3 and match.group(3) else None
        
        # Validate
        if is_valid_lab_result(lab_name, value):
            # Create unique key to avoid duplicates
            key = f"{lab_name.lower()}:{value}"
            if key not in seen:
                seen.add(key)
                labs.append(Entity(
                    text=lab_name,
                    start=match.start(),
                    end=match.end(),
                    entity_type="lab",
                    confidence=0.9 if unit else 0.7,  # Higher confidence if unit present
                    value=value,
                    unit=unit
                ))
    
    # Try pattern 2 (known lab tests)
    for match in re.finditer(pattern2, text, re.IGNORECASE):
        lab_name = match.group(1).strip()
        value = match.group(2).strip()  # Value is group 2
        unit = match.group(3) if match.lastindex >= 3 and match.group(3) else None  # Unit is group 3
        
        # Validate
        if is_valid_lab_result(lab_name, value):
            key = f"{lab_name.lower()}:{value}"
            if key not in seen:
                seen.add(key)
                labs.append(Entity(
                    text=lab_name,
                    start=match.start(),
                    end=match.end(),
                    entity_type="lab",
                    confidence=0.95,  # High confidence for known lab tests
                    value=value,
                    unit=unit
                ))
    
    return labs

# Summary


def generate_summary(extracted_text: str, diseases: list, labs: list, max_sentences: int = 4) -> str:
    """
    Ask Gemini to produce a short clinical summary from extracted text, disease entities and lab results.
    Returns a plain string summary. Defensive: tries to parse JSON but falls back to raw text.
    """
    # Build concise context
    disease_list = []
    for d in diseases:
        # accept both dict-like and pydantic Entity
        name = getattr(d, "text", None) or d.get(
            "text", "") if isinstance(d, dict) else ""
        label = getattr(d, "entity_type", None) or d.get(
            "entity_type", "") if isinstance(d, dict) else ""
        if name:
            disease_list.append(f"{name} ({label})")
    lab_list = []
    for l in labs:
        name = getattr(l, "text", None) or l.get("test_name") or l.get(
            "text") if isinstance(l, dict) else ""
        value = getattr(l, "value", None) or l.get(
            "value_extracted") if isinstance(l, dict) else None
        if name:
            lab_list.append(f"{name}: {value or '-'}")

    prompt = f"""
You are a concise clinical assistant. Produce a short clinical summary (at most {max_sentences} sentences) for a clinician,
based on the extracted report text, the detected disease entities and lab results.

Detected disease entities:
{chr(10).join(disease_list) if disease_list else 'None'}

Detected lab results:
{chr(10).join(lab_list) if lab_list else 'None'}

Extracted report text (for context — you should prioritize the explicit entities and lab values above):
\"\"\"{extracted_text[:4000]}\"\"\"

Return output as JSON ONLY in this exact format:
{{"clinical_summary": "A short 1-4 sentence clinician-facing summary."}}

Do not add any extra keys, commentary, or markdown. If you cannot produce JSON, return plain text summary only.
"""

    try:
        resp = model.invoke(prompt)
        out = getattr(resp, "text", "") or str(resp)
        out = out.strip()

        # remove triple-backtick fences if present
        if out.startswith("```"):
            # find the content inside fences
            parts = out.split("```")
            if len(parts) >= 3:
                out = parts[2].strip() if parts[1].strip(
                ).lower() == "json" else parts[1].strip()

        # try to find JSON object in output
        m = re.search(
            r"(\{\s*\"clinical_summary\"\s*:\s*\".*?\"\s*\})", out, flags=re.S)
        json_str = m.group(1) if m else out

        try:
            parsed = json.loads(json_str)
            summary_text = parsed.get("clinical_summary", "")
            if isinstance(summary_text, str) and summary_text.strip():
                return summary_text.strip()
        except json.JSONDecodeError:
            # fallback to plain text (strip any labels)
            pass

        # If no JSON or parsing failed, try to extract first 1-4 sentences from the raw output
        # Simple sentence split (keeps it short)
        sentences = re.split(r'(?<=[\.\?\!])\s+', out)
        summary_text = " ".join(sentences[:max_sentences]).strip()
        return summary_text
    except Exception as e:
        # Don't crash — return empty string so caller can fallback
        print(f"[generate_summary] Gemini/exception: {e}")
        return ""

# ===========================


def extract_labs_with_rag(text: str):
    candidates = retrieve_lab_candidates(text, top_k=10)
    context = "\n".join([
        f"{c['test']}: {c['description']}. Unit: {c['unit']}. Normal range: {c['normal_range']}"
        for c in candidates
    ])

    prompt = f"""You are a medical lab results extraction assistant. Extract ONLY actual laboratory test results from the text below.

IMPORTANT RULES:
1. Extract ONLY actual lab test names with numeric values (e.g., "Glucose: 95 mg/dL", "Creatinine: 1.2 mg/dL")
2. DO NOT extract:
   - Page numbers (e.g., "Page 2", "Page 3 of 3")
   - Dates (e.g., "2020", "2025")
   - Reference numbers (e.g., "Ref: 14", "Ref 2020")
   - Patient info (e.g., "Age: 72", "DOB: 16/05/1952")
   - Department names (e.g., "DEPT", "DEPARTMENTS")
   - Single letters or numbers (e.g., "A", "1", "2")
   - Common words (e.g., "Source", "Type", "No", "Collected", "Printed")
   - Addresses or locations (e.g., "JALAN", "SEL 46300")
   - Section headers or labels

3. Only extract if you see:
   - A recognized lab test name (like Glucose, Creatinine, Hemoglobin, etc.)
   - Followed by a colon or equals sign
   - Followed by a numeric value
   - Optionally followed by a unit (mg/dL, mmol/L, g/dL, %, U/L, etc.)

Reference lab tests you should look for:
{context}

Extract from this lab report and return ONLY a valid JSON array. Return an empty array [] if no valid lab results are found.
Format: [{{"test":"Lab Test Name","value":"123.45","unit":"mg/dL","normal_range":"70-110"}}]

Text to analyze:
{text}

Return ONLY the JSON array, nothing else:
"""

    try:
        # NOTE: method name depends on genai SDK version; using generate_content per your code
        response = model.invoke(prompt)
        content = getattr(response, "text", "") or str(response)
        # strip common fences
        content = content.strip()
        if content.startswith("```"):
            # remove any fence and possible language tag
            parts = content.split("```", 2)
            # parts[0] is empty, parts[1] may be "json" or the content - try to find JSON-looking part
            content = parts[-1].strip()
        # Find the first JSON array in the response
        import re
        m = re.search(r"(\[\s*\{.*\}\s*\])", content, re.S)
        json_str = m.group(1) if m else content
        labs = json.loads(json_str) if json_str.strip().startswith("[") else []
    except Exception as e:
        print(f"Gemini parsing error: {e}")
        labs = []

    entities: List[Entity] = []
    seen = set()  # Track seen labs to avoid duplicates
    
    for lab in labs:
        test_name = lab.get("test", "").strip()
        value = lab.get("value", "").strip()
        
        # Validate the extracted lab result
        if not test_name or not value:
            continue
        
        # Additional validation
        if not is_valid_lab_result(test_name, value):
            continue
        
        # Create unique key to avoid duplicates
        key = f"{test_name.lower()}:{value}"
        if key in seen:
            continue
        seen.add(key)
        
        entities.append(Entity(
            text=test_name,
            start=lab.get("start", 0) or 0,
            end=lab.get("end", 0) or 0,
            entity_type="lab",
            confidence=float(lab.get("confidence", 0.9)) if lab.get(
                "confidence") is not None else 0.9,
            value=value,
            unit=lab.get("unit"),
            normal_range=lab.get("normal_range")
        ))

    return entities

# -----------------------
# Sliding window function
# ------------------------


def predict_with_sliding_window(text, tokenizer, model, label_map, max_length, stride=128, prob_threshold=0.0):
    """
    Token-classification sliding-window prediction.
    - 'model' should already be moved to device (we moved d_model at load time).
    - Tensors are moved to 'device' for inference.
    """
    model.eval()

    encoded = tokenizer(
        text,
        return_offsets_mapping=True,
        truncation=True,
        max_length=max_length,
        stride=stride,
        return_overflowing_tokens=True,
        return_tensors="pt",
        padding="max_length"
    )

    all_preds = []
    with torch.no_grad():
        for i in range(encoded["input_ids"].size(0)):
            ids = encoded["input_ids"][i].unsqueeze(0).to(device)
            mask = encoded["attention_mask"][i].unsqueeze(0).to(device)
            offsets = encoded["offset_mapping"][i].cpu().tolist()
            mask_list = encoded["attention_mask"][i].cpu().tolist()

            outputs = model(input_ids=ids, attention_mask=mask)
            logits = outputs.logits[0].cpu().numpy()

            exp = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
            probs = exp / np.sum(exp, axis=-1, keepdims=True)
            pred_ids = np.argmax(probs, axis=-1)
            pred_scores = probs.max(axis=-1)

            for token_idx, (pred_id, score, offset, m) in enumerate(zip(pred_ids, pred_scores, offsets, mask_list)):
                if m == 0 or offset[0] == offset[1]:
                    continue
                label_name = label_map.get(int(pred_id), "O")
                if label_name == "O":
                    continue
                all_preds.append(
                    {"start": offset[0], "end": offset[1], "label": label_name, "score": float(score)})

    # Merge consecutive disease tokens (B-Disease and I-Disease)
    all_preds = sorted(all_preds, key=lambda x: (x["start"], x["end"]))
    merged = []
    
    for p in all_preds:
        if not merged:
            merged.append(p.copy())
            continue
        
        last = merged[-1]
        
        # Check if both are disease labels (B-Disease or I-Disease)
        is_disease_current = p["label"] in ["B-Disease", "I-Disease"]
        is_disease_last = last["label"] in ["B-Disease", "I-Disease"]
        
        # Merge if:
        # 1. Both are disease labels (B-Disease or I-Disease) and adjacent/overlapping
        # 2. Same label and overlapping
        # 3. Adjacent tokens (within 3 characters to account for whitespace/punctuation)
        gap = p["start"] - last["end"]
        is_adjacent = gap <= 3  # Allow small gap for whitespace/punctuation
        
        if (is_disease_current and is_disease_last and is_adjacent) or \
           (p["label"] == last["label"] and (p["start"] <= last["end"] or is_adjacent)):
            # Merge: extend the end position and update score (use max or average)
            last["end"] = max(last["end"], p["end"])
            # Use average score for merged entities
            last["score"] = (last["score"] + p["score"]) / 2.0
            # Keep the label as B-Disease if either was B-Disease, otherwise I-Disease
            if last["label"] == "B-Disease" or p["label"] == "B-Disease":
                last["label"] = "B-Disease"
            else:
                last["label"] = "I-Disease"
        else:
            merged.append(p.copy())
    
    # Filter by threshold and extract text
    result = []
    for p in merged:
        if p["score"] >= prob_threshold:
            extracted_text = text[p["start"]:p["end"]].strip()
            # Only include if text is not empty
            if extracted_text:
                result.append({
                    "text": extracted_text,
                    "start": p["start"],
                    "end": p["end"],
                    "entity_type": "Disease",  # Normalize to "Disease" for output
                    "confidence": round(p["score"], 4)
                })
    
    return result

# ----------------------------
# Storage Functions
# ----------------------------


def store_medical_record(
    original_filename: str,
    extracted_text: str,
    diseases: List[Entity],
    lab_results: List[Entity],
    summary: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    patient_id: Optional[str] = None,
    source: str = "pdf_upload"
):
    """
    Store processed medical record in MongoDB.
    Returns the inserted document ID if successful, None otherwise.
    """
    print(
        f"DEBUG in store_medical_record: records_collection id = {id(records_collection)}, value = {records_collection}")
    print(
        f"DEBUG in store_medical_record: Is records_collection None? {records_collection is None}")
    if records_collection is None:
        print("❌ Storage disabled: MongoDB not connected (records_collection is None)")
        return None

    try:
        # Generate patient ID if not provided
        if not patient_id:
            patient_id = f"patient_{datetime.now().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}"

        record = {
            "patient_id": patient_id,
            "original_filename": original_filename,
            "extracted_text": extracted_text,
            "diseases": [disease.dict() for disease in diseases],
            "lab_results": [lab.dict() for lab in lab_results],
            "summary": summary,
            "metadata": metadata or {},
            "upload_timestamp": datetime.now().isoformat(),
            "source": source,
            "diseases_count": len(diseases),
            "labs_count": len(lab_results)
        }

        print(f"DEBUG: Attempting to insert record for patient {patient_id}")
        result = records_collection.insert_one(record)
        print(
            f"✅ Stored record for patient {patient_id} with ID: {result.inserted_id}")
        return str(result.inserted_id)

    except Exception as e:
        print(f"❌ Error storing record: {e}")
        import traceback
        traceback.print_exc()
        return None  # Auth Helper Functions


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)  # Auth Helper Functions


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = users_db.get(username)
    if user is None:
        raise credentials_exception
    return User(**{k: v for k, v in user.items() if k != "hashed_password"})


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Create OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = users_db.get(username)
    if user is None:
        raise credentials_exception
    return User(**{k: v for k, v in user.items() if k != "hashed_password"})


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Create OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Auth Helper Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = users_db.get(username)
    if user is None:
        raise credentials_exception
    return User(**{k: v for k, v in user.items() if k != "hashed_password"})


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Create OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ----------------------------
# Predict Endpoints
# ----------------------------


@app.post("/predict", response_model=CombinedNERResponse)
async def predict_combined_rag(req: TextRequest, store: bool = Form(False),
                               patient_id: Optional[str] = Form(None)):
    req_start = time.time()
    text = req.text
    icd_map = req.icd_map

    # Disease NER
    if len(text.split()) < DISEASE_MAX_LEN:
        disease_preds = d_pipeline(text)
        # Post-process pipeline results to merge adjacent disease tokens
        # The pipeline should handle this, but we add extra merging for safety
        merged_preds = []
        for p in disease_preds:
            if not merged_preds:
                merged_preds.append(p.copy() if isinstance(p, dict) else p)
                continue
            
            last = merged_preds[-1]
            # Get entity group/label (pipeline uses "entity_group" after aggregation)
            current_label = str(p.get("entity_group") or p.get("entity") or "").lower()
            last_label = str(last.get("entity_group") or last.get("entity") or "").lower()
            
            # Check if both are disease entities
            is_disease = "disease" in current_label
            is_last_disease = "disease" in last_label
            
            current_start = p.get("start", 0)
            current_end = p.get("end", 0)
            last_end = last.get("end", 0)
            
            gap = current_start - last_end
            
            # Merge if both are diseases and adjacent (within 3 chars for whitespace)
            if is_disease and is_last_disease and gap <= 3:
                # Merge: combine text and extend end position
                last_text = last.get("word") or last.get("entity") or ""
                current_text = p.get("word") or p.get("entity") or ""
                # Only add space if there's a gap
                if gap > 0:
                    merged_text = (last_text + " " + current_text).strip()
                else:
                    merged_text = (last_text + current_text).strip()
                last["word"] = merged_text
                last["entity"] = merged_text
                last["end"] = max(last_end, current_end)
                # Average the scores
                last_score = last.get("score", 0.0)
                current_score = p.get("score", 0.0)
                last["score"] = (last_score + current_score) / 2.0
            else:
                merged_preds.append(p.copy() if isinstance(p, dict) else p)
        
        diseases = [
            Entity(
                text=p.get("word") or p.get("entity"),
                start=p.get("start", 0),
                end=p.get("end", 0),
                entity_type=p.get("entity_group") or p.get("entity"),
                icd_code=normalize_icd(p.get("word") or p.get(
                    "entity")) if icd_map else None,
                confidence=float(p.get("score", 0.0))
            ) for p in merged_preds
        ]
    else:
        diseases = [Entity(**p, icd_code=normalize_icd(p['text']) if icd_map else None)
                    for p in predict_with_sliding_window(text, d_tokenizer, d_model, d_label_map, DISEASE_MAX_LEN)]

    # Lab extraction via RAG
    lab_results = extract_labs_with_rag(text) + extract_labs_with_regex(text)

    processing_time_ms = int((time.time() - req_start) * 1000)

    metadata = {
        "input_source": "text",
        "processing_time_ms": processing_time_ms,
        "service_start_time_epoch": IMPORT_TIME_EPOCH,
        "service_start_time_iso": IMPORT_TIME_ISO,
    }

    summary_text = generate_summary(text, diseases, lab_results)
    summary_block = {
        "clinical_summary": summary_text} if summary_text else None

    print(f"{metadata, text, diseases, lab_results, summary_block}")

    # STORE RECORD IF REQUESTED
    if store and records_collection is not None:
        store_medical_record(
            original_filename="text_input.txt",
            extracted_text=text,
            diseases=diseases,
            lab_results=lab_results,
            summary=summary_block,
            metadata=metadata,
            patient_id=patient_id,
            source="text_input"
        )

    return CombinedNERResponse(
        metadata=metadata,
        text=text,
        diseases=diseases,
        lab_results=lab_results,
        summary=summary_block
    )


@app.post("/predict_pdf", response_model=CombinedNERResponse)
async def predict_combined_pdf(file: UploadFile = File(...), icd_map: bool = Form(False), store: bool = Form(False), patient_id: Optional[str] = Form(None)):
    req_start = time.time()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        text = extract_text_from_pdf(tmp_path)
        if not text.strip():
            metadata = {
                "input_source": "uploaded_pdf",
                "processing_time_ms": int((time.time() - req_start) * 1000),
                "service_start_time_epoch": IMPORT_TIME_EPOCH,
                "service_start_time_iso": IMPORT_TIME_ISO,
            }
            return CombinedNERResponse(metadata=metadata, text="", diseases=[], lab_results=[])

        diseases = [Entity(**p, icd_code=normalize_icd(p['text']) if icd_map else None)
                    for p in predict_with_sliding_window(text, d_tokenizer, d_model, d_label_map, DISEASE_MAX_LEN)]
        lab_results = extract_labs_with_rag(
            text) + extract_labs_with_regex(text)

        processing_time_ms = int((time.time() - req_start) * 1000)

        metadata = {
            "input_source": "uploaded_pdf",
            "processing_time_ms": processing_time_ms,
            "service_start_time_epoch": IMPORT_TIME_EPOCH,
            "service_start_time_iso": IMPORT_TIME_ISO,
        }

        summary_text = generate_summary(text, diseases, lab_results)
        summary_block = {
            "clinical_summary": summary_text} if summary_text else None

        print(f"{metadata, text, diseases, lab_results, summary_block}")

        # STORE RECORD IF REQUESTED
        if store and records_collection is not None:
            store_medical_record(
                original_filename=file.filename,
                extracted_text=text,
                diseases=diseases,
                lab_results=lab_results,
                summary=summary_block,
                metadata=metadata,
                patient_id=patient_id,
                source="pdf_upload"
            )

        return CombinedNERResponse(
            metadata=metadata,
            text=text,
            diseases=diseases,
            lab_results=lab_results,
            summary=summary_block
        )

    finally:
        os.remove(tmp_path)


# Multi document endpoint
@app.post("/predict_multiple_pdfs", response_model=List[CombinedNERResponse])
async def predict_multiple_pdfs(
    files: List[UploadFile] = File(...), 
    icd_map: bool = Form(False),
    store: bool = Form(False),
    patient_id: Optional[str] = Form(None)
):
    """
    Process multiple PDFs in one request.
    Returns a list of responses, one per document.
    """
    responses = []

    for file in files:
        req_start = time.time()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        try:
            # Extract text from PDF (your existing function)
            text = extract_text_from_pdf(tmp_path)
            if not text.strip():
                responses.append(CombinedNERResponse(
                    metadata={
                        "input_source": "uploaded_pdf",
                        "processing_time_ms": int((time.time() - req_start) * 1000),
                        "service_start_time_epoch": IMPORT_TIME_EPOCH,
                        "service_start_time_iso": IMPORT_TIME_ISO,
                        "original_filename": file.filename
                    },
                    text="",
                    diseases=[],
                    lab_results=[]
                ))
                continue

            # Disease NER (your existing logic)
            diseases = [Entity(**p, icd_code=normalize_icd(p['text']) if icd_map else None)
                        for p in predict_with_sliding_window(text, d_tokenizer, d_model, d_label_map, DISEASE_MAX_LEN)]

            # Lab extraction (your existing logic)
            lab_results = extract_labs_with_rag(
                text) + extract_labs_with_regex(text)

            processing_time_ms = int((time.time() - req_start) * 1000)

            summary_text = generate_summary(text, diseases, lab_results)
            summary_block = {
                "clinical_summary": summary_text} if summary_text else None

            responses.append(CombinedNERResponse(
                metadata={
                    "input_source": "uploaded_pdf",
                    "processing_time_ms": processing_time_ms,
                    "service_start_time_epoch": IMPORT_TIME_EPOCH,
                    "service_start_time_iso": IMPORT_TIME_ISO,
                    "original_filename": file.filename
                },
                text=text,
                diseases=diseases,
                lab_results=lab_results,
                summary=summary_block
            ))

            # ADD STORAGE AFTER PROCESSING EACH DOCUMENT (only if store=True)
            if store and records_collection is not None:
                store_medical_record(
                    original_filename=file.filename,
                    extracted_text=text,
                    diseases=diseases,
                    lab_results=lab_results,
                    summary=summary_block,
                    metadata={
                        "input_source": "uploaded_pdf",
                        "processing_time_ms": processing_time_ms,
                        "service_start_time_epoch": IMPORT_TIME_EPOCH,
                        "service_start_time_iso": IMPORT_TIME_ISO,
                        "original_filename": file.filename
                    },
                    patient_id=patient_id,
                    source="multi_pdf_upload"
                )

        finally:
            os.remove(tmp_path)

    return responses


# Cross document summary
@app.post("/predict_multiple_pdfs_summary")
async def predict_multiple_pdfs_consolidated(
    files: List[UploadFile] = File(...), 
    icd_map: bool = Form(False),
    store: bool = Form(False),
    patient_id: Optional[str] = Form(None)
):
    """
    Process multiple PDFs and return a single consolidated summary.
    """
    # First get individual document responses
    responses = await predict_multiple_pdfs(files, icd_map, store, patient_id)

    # Combine all entities and texts for consolidated summary
    all_texts = []
    all_diseases = []
    all_labs = []
    filenames = []

    for i, resp in enumerate(responses):
        all_texts.append(
            f"[Document {i+1}: {resp.metadata.get('original_filename', f'doc_{i+1}')}]\n{resp.text}")
        all_diseases.extend(resp.diseases)
        all_labs.extend(resp.lab_results)
        filenames.append(resp.metadata.get('original_filename', f'doc_{i+1}'))

    # Generate a consolidated summary
    consolidated_text = "\n\n---\n\n".join(all_texts)

    consolidated_summary = generate_summary(
        consolidated_text[:4000],  # Truncate to avoid token limits
        all_diseases,
        all_labs
    )

    return {
        "metadata": {
            "total_documents": len(responses),
            "filenames": filenames,
            "total_diseases_found": len(all_diseases),
            "total_labs_found": len(all_labs),
            "service_start_time_iso": IMPORT_TIME_ISO
        },
        "documents": responses,
        "consolidated_summary": consolidated_summary
    }

# ----------------------------
# Storage Endpoints
# ----------------------------


# ----------------------------
# Storage Endpoints (IN THIS ORDER!)
# ----------------------------
@app.get("/records/stats")
async def get_storage_stats():
    """Get basic storage statistics"""
    if records_collection is None:
        return {"status": "error", "message": "Storage not available", "storage_available": False}

    try:
        total_records = records_collection.count_documents({})

        # Get most common diseases (handle empty database)
        top_diseases = []
        top_labs = []

        if total_records > 0:
            # Get most common diseases
            disease_pipeline = [
                {"$unwind": "$diseases"},
                {"$group": {"_id": "$diseases.text", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            top_diseases_cursor = records_collection.aggregate(
                disease_pipeline)
            top_diseases = [{"name": d["_id"], "count": d["count"]}
                            for d in top_diseases_cursor]

            # Get most common lab tests
            lab_pipeline = [
                {"$unwind": "$lab_results"},
                {"$group": {"_id": "$lab_results.text", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            top_labs_cursor = records_collection.aggregate(lab_pipeline)
            top_labs = [{"name": l["_id"], "count": l["count"]}
                        for l in top_labs_cursor]

        return {
            "status": "success",
            "total_records": total_records,
            "top_diseases": top_diseases,
            "top_labs": top_labs,
            "storage_available": True
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            "status": "error",
            "message": str(e),
            "storage_available": True
        }


@app.post("/records/search", response_model=List[StoredRecord])
async def search_records(query: SearchQuery):
    """Search records by disease name or lab test"""
    if records_collection is None:
        return []

    try:
        search_filter = {}

        if query.disease_name:
            search_filter["diseases.text"] = {
                "$regex": query.disease_name, "$options": "i"}

        if query.lab_test:
            search_filter["lab_results.text"] = {
                "$regex": query.lab_test, "$options": "i"}

        if query.date_from and query.date_to:
            search_filter["upload_timestamp"] = {
                "$gte": query.date_from,
                "$lte": query.date_to
            }

        records = list(records_collection.find(search_filter).sort(
            "upload_timestamp", -1).limit(query.limit))

        formatted_records = []
        for record in records:
            summary_preview = ""
            if record.get("summary") and isinstance(record["summary"], dict):
                summary_preview = record["summary"].get(
                    "clinical_summary", "")[:100] + "..."

            formatted_records.append(StoredRecord(
                id=str(record["_id"]),
                patient_id=record.get("patient_id", "unknown"),
                original_filename=record.get("original_filename", "unknown"),
                upload_timestamp=record.get("upload_timestamp", ""),
                diseases_count=record.get("diseases_count", 0),
                labs_count=record.get("labs_count", 0),
                summary_preview=summary_preview
            ))

        return formatted_records
    except Exception as e:
        print(f"Error searching records: {e}")
        return []


@app.get("/records", response_model=List[StoredRecord])
async def get_all_records(skip: int = 0, limit: int = 50):
    """Get all stored records (paginated)"""
    if records_collection is None:
        return []

    try:
        records = list(records_collection.find().sort(
            "upload_timestamp", -1).skip(skip).limit(limit))

        formatted_records = []
        for record in records:
            summary_preview = ""
            if record.get("summary") and isinstance(record["summary"], dict):
                summary_preview = record["summary"].get(
                    "clinical_summary", "")[:100] + "..."
            elif isinstance(record.get("summary"), str):
                summary_preview = record["summary"][:100] + "..."

            formatted_records.append(StoredRecord(
                id=str(record["_id"]),
                patient_id=record.get("patient_id", "unknown"),
                original_filename=record.get("original_filename", "unknown"),
                upload_timestamp=record.get("upload_timestamp", ""),
                diseases_count=record.get("diseases_count", 0),
                labs_count=record.get("labs_count", 0),
                summary_preview=summary_preview
            ))

        return formatted_records
    except Exception as e:
        print(f"Error fetching records: {e}")
        return []

# THIS MUST BE LAST!


@app.get("/records/{record_id}", response_model=RecordDetail)
async def get_record(record_id: str):
    """Get a single record by ID"""
    if records_collection is None:
        # Return an error response, not None
        return RecordDetail(
            id="",
            patient_id="",
            original_filename="",
            upload_timestamp="",
            diseases_count=0,
            labs_count=0,
            summary_preview="Error: Storage not available",
            extracted_text="",
            diseases=[],
            lab_results=[],
            summary=None,
            metadata={}
        )

    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(record_id):
            return RecordDetail(
                id=record_id,
                patient_id="",
                original_filename="",
                upload_timestamp="",
                diseases_count=0,
                labs_count=0,
                summary_preview="Error: Invalid record ID",
                extracted_text="",
                diseases=[],
                lab_results=[],
                summary=None,
                metadata={}
            )

        record = records_collection.find_one({"_id": ObjectId(record_id)})
        if not record:
            return RecordDetail(
                id=record_id,
                patient_id="",
                original_filename="",
                upload_timestamp="",
                diseases_count=0,
                labs_count=0,
                summary_preview="Error: Record not found",
                extracted_text="",
                diseases=[],
                lab_results=[],
                summary=None,
                metadata={}
            )

        # Convert entities back to Entity objects
        diseases = [Entity(**d) for d in record.get("diseases", [])]
        lab_results = [Entity(**l) for l in record.get("lab_results", [])]

        summary_preview = ""
        summary_obj = None
        if record.get("summary"):
            if isinstance(record["summary"], dict):
                summary_preview = record["summary"].get(
                    "clinical_summary", "")[:100] + "..."
                summary_obj = record["summary"]
            elif isinstance(record["summary"], str):
                summary_preview = record["summary"][:100] + "..."
                summary_obj = {"clinical_summary": record["summary"]}

        return RecordDetail(
            id=str(record["_id"]),
            patient_id=record.get("patient_id", "unknown"),
            original_filename=record.get("original_filename", "unknown"),
            upload_timestamp=record.get("upload_timestamp", ""),
            diseases_count=record.get("diseases_count", 0),
            labs_count=record.get("labs_count", 0),
            summary_preview=summary_preview,
            extracted_text=record.get("extracted_text", ""),
            diseases=diseases,
            lab_results=lab_results,
            summary=summary_obj,
            metadata=record.get("metadata", {})
        )
    except Exception as e:
        print(f"Error fetching record {record_id}: {e}")
        return RecordDetail(
            id=record_id,
            patient_id="",
            original_filename="",
            upload_timestamp="",
            diseases_count=0,
            labs_count=0,
            summary_preview=f"Error: {str(e)}",
            extracted_text="",
            diseases=[],
            lab_results=[],
            summary=None,
            metadata={}
        )


@app.get("/test_mongo")
async def test_mongo():
    """Test MongoDB connection"""
    if records_collection is None:
        return {"status": "not_connected", "message": "MongoDB collection is None"}

    try:
        # Try to count documents
        count = records_collection.count_documents({})
        return {
            "status": "connected",
            "count": count,
            "collection_name": records_collection.name,
            "database_name": records_collection.database.name
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------------------
# Analytics Endpoints
# ----------------------------
@app.get("/analytics/summary")
async def get_analytics_summary():
    """Get overall analytics summary"""
    if records_collection is None:
        return {"error": "Storage not available"}

    try:
        # Total counts
        total_records = records_collection.count_documents({})

        # Aggregate disease and lab counts
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_diseases": {"$sum": "$diseases_count"},
                    "total_labs": {"$sum": "$labs_count"},
                    "earliest_date": {"$min": "$upload_timestamp"},
                    "latest_date": {"$max": "$upload_timestamp"}
                }
            }
        ]

        agg_result = list(records_collection.aggregate(pipeline))

        if agg_result and total_records > 0:
            result = agg_result[0]
            avg_diseases = result["total_diseases"] / total_records
            avg_labs = result["total_labs"] / total_records

            date_range = {}
            if result.get("earliest_date"):
                date_range["start"] = result["earliest_date"]
            if result.get("latest_date"):
                date_range["end"] = result["latest_date"]

            return AnalyticsSummary(
                total_records=total_records,
                total_diseases=result["total_diseases"],
                total_labs=result["total_labs"],
                avg_diseases_per_record=round(avg_diseases, 2),
                avg_labs_per_record=round(avg_labs, 2),
                date_range=date_range
            )
        else:
            return AnalyticsSummary(
                total_records=0,
                total_diseases=0,
                total_labs=0,
                avg_diseases_per_record=0,
                avg_labs_per_record=0
            )

    except Exception as e:
        print(f"Error in analytics summary: {e}")
        return {"error": str(e)}


@app.get("/analytics/top_entities")
async def get_top_entities(limit: int = 10):
    """Get most frequent diseases and lab tests"""
    if records_collection is None:
        return {"error": "Storage not available"}

    try:
        # Top diseases
        disease_pipeline = [
            {"$unwind": "$diseases"},
            {"$group": {
                "_id": "$diseases.text",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]

        top_diseases = []
        disease_results = list(records_collection.aggregate(disease_pipeline))
        total_disease_mentions = sum(d["count"] for d in disease_results)

        for d in disease_results:
            percentage = (d["count"] / total_disease_mentions *
                          100) if total_disease_mentions > 0 else 0
            top_diseases.append(DiseaseFrequency(
                disease_name=d["_id"],
                count=d["count"],
                percentage=round(percentage, 1)
            ))

        # Top labs
        lab_pipeline = [
            {"$unwind": "$lab_results"},
            {"$group": {
                "_id": "$lab_results.text",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]

        top_labs = []
        lab_results = list(records_collection.aggregate(lab_pipeline))
        total_lab_mentions = sum(l["count"] for l in lab_results)

        for l in lab_results:
            percentage = (l["count"] / total_lab_mentions *
                          100) if total_lab_mentions > 0 else 0
            top_labs.append(LabFrequency(
                lab_name=l["_id"],
                count=l["count"],
                percentage=round(percentage, 1)
            ))

        return {
            "top_diseases": top_diseases,
            "top_labs": top_labs
        }

    except Exception as e:
        print(f"Error in top entities: {e}")
        return {"error": str(e)}


@app.get("/analytics/trends")
async def get_analytics_trends(days: int = 30):
    """Get upload trends over time"""
    if records_collection is None:
        return {"error": "Storage not available"}

    try:
        # Get upload trend (records per day)
        pipeline = [
            {
                "$project": {
                    "date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": {"$toDate": "$upload_timestamp"}
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": "$date",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}},
            {"$limit": days}
        ]

        trend_results = list(records_collection.aggregate(pipeline))

        upload_trend = []
        for t in trend_results:
            upload_trend.append(TimeSeriesPoint(
                date=t["_id"],
                count=t["count"]
            ))

        # Get disease frequency trend (optional)
        disease_trend = []
        try:
            disease_pipeline = [
                {"$unwind": "$diseases"},
                {
                    "$project": {
                        "date": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": {"$toDate": "$upload_timestamp"}
                            }
                        },
                        "disease": "$diseases.text"
                    }
                },
                {
                    "$group": {
                        "_id": {"date": "$date", "disease": "$disease"},
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"_id.date": 1}},
                {"$limit": 100}
            ]

            disease_trend_results = list(
                records_collection.aggregate(disease_pipeline))

            # Group by date for top diseases
            date_groups = {}
            for dt in disease_trend_results:
                date = dt["_id"]["date"]
                disease = dt["_id"]["disease"]
                count = dt["count"]

                if date not in date_groups:
                    date_groups[date] = []

                date_groups[date].append({
                    "disease": disease,
                    "count": count
                })

            # Get top disease for each date
            for date, diseases in date_groups.items():
                if diseases:
                    top_disease = max(diseases, key=lambda x: x["count"])
                    disease_trend.append(TimeSeriesPoint(
                        date=date,
                        count=top_disease["count"]
                    ))
        except Exception as e:
            print(f"Error getting disease trend: {e}")
            # Continue without disease trend

        return {
            "upload_trend": upload_trend,
            "disease_trend": disease_trend[:days]  # Limit to same days
        }

    except Exception as e:
        print(f"Error in trends: {e}")
        return {"error": str(e)}


@app.get("/analytics/outbreak_detection")
async def get_outbreak_detection(threshold: float = 2.0):
    """Detect potential outbreaks based on disease frequency spikes"""
    if records_collection is None:
        return {"error": "Storage not available"}

    try:
        # Get disease frequency per day for last 14 days
        pipeline = [
            {
                "$match": {
                    "upload_timestamp": {
                        "$gte": datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=14)
                    }
                }
            },
            {"$unwind": "$diseases"},
            {
                "$project": {
                    "date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": {"$toDate": "$upload_timestamp"}
                        }
                    },
                    "disease": "$diseases.text"
                }
            },
            {
                "$group": {
                    "_id": {"date": "$date", "disease": "$disease"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id.date": 1}}
        ]

        results = list(records_collection.aggregate(pipeline))

        # Group by disease
        disease_data = {}
        for r in results:
            disease = r["_id"]["disease"]
            date = r["_id"]["date"]
            count = r["count"]

            if disease not in disease_data:
                disease_data[disease] = {}

            disease_data[disease][date] = count

        # Check for spikes
        potential_outbreaks = []
        for disease, dates in disease_data.items():
            if len(dates) < 3:  # Need at least 3 data points
                continue

            # Get values for last 3 days
            sorted_dates = sorted(dates.keys())
            if len(sorted_dates) >= 3:
                last_3_days = sorted_dates[-3:]
                counts = [dates.get(day, 0) for day in last_3_days]

                # Check if latest day is significantly higher
                if counts[-1] > 0 and counts[-2] > 0:
                    increase_ratio = counts[-1] / counts[-2]

                    if increase_ratio >= threshold:
                        potential_outbreaks.append({
                            "disease": disease,
                            "date": last_3_days[-1],
                            "count": counts[-1],
                            "previous_count": counts[-2],
                            "increase_ratio": round(increase_ratio, 2),
                            "severity": "HIGH" if increase_ratio >= 3 else "MEDIUM" if increase_ratio >= 2 else "LOW"
                        })

        # Sort by severity and ratio
        potential_outbreaks.sort(key=lambda x: (
            x["severity"], x["increase_ratio"]), reverse=True)

        return {
            "potential_outbreaks": potential_outbreaks[:10],  # Top 10
            "threshold": threshold,
            "analysis_period_days": 14
        }

    except Exception as e:
        print(f"Error in outbreak detection: {e}")
        return {"error": str(e)}


# ----------------------------
# Screening Endpoints
# ----------------------------
@app.get("/screening/rules")
async def get_screening_rules():
    """Get all screening rules"""
    return SCREENING_RULES


@app.post("/screening/analyze")
async def analyze_screening(request: ScreeningRequest):
    """Run screening analysis on records"""
    if records_collection is None:
        return {"error": "Storage not available"}

    try:
        # Build query based on request
        query = {}
        if request.record_id:
            if ObjectId.is_valid(request.record_id):
                query["_id"] = ObjectId(request.record_id)
        elif request.patient_id:
            query["patient_id"] = request.patient_id

        # Get records to analyze
        if request.run_all:
            records = list(records_collection.find(
                {}).sort("upload_timestamp", -1).limit(100))
        else:
            records = list(records_collection.find(
                query).sort("upload_timestamp", -1).limit(10))

        if not records:
            return {"message": "No records found for screening", "results": []}

        results = []
        for record in records:
            screening_result = run_screening_on_record(record)
            results.append(screening_result)

        # Calculate summary statistics
        risk_counts = {
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        }

        for result in results:
            risk_counts[result["risk_level"]] += 1

        return {
            "summary": {
                "total_records_screened": len(results),
                "high_risk": risk_counts["HIGH"],
                "medium_risk": risk_counts["MEDIUM"],
                "low_risk": risk_counts["LOW"]
            },
            "results": results
        }

    except Exception as e:
        print(f"Error in screening analysis: {e}")
        return {"error": str(e)}


@app.post("/screening/analyze_record/{record_id}")
async def analyze_single_record(record_id: str):
    """Run screening on a single record"""
    if records_collection is None:
        return {"error": "Storage not available"}

    try:
        if not ObjectId.is_valid(record_id):
            return {"error": "Invalid record ID"}

        record = records_collection.find_one({"_id": ObjectId(record_id)})
        if not record:
            return {"error": "Record not found"}

        result = run_screening_on_record(record)
        return result

    except Exception as e:
        print(f"Error screening record: {e}")
        return {"error": str(e)}


def run_screening_on_record(record):
    """Run all screening rules on a single record"""
    triggered_rules = []
    recommendations = []
    max_risk_level = "LOW"

    # Extract diseases and labs
    diseases = [d.get("text", "").lower() for d in record.get("diseases", [])]
    labs = {}

    for lab in record.get("lab_results", []):
        lab_name = lab.get("text", "").lower()
        lab_value = lab.get("value")
        if lab_name and lab_value:
            try:
                # Try to parse numeric value
                if isinstance(lab_value, str):
                    # Extract numbers from string
                    numbers = re.findall(r'\d+\.?\d*', lab_value)
                    if numbers:
                        labs[lab_name] = float(numbers[0])
                else:
                    labs[lab_name] = float(lab_value)
            except:
                labs[lab_name] = None

    # Check each rule
    for rule in SCREENING_RULES:
        rule_triggered = True

        for condition in rule.get("conditions", []):
            cond_type = condition.get("type")
            cond_value = condition.get("value")
            operator = condition.get("operator", "contains")

            if cond_type == "disease":
                # Check if disease is present
                disease_found = any(cond_value.lower()
                                    in disease for disease in diseases)
                if operator == "contains" and not disease_found:
                    rule_triggered = False
                    break
                elif operator == "not_contains" and disease_found:
                    rule_triggered = False
                    break

            elif cond_type == "lab":
                # Check if lab test is present
                lab_found = any(cond_value.lower()
                                in lab_name for lab_name in labs.keys())
                if operator == "contains" and not lab_found:
                    rule_triggered = False
                    break
                elif operator == "not_contains" and lab_found:
                    rule_triggered = False
                    break

            elif cond_type == "lab_value":
                # Check lab value against threshold
                lab_name = condition.get("lab_name", "").lower()
                threshold = float(cond_value)
                unit = condition.get("unit", "")

                # Find matching lab
                lab_value = None
                for lab_key in labs.keys():
                    if lab_name in lab_key:
                        lab_value = labs[lab_key]
                        break

                if lab_value is None:
                    rule_triggered = False
                    break

                if operator == "greater_than" and not (lab_value > threshold):
                    rule_triggered = False
                    break
                elif operator == "less_than" and not (lab_value < threshold):
                    rule_triggered = False
                    break
                elif operator == "greater_than_equal" and not (lab_value >= threshold):
                    rule_triggered = False
                    break
                elif operator == "less_than_equal" and not (lab_value <= threshold):
                    rule_triggered = False
                    break

            elif cond_type == "disease_count":
                threshold = int(cond_value)
                if operator == "greater_than" and not (len(diseases) > threshold):
                    rule_triggered = False
                    break
                elif operator == "greater_than_equal" and not (len(diseases) >= threshold):
                    rule_triggered = False
                    break
                elif operator == "less_than" and not (len(diseases) < threshold):
                    rule_triggered = False
                    break
                elif operator == "less_than_equal" and not (len(diseases) <= threshold):
                    rule_triggered = False
                    break

        if rule_triggered:
            triggered_rules.append({
                "rule_id": rule["id"],
                "rule_name": rule["name"],
                "risk_level": rule["risk_level"],
                "recommendation": rule["recommendation"]
            })
            recommendations.append(rule["recommendation"])

            # Update max risk level
            risk_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
            if risk_levels[rule["risk_level"]] > risk_levels[max_risk_level]:
                max_risk_level = rule["risk_level"]

    # If no rules triggered, it's low risk
    if not triggered_rules:
        max_risk_level = "LOW"
        recommendations.append(
            "No specific risk factors identified. Routine follow-up recommended.")

    # Prepare result
    return {
        "record_id": str(record["_id"]),
        "patient_id": record.get("patient_id", "unknown"),
        "original_filename": record.get("original_filename", "unknown"),
        "upload_timestamp": record.get("upload_timestamp", ""),
        "screening_date": datetime.now().isoformat(),
        "risk_level": max_risk_level,
        "triggered_rules": triggered_rules,
        "recommendations": list(set(recommendations)),  # Remove duplicates
        "diseases_found": [d for d in diseases if d],
        "labs_found": list(labs.keys()),
        "disease_count": len(diseases),
        "lab_count": len(labs)
    }


@app.get("/screening/high_risk")
async def get_high_risk_records(limit: int = 20):
    """Get all high-risk records"""
    if records_collection is None:
        return {"error": "Storage not available"}

    try:
        # This would ideally query a screening results collection
        # For now, we'll run screening on recent records
        records = list(records_collection.find(
            {}).sort("upload_timestamp", -1).limit(50))

        high_risk_results = []
        for record in records:
            result = run_screening_on_record(record)
            if result["risk_level"] == "HIGH":
                high_risk_results.append(result)

        return {
            "count": len(high_risk_results),
            "results": high_risk_results[:limit]
        }

    except Exception as e:
        print(f"Error getting high risk records: {e}")
        return {"error": str(e)}


# ----------------------------
# Auth Endpoints
# ----------------------------
@app.post("/auth/register", response_model=User)
async def register_user(user: UserCreate):
    """Register a new user (legacy endpoint - use /auth/register from routes)"""
    if USE_MONGODB_AUTH:
        new_user = AuthService.register_user(user)
        if not new_user:
            raise HTTPException(
                status_code=400, detail="Username already registered or registration failed")
        return new_user
    else:
        if user.username in users_db:
            raise HTTPException(
                status_code=400, detail="Username already registered")

        # Validate role
        if user.role not in ["doctor", "patient", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")

        user_id = f"user_{len(users_db) + 1:03d}"
        hashed_password = get_password_hash(user.password)

        new_user = {
            "id": user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "full_name": user.full_name,
            "hashed_password": hashed_password,
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }

        users_db[user.username] = new_user

        # Return user without password
        return_user = new_user.copy()
        del return_user["hashed_password"]
        return User(**return_user)


@app.post("/auth/login", response_model=Token)
async def login_user(user: UserLogin):
    """Login user and return JWT token (legacy endpoint - use /auth/login from routes)"""
    if USE_MONGODB_AUTH:
        authenticated_user = AuthService.authenticate_user(
            user.username, user.password)
        if not authenticated_user:
            raise HTTPException(
                status_code=400, detail="Incorrect username or password")
        return AuthService.create_token_for_user(authenticated_user)
    else:
        db_user = users_db.get(user.username)
        if not db_user:
            raise HTTPException(
                status_code=400, detail="Incorrect username or password")

        if not verify_password(user.password, db_user["hashed_password"]):
            raise HTTPException(
                status_code=400, detail="Incorrect username or password")

        if not db_user["is_active"]:
            raise HTTPException(status_code=400, detail="Inactive user")

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user["username"], "role": db_user["role"]},
            expires_delta=access_token_expires
        )

        # Return token and user info
        user_info = {k: v for k, v in db_user.items() if k !=
                     "hashed_password"}
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=User(**user_info)
        )


@app.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@app.post("/auth/logout")
async def logout_user():
    """Logout user (client-side token removal)"""
    return {"message": "Successfully logged out"}

# ----------------------------
# Role-Based Permission Decorator
# ----------------------------


def require_role(required_role: str):
    """Decorator to require specific role"""
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail=f"Requires {required_role} role"
            )
        return current_user
    return role_checker

# ----------------------------
# Protected Endpoints Examples
# ----------------------------


@app.get("/doctor/dashboard")
async def doctor_dashboard(current_user: User = Depends(require_role("doctor"))):
    """Doctor-only dashboard data"""
    return {
        "message": f"Welcome to doctor dashboard, Dr. {current_user.full_name}",
        "stats": {
            "patients_today": 15,
            "pending_reviews": 8,
            "high_risk_cases": 3
        }
    }


@app.get("/patient/dashboard")
async def patient_dashboard(current_user: User = Depends(require_role("patient"))):
    """Patient-only dashboard data"""
    return {
        "message": f"Welcome {current_user.full_name}",
        "upcoming_appointments": [
            {"date": "2024-12-15", "doctor": "Dr. Smith", "type": "Follow-up"}
        ],
        "recent_records": 5
    }


@app.get("/")
async def root():
    return {"message": "Disease + Lab RAG API running!", "service_start_time_iso": IMPORT_TIME_ISO}
