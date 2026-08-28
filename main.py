"""
DiabCare AI — FastAPI Backend
================================
Phase 4: serves the fixed API contract below.

Endpoints:
  POST /predict   { "patient_id": "..." }
  GET  /patients
  GET  /health

Run from project root:
  uvicorn main:app --reload
  # then visit http://localhost:8000/docs
"""

import os
import sys
import uuid
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# pyrefly: ignore [missing-import]
import joblib
# pyrefly: ignore [missing-import]
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

from Src.database import (
    cache_prediction,
    get_all_patients,
    get_cached_prediction,
    get_patient,
    init_db,
    save_new_patient,
    get_user_by_email,
    save_new_user,
    get_pending_requests,
    update_user_status,
    update_follow_up_status,
    get_dashboard_stats,
)
from Src.explain import explain_patient

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = "DATA/diabcare.db"
MODEL_PATH = "DATA/lgbm_pipeline.joblib"

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DiabCare AI",
    description="30-day hospital readmission risk predictor for diabetic patients.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Security & JWT Configuration
# ---------------------------------------------------------------------------
JWT_SECRET = "diabcare_secret_key_123456"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token claims.")
        return {"user_id": user_id, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

# CORS — allow all origins during development (frontend is a separate static app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
@app.get("/")
def read_root() -> FileResponse:
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------------------------------------------------------------------
# Startup: init DB + load model once into memory
# ---------------------------------------------------------------------------
_pipeline = None


@app.on_event("startup")
def startup_event() -> None:
    global _pipeline
    init_db(DB_PATH)
    _pipeline = joblib.load(MODEL_PATH)
    print(f"[startup] DB ready: {DB_PATH}")
    print(f"[startup] Model loaded: {type(_pipeline.named_steps['model']).__name__}")
    
    # Pre-compute risk predictions for all existing patients if not already cached
    try:
        patients_list = get_all_patients(DB_PATH)
        for p in patients_list:
            patient_id = p["patient_id"]
            if get_cached_prediction(DB_PATH, patient_id) is None:
                print(f"Pre-calculating risk for patient {patient_id}...")
                patient_row = get_patient(DB_PATH, patient_id)
                if patient_row is not None:
                    result = explain_patient(patient_row, pipeline=_pipeline)
                    result["patient_id"] = patient_id
                    cache_prediction(DB_PATH, patient_id, result)
        print("[startup] Seeded patient predictions pre-calculated.")
    except Exception as e:
        print(f"[Warning] Failed to pre-calculate predictions on startup: {str(e)}")


# ---------------------------------------------------------------------------
# Request / response models (per fixed API contract in README)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class RequestActionRequest(BaseModel):
    user_id: str
    action: str


class PendingRequestListItem(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    created_at: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginUserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: LoginUserResponse


class PredictRequest(BaseModel):
    patient_id: str


class PredictNewRequest(BaseModel):
    name: str
    race: str
    gender: str
    age: str
    admission_type_id: int
    discharge_disposition_id: int
    admission_source_id: int
    time_in_hospital: int
    num_lab_procedures: int
    num_procedures: int
    num_medications: int
    number_outpatient: int
    number_emergency: int
    number_inpatient: int
    diag_1: str
    diag_2: str
    diag_3: str
    number_diagnoses: int
    max_glu_serum: str = "None"
    A1Cresult: str = "None"
    metformin: str = "No"
    repaglinide: str = "No"
    nateglinide: str = "No"
    chlorpropamide: str = "No"
    glimepiride: str = "No"
    acetohexamide: str = "No"
    glipizide: str = "No"
    glyburide: str = "No"
    tolbutamide: str = "No"
    pioglitazone: str = "No"
    rosiglitazone: str = "No"
    acarbose: str = "No"
    miglitol: str = "No"
    troglitazone: str = "No"
    tolazamide: str = "No"
    examide: str = "No"
    citoglipton: str = "No"
    insulin: str = "No"
    glyburide_metformin: str = Field(default="No", alias="glyburide-metformin")
    glipizide_metformin: str = Field(default="No", alias="glipizide-metformin")
    glimepiride_pioglitazone: str = Field(default="No", alias="glimepiride-pioglitazone")
    metformin_rosiglitazone: str = Field(default="No", alias="metformin-rosiglitazone")
    metformin_pioglitazone: str = Field(default="No", alias="metformin-pioglitazone")
    change: str = "No"
    diabetesMed: str = "No"

    model_config = {
        "populate_by_name": True
    }


class FactorItem(BaseModel):
    factor: str
    direction: str


class PredictResponse(BaseModel):
    patient_id: str
    risk_percent: float
    risk_category: str
    top_factors: list[FactorItem]
    follow_up_priority: str
    follow_up_status: str = "Pending"


class PatientListItem(BaseModel):
    patient_id: str
    summary: str
    name: str | None = None
    risk_percent: float | None = None
    follow_up_status: str | None = "Pending"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/login", response_model=LoginResponse, summary="User login")
def login(request: LoginRequest) -> LoginResponse:
    email = request.email.strip().lower()
    password = request.password

    user = get_user_by_email(DB_PATH, email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Verify password hash using bcrypt
    hashed_bytes = user["password_hash"].encode('utf-8')
    if not bcrypt.checkpw(password.encode('utf-8'), hashed_bytes):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Check account approval status
    if user["status"] == "pending":
        raise HTTPException(
            status_code=401,
            detail="Account pending approval by administrator."
        )
    elif user["status"] == "rejected":
        raise HTTPException(
            status_code=401,
            detail="Access request has been rejected."
        )

    token_data = {"user_id": user["user_id"], "role": user["role"]}
    token = create_access_token(token_data)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=LoginUserResponse(
            user_id=user["user_id"],
            name=user["name"],
            email=user["email"],
            role=user["role"]
        )
    )


@app.post("/auth/register", summary="Register as a new doctor")
def register(request: RegisterRequest) -> dict:
    name = request.name.strip()
    email = request.email.strip().lower()
    password = request.password

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="All fields (name, email, password) are required.")

    # Check email uniqueness
    existing_user = get_user_by_email(DB_PATH, email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    # Create random user ID
    user_id = f"U-{uuid.uuid4().hex[:6].upper()}"

    # Hash password using bcrypt
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwd_hash = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    # Save to database with status 'pending' and role 'doctor'
    try:
        save_new_user(DB_PATH, user_id, name, email, pwd_hash, "doctor", "pending")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error during registration: {str(e)}")

    return {"message": "Access request submitted. Pending administrator approval."}


@app.get("/admin/requests", response_model=list[PendingRequestListItem], summary="List pending doctor access requests")
def list_pending_requests(current_user: dict = Depends(get_current_user)) -> list[PendingRequestListItem]:
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Only administrators can view pending registration requests."
        )
    rows = get_pending_requests(DB_PATH)
    return [PendingRequestListItem(**r) for r in rows]


@app.post("/admin/requests/action", summary="Approve or reject doctor access request")
def action_pending_request(request: RequestActionRequest, current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Only administrators can process registration requests."
        )

    user_id = request.user_id.strip()
    action = request.action.strip().lower()

    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

    status = "approved" if action == "approve" else "rejected"
    try:
        update_user_status(DB_PATH, user_id, status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error updating status: {str(e)}")

    return {"message": f"User {user_id} has been {status}."}


@app.post("/predict", response_model=PredictResponse, summary="Predict 30-day readmission risk")
def predict(request: PredictRequest, current_user: dict = Depends(get_current_user)) -> PredictResponse:
    """
    Given a patient_id, return:
    - risk_percent      : 0-100 float
    - risk_category     : Low / Moderate / High
    - top_factors       : top 3 SHAP-based plain-language factors
    - follow_up_priority: Low / Medium / High

    Results are cached in SQLite — repeated calls for the same patient_id
    skip SHAP re-computation.
    """
    patient_id = request.patient_id.strip()
    if not patient_id:
        raise HTTPException(
            status_code=400,
            detail="Patient ID cannot be empty."
        )

    # 1. Check prediction cache
    cached = get_cached_prediction(DB_PATH, patient_id)
    if cached is not None:
        return PredictResponse(**cached)

    # 2. Load patient row from DB
    patient_row = get_patient(DB_PATH, patient_id)
    if patient_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patient '{patient_id}' not found in the database.",
        )

    # 3. Run explain_patient (SHAP + LightGBM)
    result = explain_patient(patient_row, pipeline=_pipeline)
    result["patient_id"] = patient_id

    # 4. Cache result
    cache_prediction(DB_PATH, patient_id, result)

    return PredictResponse(**result)


@app.post("/predict_new", response_model=PredictResponse, summary="Predict 30-day readmission risk for a new patient")
def predict_new(request: PredictNewRequest, current_user: dict = Depends(get_current_user)) -> PredictResponse:
    """
    Given raw patient feature values as JSON, return prediction results:
    - risk_percent      : 0-100 float
    - risk_category     : Low / Moderate / High
    - top_factors       : top 3 SHAP-based plain-language factors
    - follow_up_priority: Low / Medium / High

    Results are cached in predictions table under a generated placeholder patient ID.
    """
    # 1. Server-side validation
    errors = []

    # Check numeric bounds
    numeric_bounds = {
        "time_in_hospital": (1, 14, "Length of hospital stay must be between 1 and 14 days."),
        "num_lab_procedures": (1, 150, "Number of lab procedures must be between 1 and 150."),
        "num_procedures": (0, 10, "Number of procedures must be between 0 and 10."),
        "num_medications": (1, 100, "Number of medications must be between 1 and 100."),
        "number_diagnoses": (1, 16, "Number of diagnoses must be between 1 and 16."),
        "number_outpatient": (0, 100, "Prior outpatient visits must be >= 0."),
        "number_emergency": (0, 100, "Prior emergency visits must be >= 0."),
        "number_inpatient": (0, 100, "Number of prior inpatient visits must be >= 0."),
    }

    for field, (min_val, max_val, msg) in numeric_bounds.items():
        val = getattr(request, field, None)
        if val is None:
            errors.append(f"Missing required numeric field: '{field}'")
        elif not (min_val <= val <= max_val):
            errors.append(msg)

    # Check diagnosis codes are not empty
    for field in ["diag_1", "diag_2", "diag_3"]:
        val = getattr(request, field, "")
        if not val or not str(val).strip():
            errors.append(f"Diagnosis code '{field}' is required.")

    if errors:
        raise HTTPException(status_code=400, detail=errors)

    # 2. Build patient dictionary with aliases for hyphenated keys
    patient_dict = request.model_dump(by_alias=True)

    # 3. Create single-row DataFrame for evaluation (excluding non-model metadata)
    eval_dict = {k: v for k, v in patient_dict.items() if k not in ["name"]}
    df = pd.DataFrame([eval_dict])

    # Ensure numeric columns are correct dtype
    _INT_COLS = [
        "admission_type_id", "discharge_disposition_id", "admission_source_id",
        "time_in_hospital", "num_lab_procedures", "num_procedures",
        "num_medications", "number_outpatient", "number_emergency",
        "number_inpatient", "number_diagnoses",
    ]
    for col in _INT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Generate placeholder ID
    placeholder_id = f"NEW-{uuid.uuid4().hex[:6].upper()}"

    # 5. Run explain_patient
    try:
        result = explain_patient(df, pipeline=_pipeline)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error evaluating model prediction: {str(e)}"
        )

    result["patient_id"] = placeholder_id

    # 6. Save raw features to patient database registry
    try:
        save_new_patient(DB_PATH, placeholder_id, patient_dict)
    except Exception as e:
        print(f"[Warning] Failed to save new patient raw features: {str(e)}")

    # 7. Cache prediction
    try:
        cache_prediction(DB_PATH, placeholder_id, result)
    except Exception as e:
        print(f"[Warning] Failed to cache new patient prediction: {str(e)}")

    return PredictResponse(**result)


@app.get("/patients", response_model=list[PatientListItem], summary="List available patients")
def patients(current_user: dict = Depends(get_current_user)) -> list[PatientListItem]:
    """
    Return all patient IDs and their one-line summaries.
    Used by the frontend to populate the search / dropdown.
    """
    rows = get_all_patients(DB_PATH)
    return [PatientListItem(**r) for r in rows]


class UpdateFollowUpRequest(BaseModel):
    status: str


@app.patch("/predict/{patient_id}/follow-up", summary="Update follow-up status")
def patch_follow_up(
    patient_id: str,
    request: UpdateFollowUpRequest,
    current_user: dict = Depends(get_current_user)
) -> dict:
    status = request.status.strip()
    if status not in ["Pending", "Scheduled", "Completed"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Status must be one of 'Pending', 'Scheduled', or 'Completed'."
        )
    
    # Verify patient exists
    cached = get_cached_prediction(DB_PATH, patient_id)
    if cached is None:
        patient_row = get_patient(DB_PATH, patient_id)
        if patient_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Patient '{patient_id}' not found in the database."
            )
        result = explain_patient(patient_row, pipeline=_pipeline)
        result["patient_id"] = patient_id
        cache_prediction(DB_PATH, patient_id, result)
    
    try:
        update_follow_up_status(DB_PATH, patient_id, status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    return {"message": "Follow-up status updated successfully.", "patient_id": patient_id, "follow_up_status": status}


@app.get("/dashboard/stats", summary="Get dashboard statistics")
def dashboard_stats(current_user: dict = Depends(get_current_user)) -> dict:
    try:
        stats = get_dashboard_stats(DB_PATH)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error fetching stats: {str(e)}")


@app.get("/health", summary="Health check")
def health() -> dict:
    """Returns 200 OK with basic status — useful for Render deployment checks."""
    return {"status": "ok", "model": type(_pipeline.named_steps["model"]).__name__}
