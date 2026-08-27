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
from fastapi import FastAPI, HTTPException
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


# ---------------------------------------------------------------------------
# Request / response models (per fixed API contract in README)
# ---------------------------------------------------------------------------

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


class PatientListItem(BaseModel):
    patient_id: str
    summary: str
    name: str | None = None
    risk_percent: float | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/predict", response_model=PredictResponse, summary="Predict 30-day readmission risk")
def predict(request: PredictRequest) -> PredictResponse:
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
def predict_new(request: PredictNewRequest) -> PredictResponse:
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
def patients() -> list[PatientListItem]:
    """
    Return all patient IDs and their one-line summaries.
    Used by the frontend to populate the search / dropdown.
    """
    rows = get_all_patients(DB_PATH)
    return [PatientListItem(**r) for r in rows]


@app.get("/health", summary="Health check")
def health() -> dict:
    """Returns 200 OK with basic status — useful for Render deployment checks."""
    return {"status": "ok", "model": type(_pipeline.named_steps["model"]).__name__}
