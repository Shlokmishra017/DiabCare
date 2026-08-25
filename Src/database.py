"""
DiabCare AI — SQLite Database Helpers
========================================
Plain sqlite3 module only — no SQLAlchemy or ORM (per README spec).

Tables:
  patients    — raw feature columns + patient_id (encounter_id) + summary
  predictions — prediction cache to avoid re-running SHAP on repeated lookups
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

# All 44 feature columns (matches Preprocessing.py column lists)
_FEATURE_COLS = [
    "race", "gender", "age",
    "admission_type_id", "discharge_disposition_id", "admission_source_id",
    "time_in_hospital", "num_lab_procedures", "num_procedures",
    "num_medications", "number_outpatient", "number_emergency",
    "number_inpatient", "diag_1", "diag_2", "diag_3",
    "number_diagnoses", "max_glu_serum", "A1Cresult",
    "metformin", "repaglinide", "nateglinide", "chlorpropamide",
    "glimepiride", "acetohexamide", "glipizide", "glyburide",
    "tolbutamide", "pioglitazone", "rosiglitazone", "acarbose",
    "miglitol", "troglitazone", "tolazamide", "examide",
    "citoglipton", "insulin", "glyburide-metformin",
    "glipizide-metformin", "glimepiride-pioglitazone",
    "metformin-rosiglitazone", "metformin-pioglitazone",
    "change", "diabetesMed",
]

_FEATURE_COL_DEFS = ", ".join(
    f'"{col}" TEXT' for col in _FEATURE_COLS
)

CREATE_PATIENTS_SQL = f"""
CREATE TABLE IF NOT EXISTS patients (
    patient_id  TEXT PRIMARY KEY,
    summary     TEXT,
    {_FEATURE_COL_DEFS}
);
"""

CREATE_PREDICTIONS_SQL = """
CREATE TABLE IF NOT EXISTS predictions (
    patient_id          TEXT PRIMARY KEY,
    risk_percent        REAL,
    risk_category       TEXT,
    factors             TEXT,
    follow_up_priority  TEXT,
    created_at          TEXT
);
"""


def init_db(db_path: str) -> None:
    """Create tables if they don't exist."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_PATIENTS_SQL)
        conn.execute(CREATE_PREDICTIONS_SQL)
        conn.commit()


def _build_summary(row: pd.Series) -> str:
    """Build a human-readable one-line patient summary for the /patients endpoint."""
    gender = str(row.get("gender", "Unknown"))
    age = str(row.get("age", "Unknown")).replace("[", "").replace(")", "")
    race = str(row.get("race", "Unknown"))
    time_in = row.get("time_in_hospital", "?")
    n_inpatient = row.get("number_inpatient", 0)
    return (
        f"{gender}, {age} yrs, {race} | "
        f"Stay: {time_in}d | Prior inpatient: {n_inpatient}"
    )


def seed_patients(
    db_path: str,
    cleaned_csv: str = "DATA/CleanedDiabetic_data.csv",
    original_csv: str = "DATA/diabetic_data.csv",
    n_patients: int = 6,
) -> list[str]:
    """
    Select n_patients representative patients (spread across risk tiers by proxy
    of number_inpatient visits), retrieve their encounter_id from the original
    CSV, and insert into the patients table.

    Returns list of inserted patient_ids.
    """
    # Load both CSVs — row indices match (same rows, different columns)
    print("Loading cleaned dataset ...")
    cleaned = pd.read_csv(cleaned_csv)

    print("Loading original dataset for encounter_ids ...")
    original = pd.read_csv(original_csv, usecols=["encounter_id"])

    # Align encounter_ids with cleaned rows
    cleaned["patient_id"] = original["encounter_id"].astype(str)

    # Select 6 patients: 2 low / 2 medium / 2 high risk proxy
    # Proxy: number_inpatient == 0 → low risk; 1-2 → medium; >= 3 → high
    low    = cleaned[cleaned["number_inpatient"] == 0].head(2)
    medium = cleaned[(cleaned["number_inpatient"] >= 1) & (cleaned["number_inpatient"] <= 2)].head(2)
    high   = cleaned[cleaned["number_inpatient"] >= 3].head(2)

    selected = pd.concat([low, medium, high]).reset_index(drop=True)

    if len(selected) < n_patients:
        # Fallback: just take first n_patients rows
        selected = cleaned.head(n_patients)

    inserted_ids = []

    with sqlite3.connect(db_path) as conn:
        for _, row in selected.iterrows():
            patient_id = str(row["patient_id"])
            summary = _build_summary(row)

            # Build values dict for feature columns
            feature_vals = {col: str(row[col]) if pd.notna(row.get(col)) else None
                            for col in _FEATURE_COLS}

            cols = ["patient_id", "summary"] + _FEATURE_COLS
            placeholders = ", ".join("?" for _ in cols)
            col_names = ", ".join(f'"{c}"' for c in cols)
            values = [patient_id, summary] + [feature_vals[c] for c in _FEATURE_COLS]

            conn.execute(
                f"INSERT OR REPLACE INTO patients ({col_names}) VALUES ({placeholders})",
                values,
            )
            inserted_ids.append(patient_id)
            print(f"  Seeded patient {patient_id}: {summary}")

        conn.commit()

    return inserted_ids


def get_patient(db_path: str, patient_id: str) -> Optional[pd.DataFrame]:
    """
    Load a patient's feature row from the DB as a single-row DataFrame.
    Returns None if patient_id not found.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM patients WHERE patient_id = ?", (patient_id,)
        )
        row = cur.fetchone()

    if row is None:
        return None

    # Reconstruct as DataFrame with only the 44 feature columns
    record = {col: row[col] for col in _FEATURE_COLS}
    df = pd.DataFrame([record])

    # Restore numeric columns to their correct dtypes
    _INT_COLS = [
        "admission_type_id", "discharge_disposition_id", "admission_source_id",
        "time_in_hospital", "num_lab_procedures", "num_procedures",
        "num_medications", "number_outpatient", "number_emergency",
        "number_inpatient", "number_diagnoses",
    ]
    for col in _INT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_all_patients(db_path: str) -> list[dict]:
    """Return all patients as list of {patient_id, summary} for /patients endpoint."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT patient_id, summary FROM patients ORDER BY patient_id"
        ).fetchall()
    return [{"patient_id": r["patient_id"], "summary": r["summary"]} for r in rows]


def get_cached_prediction(db_path: str, patient_id: str) -> Optional[dict]:
    """Return cached prediction if exists, else None."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM predictions WHERE patient_id = ?", (patient_id,)
        ).fetchone()

    if row is None:
        return None

    return {
        "patient_id": row["patient_id"],
        "risk_percent": row["risk_percent"],
        "risk_category": row["risk_category"],
        "top_factors": json.loads(row["factors"]),
        "follow_up_priority": row["follow_up_priority"],
    }


def cache_prediction(db_path: str, patient_id: str, result: dict) -> None:
    """Persist a prediction result so repeated calls skip SHAP re-computation."""
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO predictions
               (patient_id, risk_percent, risk_category, factors, follow_up_priority, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                patient_id,
                result["risk_percent"],
                result["risk_category"],
                json.dumps(result["top_factors"]),
                result["follow_up_priority"],
                now,
            ),
        )
        conn.commit()
