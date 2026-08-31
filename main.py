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

import logging
import os
import re
import sys
import uuid
from contextlib import asynccontextmanager
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("diabcare")

# pyrefly: ignore [missing-import]
import joblib
# pyrefly: ignore [missing-import]
from datetime import datetime, timedelta, timezone
# pyrefly: ignore [missing-import]
import jwt
# pyrefly: ignore [missing-import]
import bcrypt
# pyrefly: ignore [missing-import]
import io
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
# pyrefly: ignore [missing-import]
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse, Response
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, EmailStr

# pyrefly: ignore [missing-import]
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from Src.Preprocessing import INT_COLS
from Src.database import (
    cache_prediction,
    get_all_patients,
    get_cached_prediction,
    get_patient,
    get_patient_record,
    init_db,
    save_new_patient,
    get_user_by_email,
    get_user_by_id,
    update_user_profile,
    save_new_user,
    get_pending_requests,
    get_all_doctors,
    get_all_admins,
    update_user_status,
    update_follow_up_status,
    get_dashboard_stats,
    assign_patient_to_doctor,
    save_refresh_token,
    get_refresh_token,
    delete_refresh_token,
    save_audit_log,
    get_patient_timeline,
)
from Src.explain import explain_patient

from Src.database import (
    cache_prediction,
    get_all_patients,
    get_cached_prediction,
    get_patient,
    get_patient_record,
    init_db,
    save_new_patient,
    get_user_by_email,
    get_user_by_id,
    update_user_profile,
    save_new_user,
    get_pending_requests,
    get_all_doctors,
    get_all_admins,
    update_user_status,
    update_follow_up_status,
    get_dashboard_stats,
    assign_patient_to_doctor,
)
from Src.explain import explain_patient

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = "DATA/diabcare.db"
MODEL_PATH = "DATA/lgbm_pipeline.joblib"

# ---------------------------------------------------------------------------
# App Lifespan & State Initialization
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DB_PATH)
    pipeline = joblib.load(MODEL_PATH)
    app.state.pipeline = pipeline
    logger.info(f"DB ready: {DB_PATH}")
    logger.info(f"Model loaded: {type(pipeline.named_steps['model']).__name__}")

    # Pre-compute risk predictions for all existing patients if not already cached
    try:
        patients_list = get_all_patients(DB_PATH)
        for p in patients_list:
            patient_id = p["patient_id"]
            if get_cached_prediction(DB_PATH, patient_id) is None:
                logger.info(f"Pre-calculating risk for patient {patient_id}...")
                patient_row = get_patient(DB_PATH, patient_id)
                if patient_row is not None:
                    result = explain_patient(patient_row, pipeline=pipeline)
                    result["patient_id"] = patient_id
                    cache_prediction(DB_PATH, patient_id, result)
        logger.info("Seeded patient predictions pre-calculated.")
    except Exception as e:
        logger.warning(f"Failed to pre-calculate predictions on startup: {str(e)}")

    yield

def get_pipeline(request: Request):
    return request.app.state.pipeline

# ---------------------------------------------------------------------------
# App init & Rate Limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="DiabCare AI",
    description="30-day hospital readmission risk predictor for diabetic patients.",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Security & JWT Configuration
# ---------------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET")
APP_ENV = os.getenv("APP_ENV", "development")
if not JWT_SECRET:
    if APP_ENV == "production":
        raise RuntimeError("JWT_SECRET environment variable is MANDATORY in production mode!")
    import secrets
    JWT_SECRET = secrets.token_hex(32)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: str) -> tuple[str, str, str]:
    """Returns (token_id, token, expires_at_iso)"""
    token_id = f"RT-{uuid.uuid4().hex[:12]}"
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "token_id": token_id,
        "user_id": user_id,
        "exp": expire,
        "type": "refresh"
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token_id, token, expire.isoformat()

def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token claims.")

        # Log action in audit_logs
        client_ip = request.client.host if request.client else "unknown"
        action = f"{request.method} {request.url.path}"
        save_audit_log(DB_PATH, user_id, action, request.url.path, client_ip)

        return {"user_id": user_id, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

def validate_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True

# CORS — dynamic configuration based on ALLOWED_ORIGINS env var
raw_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000")
allowed_origins = [origin.strip() for origin in raw_allowed_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
@app.get("/")
def read_root() -> FileResponse:
    return FileResponse("static/index.html")

@app.get("/api/config", summary="Get application configuration settings")
def get_config() -> dict:
    show_demo = os.getenv("SHOW_DEMO_ACCOUNTS", "true").lower() in ("true", "1", "yes")
    return {"show_demo_accounts": show_demo}

app.mount("/static", StaticFiles(directory="static"), name="static")



# ---------------------------------------------------------------------------
# Request / response models (per fixed API contract in README)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
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
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginUserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    education: str | None = None
    reference_id: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    user: LoginUserResponse


class UpdateProfileRequest(BaseModel):
    name: str
    education: str
    reference_id: str


class UserProfileResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    status: str
    education: str | None = None
    reference_id: str | None = None
    created_at: str


class CreateAdminRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class DoctorRecordItem(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    status: str
    education: str | None = None
    reference_id: str | None = None
    created_at: str


class AdminRecordItem(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    status: str
    education: str | None = None
    reference_id: str | None = None
    created_at: str


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
    shap_value: float = 0.0


class PredictResponse(BaseModel):
    patient_id: str
    risk_percent: float
    risk_category: str
    top_factors: list[FactorItem]
    follow_up_priority: str
    follow_up_status: str = "Pending"
    scheduled_date: str | None = None


class PatientListItem(BaseModel):
    patient_id: str
    summary: str
    name: str | None = None
    assigned_doctor_id: str | None = None
    assigned_doctor_name: str | None = None
    risk_percent: float | None = None
    follow_up_status: str | None = "Pending"
    scheduled_date: str | None = None


class AssignPatientRequest(BaseModel):
    doctor_id: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/login", response_model=LoginResponse, summary="User login")
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest) -> LoginResponse:
    email = body.email.strip().lower()
    password = body.password

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
    access_token = create_access_token(token_data)
    rt_id, refresh_token, expires_at = create_refresh_token(user["user_id"])
    save_refresh_token(DB_PATH, rt_id, user["user_id"], refresh_token, expires_at)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        user=LoginUserResponse(
            user_id=user["user_id"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            education=user.get("education"),
            reference_id=user.get("reference_id")
        )
    )


@app.post("/auth/register", summary="Register as a new doctor")
@limiter.limit("5/minute")
def register(request: Request, body: RegisterRequest) -> dict:
    name = body.name.strip()
    email = body.email.strip().lower()
    password = body.password

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="All fields (name, email, password) are required.")

    if not validate_password_strength(password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long and include at least one uppercase letter, one lowercase letter, and one number."
        )

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


@app.post("/auth/refresh", summary="Refresh access token")
def refresh_token_endpoint(body: RefreshTokenRequest) -> dict:
    token_str = body.refresh_token.strip()
    stored_token = get_refresh_token(DB_PATH, token_str)
    if not stored_token:
        raise HTTPException(status_code=401, detail="Invalid or reused refresh token.")

    try:
        payload = jwt.decode(token_str, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type.")
        user_id = payload.get("user_id")
    except jwt.PyJWTError:
        delete_refresh_token(DB_PATH, token_str)
        raise HTTPException(status_code=401, detail="Expired or invalid refresh token.")

    user = get_user_by_id(DB_PATH, user_id)
    if not user or user["status"] != "approved":
        delete_refresh_token(DB_PATH, token_str)
        raise HTTPException(status_code=401, detail="User account inactive or not found.")

    # Rotate refresh token: delete old, create new
    delete_refresh_token(DB_PATH, token_str)

    new_access_token = create_access_token({"user_id": user["user_id"], "role": user["role"]})
    rt_id, new_refresh_token, expires_at = create_refresh_token(user["user_id"])
    save_refresh_token(DB_PATH, rt_id, user["user_id"], new_refresh_token, expires_at)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh_token
    }


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


@app.get("/user/profile", response_model=UserProfileResponse, summary="Get current user profile")
def get_profile(current_user: dict = Depends(get_current_user)) -> UserProfileResponse:
    user = get_user_by_id(DB_PATH, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found.")
    return UserProfileResponse(
        user_id=user["user_id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        status=user["status"],
        education=user.get("education"),
        reference_id=user.get("reference_id"),
        created_at=user["created_at"]
    )


@app.put("/user/profile", response_model=UserProfileResponse, summary="Update current user profile")
def update_profile(request: UpdateProfileRequest, current_user: dict = Depends(get_current_user)) -> UserProfileResponse:
    user = get_user_by_id(DB_PATH, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    name = request.name.strip()
    education = request.education.strip()
    reference_id = request.reference_id.strip()

    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    try:
        update_user_profile(DB_PATH, current_user["user_id"], name, education, reference_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error updating profile: {str(e)}")

    updated_user = get_user_by_id(DB_PATH, current_user["user_id"])
    return UserProfileResponse(
        user_id=updated_user["user_id"],
        name=updated_user["name"],
        email=updated_user["email"],
        role=updated_user["role"],
        status=updated_user["status"],
        education=updated_user.get("education"),
        reference_id=updated_user.get("reference_id"),
        created_at=updated_user["created_at"]
    )


@app.get("/admin/doctors", response_model=list[DoctorRecordItem], summary="Get all registered doctor records (Admin only)")
def list_all_doctors(current_user: dict = Depends(get_current_user)) -> list[DoctorRecordItem]:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden. Only administrators can view doctor records.")
    doctors = get_all_doctors(DB_PATH)
    return [DoctorRecordItem(**d) for d in doctors]


@app.get("/admin/admins", response_model=list[AdminRecordItem], summary="Get all system administrators (Admin only)")
def list_all_admins(current_user: dict = Depends(get_current_user)) -> list[AdminRecordItem]:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden. Only administrators can view admin records.")
    admins = get_all_admins(DB_PATH)
    return [AdminRecordItem(**a) for a in admins]


@app.post("/admin/create-admin", summary="Directly create a new administrator account (Admin only)")
def create_admin(request: CreateAdminRequest, current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden. Only administrators can create admin accounts.")

    name = request.name.strip()
    email = request.email.strip().lower()
    password = request.password

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")
    if not name:
        name = "Admin User"

    existing_user = get_user_by_email(DB_PATH, email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    user_id = f"ADM-{uuid.uuid4().hex[:6].upper()}"
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwd_hash = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    try:
        save_new_user(DB_PATH, user_id, name, email, pwd_hash, "admin", "approved", "System Administrator", f"REF-ADM-{user_id[-4:]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error creating admin: {str(e)}")

    return {"message": f"Administrator account created successfully for {email}.", "user_id": user_id}


@app.post("/predict", response_model=PredictResponse, summary="Predict 30-day readmission risk")
def predict(request: PredictRequest, current_user: dict = Depends(get_current_user), pipeline = Depends(get_pipeline)) -> PredictResponse:
    """
    Given a patient_id, return:
    - risk_percent      : 0-100 float
    - risk_category     : Low / Moderate / High
    - top_factors       : top 3 SHAP-based plain-language factors
    - follow_up_priority: Low / Medium / High

    Results are cached in SQLite — repeated calls for the same patient_id
    skip SHAP re-computation.
    """
    if current_user["role"] == "patient":
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Patients cannot run predictions."
        )
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
    result = explain_patient(patient_row, pipeline=pipeline)
    result["patient_id"] = patient_id

    # 4. Cache result
    cache_prediction(DB_PATH, patient_id, result)

    return PredictResponse(**result)


@app.post("/predict_new", response_model=PredictResponse, summary="Predict 30-day readmission risk for a new patient")
def predict_new(request: PredictNewRequest, current_user: dict = Depends(get_current_user), pipeline = Depends(get_pipeline)) -> PredictResponse:
    """
    Given raw patient feature values as JSON, return prediction results:
    - risk_percent      : 0-100 float
    - risk_category     : Low / Moderate / High
    - top_factors       : top 3 SHAP-based plain-language factors
    - follow_up_priority: Low / Medium / High

    Results are cached in predictions table under a generated placeholder patient ID.
    """
    if current_user["role"] == "patient":
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Patients cannot run predictions."
        )
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
    for col in INT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Generate placeholder ID
    placeholder_id = f"NEW-{uuid.uuid4().hex[:6].upper()}"

    # 5. Run explain_patient
    try:
        result = explain_patient(df, pipeline=pipeline)
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
        logger.warning(f"Failed to save new patient raw features: {str(e)}")

    # 7. Cache prediction
    try:
        cache_prediction(DB_PATH, placeholder_id, result)
    except Exception as e:
        logger.warning(f"Failed to cache new patient prediction: {str(e)}")

    return PredictResponse(**result)


@app.get("/patients", response_model=list[PatientListItem], summary="List available patients")
def patients(current_user: dict = Depends(get_current_user)) -> list[PatientListItem]:
    """
    Return all patient IDs and their one-line summaries.
    Used by the frontend to populate the search / dropdown.
    """
    if current_user["role"] == "patient":
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Patients cannot view the patient directory."
        )
    rows = get_all_patients(DB_PATH)
    return [PatientListItem(**r) for r in rows]


@app.get("/patients/{patient_id}/timeline", summary="Get patient readmission evaluation history timeline")
def patient_timeline(patient_id: str, current_user: dict = Depends(get_current_user)) -> list[dict]:
    patient_id_str = patient_id.strip()
    if current_user["role"] == "patient":
        logged_in_user = get_user_by_id(DB_PATH, current_user["user_id"])
        if not logged_in_user or logged_in_user.get("reference_id") != patient_id_str:
            raise HTTPException(
                status_code=403,
                detail="Forbidden. Patients can only view their own history timeline."
            )
    patient_rec = get_patient_record(DB_PATH, patient_id_str)
    if not patient_rec:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id_str}' not found.")
    return get_patient_timeline(DB_PATH, patient_id_str)


class UpdateFollowUpRequest(BaseModel):
    status: str
    scheduled_date: str | None = None


@app.patch("/predict/{patient_id}/follow-up", summary="Update follow-up status")
def patch_follow_up(
    patient_id: str,
    request: UpdateFollowUpRequest,
    current_user: dict = Depends(get_current_user),
    pipeline = Depends(get_pipeline)
) -> dict:
    status = request.status.strip()
    if status not in ["Pending", "Scheduled", "Completed"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Status must be one of 'Pending', 'Scheduled', or 'Completed'."
        )
    
    # Authorization check: Doctor can only update status for patients assigned to them
    user_role = current_user.get("role")
    user_id = current_user.get("user_id")

    patient_rec = get_patient_record(DB_PATH, patient_id)
    if patient_rec is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patient '{patient_id}' not found in the database."
        )

    if user_role == "doctor":
        assigned_doc = patient_rec.get("assigned_doctor_id")
        if assigned_doc != user_id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden. Doctors can only update follow-up status for their assigned patients."
            )

    scheduled_date = request.scheduled_date.strip() if request.scheduled_date and request.scheduled_date.strip() else None
    
    # Verify cached prediction exists or initialize it
    cached = get_cached_prediction(DB_PATH, patient_id)
    if cached is None:
        patient_row = get_patient(DB_PATH, patient_id)
        if patient_row is not None:
            result = explain_patient(patient_row, pipeline=pipeline)
            result["patient_id"] = patient_id
            cache_prediction(DB_PATH, patient_id, result)
    
    try:
        update_follow_up_status(DB_PATH, patient_id, status, scheduled_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    # Get updated record to return current status and scheduled_date
    updated_pred = get_cached_prediction(DB_PATH, patient_id)

    return {
        "message": "Follow-up status updated successfully.",
        "patient_id": patient_id,
        "follow_up_status": updated_pred.get("follow_up_status") if updated_pred else status,
        "scheduled_date": updated_pred.get("scheduled_date") if updated_pred else scheduled_date
    }


@app.patch("/patients/{patient_id}/assign", summary="Assign or unassign patient to a doctor (Admin only)")
def patch_assign_patient(
    patient_id: str,
    request: AssignPatientRequest,
    current_user: dict = Depends(get_current_user)
) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Only administrators can assign patients to doctors."
        )
    
    doctor_id = request.doctor_id.strip() if request.doctor_id and request.doctor_id.strip() else None
    
    # If doctor_id is specified, verify doctor exists and is approved
    if doctor_id:
        doc_user = get_user_by_id(DB_PATH, doctor_id)
        if not doc_user or doc_user["role"] != "doctor" or doc_user["status"] != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid doctor ID '{doctor_id}'. Must be an approved doctor."
            )
            
    try:
        assign_patient_to_doctor(DB_PATH, patient_id, doctor_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error updating patient assignment: {str(e)}")

    return {
        "message": f"Patient '{patient_id}' assigned successfully.",
        "patient_id": patient_id,
        "assigned_doctor_id": doctor_id
    }


@app.get("/dashboard/stats", summary="Get dashboard statistics")
def dashboard_stats(current_user: dict = Depends(get_current_user)) -> dict:
    try:
        stats = get_dashboard_stats(DB_PATH)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error fetching stats: {str(e)}")


@app.get("/api/patient/dashboard", summary="Get patient dashboard details (Patient only)")
def patient_dashboard(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "patient":
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Only patients can access the patient dashboard."
        )
    
    user_id = current_user["user_id"]
    user = get_user_by_id(DB_PATH, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    patient_id = user.get("reference_id")
    if not patient_id:
        raise HTTPException(status_code=400, detail="User is not linked to any patient record.")
        
    patient_rec = get_patient_record(DB_PATH, patient_id)
    if not patient_rec:
        raise HTTPException(status_code=404, detail=f"Patient record '{patient_id}' not found.")
        
    # Get doctor details
    doc_id = patient_rec.get("assigned_doctor_id")
    doc_info = None
    if doc_id:
        doc_user = get_user_by_id(DB_PATH, doc_id)
        if doc_user:
            doc_info = {
                "name": doc_user["name"],
                "email": doc_user["email"],
                "education": doc_user.get("education"),
                "reference_id": doc_user.get("reference_id")
            }
            
    # Get latest cached prediction
    latest_pred = get_cached_prediction(DB_PATH, patient_id)
    
    # Get appointment details from prediction
    appt_info = None
    if latest_pred:
        appt_info = {
            "status": latest_pred.get("follow_up_status", "Pending"),
            "scheduled_date": latest_pred.get("scheduled_date")
        }
    else:
        appt_info = {
            "status": "Pending",
            "scheduled_date": None
        }
        
    return {
        "patient_id": patient_id,
        "name": user["name"],
        "assigned_doctor": doc_info,
        "appointment": appt_info,
        "latest_prediction": latest_pred
    }


@app.post("/predict/bulk", summary="Bulk CSV Upload Risk Screening")
async def predict_bulk(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    pipeline = Depends(get_pipeline)
) -> list[dict]:
    if current_user["role"] == "patient":
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Patients cannot run bulk predictions."
        )
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV file.")

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file format: {str(e)}")

    results = []
    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        row_df = pd.DataFrame([row_dict])

        for col in INT_COLS:
            if col in row_df.columns:
                row_df[col] = pd.to_numeric(row_df[col], errors="coerce")

        p_id = str(row_dict.get("patient_id", f"BULK-{idx+1}"))
        try:
            res = explain_patient(row_df, pipeline=pipeline)
            res["patient_id"] = p_id
            results.append(res)
        except Exception as e:
            results.append({
                "patient_id": p_id,
                "error": str(e)
            })

    return results


@app.get("/patients/{patient_id}/report/pdf", summary="Export patient clinical risk report as PDF")
def export_pdf_report(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    pipeline = Depends(get_pipeline)
) -> Response:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    patient_id_str = patient_id.strip()
    if current_user["role"] == "patient":
        logged_in_user = get_user_by_id(DB_PATH, current_user["user_id"])
        if not logged_in_user or logged_in_user.get("reference_id") != patient_id_str:
            raise HTTPException(
                status_code=403,
                detail="Forbidden. Patients can only export their own PDF report."
            )
    patient_row = get_patient(DB_PATH, patient_id_str)
    if patient_row is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id_str}' not found.")

    cached = get_cached_prediction(DB_PATH, patient_id_str)
    if not cached:
        cached = explain_patient(patient_row, pipeline=pipeline)
        cached["patient_id"] = patient_id_str

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#dc2626'),
        spaceAfter=12
    )

    story.append(Paragraph(f"DiabCare AI — Clinical Readmission Risk Report", title_style))
    story.append(Paragraph(f"<b>Patient ID:</b> {patient_id_str}", styles['Normal']))
    story.append(Paragraph(f"<b>Generated At:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Risk Summary
    risk_color = '#059669' if cached['risk_category'] == 'Low' else ('#d97706' if cached['risk_category'] == 'Moderate' else '#dc2626')
    story.append(Paragraph(f"<b>30-Day Readmission Risk:</b> {cached['risk_percent']}%", styles['Heading2']))
    story.append(Paragraph(f"<b>Risk Category:</b> <font color='{risk_color}'><b>{cached['risk_category']}</b></font>", styles['Normal']))
    story.append(Paragraph(f"<b>Follow-Up Priority:</b> {cached['follow_up_priority']}", styles['Normal']))
    story.append(Paragraph(f"<b>Follow-Up Status:</b> {cached.get('follow_up_status', 'Pending')}", styles['Normal']))
    story.append(Spacer(1, 14))

    # SHAP Factors Table
    story.append(Paragraph("<b>Top SHAP Contributing Risk Factors:</b>", styles['Heading3']))
    table_data = [["Factor Description", "Direction", "SHAP Value"]]
    for f in cached.get('top_factors', []):
        table_data.append([
            f.get('factor', ''),
            f.get('direction', ''),
            f"{f.get('shap_value', 0.0):.4f}"
        ])

    t = Table(table_data, colWidths=[300, 120, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<i>Disclaimer: DiabCare AI is a prototype clinical decision-support system. It is not a medical diagnosis or clinically validated risk assessment.</i>", styles['Italic']))

    doc.build(story)
    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=DiabCare_Report_{patient_id_str}.pdf"}
    )


@app.get("/health", summary="Health check")
def health() -> dict:
    """Returns 200 OK with model and risk distribution statistics."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            high = cursor.execute("SELECT COUNT(*) FROM predictions WHERE risk_category = 'High'").fetchone()[0]
            mod = cursor.execute("SELECT COUNT(*) FROM predictions WHERE risk_category = 'Moderate'").fetchone()[0]
            low = cursor.execute("SELECT COUNT(*) FROM predictions WHERE risk_category = 'Low'").fetchone()[0]
            total = high + mod + low
    except Exception:
        high, mod, low, total = 0, 0, 0, 0

    return {
        "status": "ok",
        "model": "LGBMClassifier",
        "risk_distribution": {
            "total_predictions": total,
            "high_risk": high,
            "moderate_risk": mod,
            "low_risk": low
        }
    }
