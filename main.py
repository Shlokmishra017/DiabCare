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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# pyrefly: ignore [missing-import]
import joblib
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from pydantic import BaseModel

from Src.database import (
    cache_prediction,
    get_all_patients,
    get_cached_prediction,
    get_patient,
    init_db,
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
    patient_id = request.patient_id

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
