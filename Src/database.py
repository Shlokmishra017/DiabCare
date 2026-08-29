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
# pyrefly: ignore [missing-import]
import bcrypt

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
    patient_id          TEXT PRIMARY KEY,
    summary             TEXT,
    name                TEXT,
    assigned_doctor_id  TEXT,
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
    created_at          TEXT,
    follow_up_status    TEXT CHECK(follow_up_status IN ('Pending','Scheduled','Completed')) DEFAULT 'Pending',
    scheduled_date      TEXT
);
"""

CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    name          TEXT,
    email         TEXT UNIQUE,
    password_hash TEXT,
    role          TEXT CHECK(role IN ('doctor','admin')),
    status        TEXT CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'approved',
    education     TEXT,
    reference_id  TEXT,
    created_at    TEXT
);
"""


def _seed_users(conn) -> None:
    """Seed default doctor and admin accounts if they don't exist."""
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        now = datetime.now(timezone.utc).isoformat()
        users_data = [
            ("U-1001", "Dr. Alice Smith", "doctor1@diabcare.ai", "doctor123", "doctor", "approved", "MD - Endocrinology (Harvard Medical School)", "REF-DOC-1001"),
            ("U-1002", "Dr. Bob Jones", "doctor2@diabcare.ai", "doctor288", "doctor", "approved", "MBBS, MD - Diabetology (Johns Hopkins)", "REF-DOC-1002"),
            ("U-1003", "Admin User", "admin@diabcare.ai", "admin999", "admin", "approved", "System Administrator", "REF-ADM-0001"),
        ]
        for uid, name, email, pwd, role, status, edu, ref in users_data:
            pwd_bytes = pwd.encode('utf-8')
            salt = bcrypt.gensalt()
            pwd_hash = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
            conn.execute(
                "INSERT INTO users (user_id, name, email, password_hash, role, status, education, reference_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, name, email, pwd_hash, role, status, edu, ref, now)
            )
        conn.commit()
    else:
        # Update existing seeded users if education or reference_id is NULL
        conn.execute("UPDATE users SET education = 'MD - Endocrinology (Harvard Medical School)', reference_id = 'REF-DOC-1001' WHERE user_id = 'U-1001' AND (education IS NULL OR reference_id IS NULL)")
        conn.execute("UPDATE users SET education = 'MBBS, MD - Diabetology (Johns Hopkins)', reference_id = 'REF-DOC-1002' WHERE user_id = 'U-1002' AND (education IS NULL OR reference_id IS NULL)")
        conn.execute("UPDATE users SET education = 'System Administrator', reference_id = 'REF-ADM-0001' WHERE user_id = 'U-1003' AND (education IS NULL OR reference_id IS NULL)")
        conn.commit()


def init_db(db_path: str) -> None:
    """Create tables if they don't exist."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        try:
            table_info = cursor.execute("PRAGMA table_info(users)").fetchall()
            if table_info:
                has_status = any(col[1] == "status" for col in table_info)
                if not has_status:
                    conn.execute("DROP TABLE users")
                else:
                    # Check for education and reference_id columns
                    col_names = [col[1] for col in table_info]
                    if "education" not in col_names:
                        conn.execute("ALTER TABLE users ADD COLUMN education TEXT")
                        print("[Migration] Added education column to users table.")
                    if "reference_id" not in col_names:
                        conn.execute("ALTER TABLE users ADD COLUMN reference_id TEXT")
                        print("[Migration] Added reference_id column to users table.")
                    conn.commit()
        except Exception as e:
            print(f"[Warning] Migration check failed: {str(e)}")

        conn.execute(CREATE_PATIENTS_SQL)
        conn.execute(CREATE_PREDICTIONS_SQL)
        conn.execute(CREATE_USERS_SQL)
        conn.commit()

        # Check if patients table needs assigned_doctor_id column migration
        try:
            pat_info = cursor.execute("PRAGMA table_info(patients)").fetchall()
            if pat_info:
                has_assigned_doc = any(col[1] == "assigned_doctor_id" for col in pat_info)
                if not has_assigned_doc:
                    conn.execute("ALTER TABLE patients ADD COLUMN assigned_doctor_id TEXT")
                    conn.commit()
                    print("[Migration] Added assigned_doctor_id column to patients table.")
        except Exception as e:
            print(f"[Warning] Patients table assigned_doctor_id migration failed: {str(e)}")

        # Check if predictions table needs follow_up_status or scheduled_date column migration
        try:
            pred_info = cursor.execute("PRAGMA table_info(predictions)").fetchall()
            if pred_info:
                pred_cols = [col[1] for col in pred_info]
                if "follow_up_status" not in pred_cols:
                    conn.execute(
                        "ALTER TABLE predictions ADD COLUMN follow_up_status TEXT CHECK(follow_up_status IN ('Pending','Scheduled','Completed')) DEFAULT 'Pending'"
                    )
                    conn.commit()
                    print("[Migration] Added follow_up_status column to predictions table.")
                if "scheduled_date" not in pred_cols:
                    conn.execute("ALTER TABLE predictions ADD COLUMN scheduled_date TEXT")
                    conn.commit()
                    print("[Migration] Added scheduled_date column to predictions table.")
        except Exception as e:
            print(f"[Warning] Predictions table migration failed: {str(e)}")

        _seed_users(conn)

        # Seed default patient assignments if assigned_doctor_id is unassigned
        try:
            conn.execute("UPDATE patients SET assigned_doctor_id = 'U-1001' WHERE patient_id = '2552952' AND assigned_doctor_id IS NULL")
            conn.execute("UPDATE patients SET assigned_doctor_id = 'U-1002' WHERE patient_id = '149190' AND assigned_doctor_id IS NULL")
            conn.commit()
        except Exception:
            pass


def get_user_by_email(db_path: str, email: str) -> Optional[dict]:
    """Return user data dict if email exists, else None."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    if row is None:
        return None
    row_dict = dict(row)
    return {
        "user_id": row_dict["user_id"],
        "name": row_dict["name"],
        "email": row_dict["email"],
        "password_hash": row_dict["password_hash"],
        "role": row_dict["role"],
        "status": row_dict["status"],
        "education": row_dict.get("education"),
        "reference_id": row_dict.get("reference_id"),
        "created_at": row_dict["created_at"]
    }


def get_user_by_id(db_path: str, user_id: str) -> Optional[dict]:
    """Return user data dict if user_id exists, else None."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    if row is None:
        return None
    row_dict = dict(row)
    return {
        "user_id": row_dict["user_id"],
        "name": row_dict["name"],
        "email": row_dict["email"],
        "password_hash": row_dict["password_hash"],
        "role": row_dict["role"],
        "status": row_dict["status"],
        "education": row_dict.get("education"),
        "reference_id": row_dict.get("reference_id"),
        "created_at": row_dict["created_at"]
    }


def update_user_profile(db_path: str, user_id: str, name: str, education: str, reference_id: str) -> None:
    """Update profile details (name, education, reference_id) for a user."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE users SET name = ?, education = ?, reference_id = ? WHERE user_id = ?",
            (name, education, reference_id, user_id)
        )
        conn.commit()


def save_new_user(db_path: str, user_id: str, name: str, email: str, password_hash: str, role: str, status: str, education: str = None, reference_id: str = None) -> None:
    """Register a new user in the database."""
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO users (user_id, name, email, password_hash, role, status, education, reference_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, email, password_hash, role, status, education, reference_id, now)
        )
        conn.commit()


def get_pending_requests(db_path: str) -> list[dict]:
    """Get all doctor accounts pending access approval."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT user_id, name, email, role, education, reference_id, created_at FROM users WHERE status = 'pending' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_doctors(db_path: str) -> list[dict]:
    """Get all doctor accounts with full profile data and approval status."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT user_id, name, email, role, status, education, reference_id, created_at FROM users WHERE role = 'doctor' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_admins(db_path: str) -> list[dict]:
    """Get all admin accounts."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT user_id, name, email, role, status, education, reference_id, created_at FROM users WHERE role = 'admin' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_user_status(db_path: str, user_id: str, status: str) -> None:
    """Approve or reject a user's sign up request."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE users SET status = ? WHERE user_id = ?",
            (status, user_id)
        )
        conn.commit()



def _build_summary(row: pd.Series) -> str:
    """Build a human-readable one-line patient summary for the /patients endpoint."""
    gender = str(row.get("gender", "Unknown"))
    age = str(row.get("age", "Unknown")).replace("[", "").replace(")", "")
    race = str(row.get("race", "Unknown"))
    time_in = row.get("time_in_hospital", "?")
    n_inpatient = row.get("number_inpatient", 0)
    
    # Extra fields for the details expander
    n_medications = row.get("num_medications", 0)
    n_lab = row.get("num_lab_procedures", 0)
    n_diagnoses = row.get("number_diagnoses", 0)
    n_outpatient = row.get("number_outpatient", 0)
    n_emergency = row.get("number_emergency", 0)
    n_procedures = row.get("num_procedures", 0)
    
    return (
        f"{gender}, {age} yrs, {race} | "
        f"Stay: {time_in}d | Prior inpatient: {n_inpatient} | "
        f"Meds: {n_medications} | Lab: {n_lab} | Diagnoses: {n_diagnoses} | "
        f"Outpatient: {n_outpatient} | Emergency: {n_emergency} | Procedures: {n_procedures}"
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


def save_new_patient(db_path: str, patient_id: str, features: dict) -> None:
    """Save a new patient's raw features into the patients table."""
    summary = _build_summary(pd.Series(features))
    name = features.get("name")

    cols = ["patient_id", "summary", "name"] + _FEATURE_COLS
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(f'"{c}"' for c in cols)

    # Build values list matching the feature column definitions
    values = [
        patient_id,
        summary,
        name,
    ] + [
        str(features.get(col)) if features.get(col) is not None else None
        for col in _FEATURE_COLS
    ]

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO patients ({col_names}) VALUES ({placeholders})",
            values,
        )
        conn.commit()


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


def assign_patient_to_doctor(db_path: str, patient_id: str, doctor_id: Optional[str]) -> None:
    """Assign a patient to a doctor (or unassign if doctor_id is None)."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE patients SET assigned_doctor_id = ? WHERE patient_id = ?",
            (doctor_id, patient_id)
        )
        conn.commit()


def get_all_patients(db_path: str) -> list[dict]:
    """Return all patients with assigned doctor information."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT p.patient_id, p.summary, p.name, p.assigned_doctor_id, u.name AS assigned_doctor_name, pr.risk_percent, pr.follow_up_status, pr.scheduled_date
            FROM patients p
            LEFT JOIN predictions pr ON p.patient_id = pr.patient_id
            LEFT JOIN users u ON p.assigned_doctor_id = u.user_id
            ORDER BY COALESCE(pr.risk_percent, -1) DESC, p.patient_id ASC
            """
        ).fetchall()
    return [
        {
            "patient_id": r["patient_id"],
            "summary": r["summary"],
            "name": r["name"],
            "assigned_doctor_id": r["assigned_doctor_id"],
            "assigned_doctor_name": r["assigned_doctor_name"],
            "risk_percent": r["risk_percent"],
            "follow_up_status": r["follow_up_status"] if r["follow_up_status"] is not None else "Pending",
            "scheduled_date": r["scheduled_date"] if "scheduled_date" in r.keys() else None,
        }
        for r in rows
    ]


def get_cached_prediction(db_path: str, patient_id: str) -> Optional[dict]:
    """Return cached prediction if exists, else None."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM predictions WHERE patient_id = ?", (patient_id,)
        ).fetchone()

    if row is None:
        return None

    # Retrieve follow_up_status and scheduled_date
    follow_up_status = "Pending"
    scheduled_date = None
    try:
        if "follow_up_status" in row.keys() and row["follow_up_status"] is not None:
            follow_up_status = row["follow_up_status"]
        if "scheduled_date" in row.keys() and row["scheduled_date"] is not None:
            scheduled_date = row["scheduled_date"]
    except Exception:
        pass

    return {
        "patient_id": row["patient_id"],
        "risk_percent": row["risk_percent"],
        "risk_category": row["risk_category"],
        "top_factors": json.loads(row["factors"]),
        "follow_up_priority": row["follow_up_priority"],
        "follow_up_status": follow_up_status,
        "scheduled_date": scheduled_date,
    }


def cache_prediction(db_path: str, patient_id: str, result: dict) -> None:
    """Persist a prediction result so repeated calls skip SHAP re-computation."""
    now = datetime.now(timezone.utc).isoformat()
    
    # Check if we already have status/scheduled_date in DB to preserve them
    existing_status = "Pending"
    existing_scheduled_date = None
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT follow_up_status, scheduled_date FROM predictions WHERE patient_id = ?", (patient_id,)).fetchone()
        if row is not None:
            try:
                if "follow_up_status" in row.keys() and row["follow_up_status"] is not None:
                    existing_status = row["follow_up_status"]
                if "scheduled_date" in row.keys() and row["scheduled_date"] is not None:
                    existing_scheduled_date = row["scheduled_date"]
            except Exception:
                pass

    follow_up_status = result.get("follow_up_status", existing_status)
    scheduled_date = result.get("scheduled_date", existing_scheduled_date)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO predictions
               (patient_id, risk_percent, risk_category, factors, follow_up_priority, created_at, follow_up_status, scheduled_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                patient_id,
                result["risk_percent"],
                result["risk_category"],
                json.dumps(result["top_factors"]),
                result["follow_up_priority"],
                now,
                follow_up_status,
                scheduled_date,
            ),
        )
        conn.commit()


def get_patient_record(db_path: str, patient_id: str) -> Optional[dict]:
    """Get patient basic info dictionary including assigned_doctor_id."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT patient_id, summary, name, assigned_doctor_id FROM patients WHERE patient_id = ?",
            (patient_id,)
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def update_follow_up_status(db_path: str, patient_id: str, status: str, scheduled_date: Optional[str] = None) -> None:
    """Update the follow-up status and scheduled_date for a patient's prediction record."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        if status == "Pending":
            final_date = None
        elif status == "Completed":
            if scheduled_date is not None:
                final_date = scheduled_date
            else:
                row = conn.execute("SELECT scheduled_date FROM predictions WHERE patient_id = ?", (patient_id,)).fetchone()
                final_date = row["scheduled_date"] if row and "scheduled_date" in row.keys() else None
        else:  # Scheduled
            final_date = scheduled_date

        conn.execute(
            "UPDATE predictions SET follow_up_status = ?, scheduled_date = ? WHERE patient_id = ?",
            (status, final_date, patient_id)
        )
        conn.commit()


def get_dashboard_stats(db_path: str) -> dict:
    """Return dict of counts for doctor and admin dashboard metrics."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Approved doctors
        approved_docs = cursor.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'doctor' AND status = 'approved'"
        ).fetchone()[0]
        
        # Pending doctor requests
        pending_docs = cursor.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'doctor' AND status = 'pending'"
        ).fetchone()[0]
        
        # Rejected doctor requests
        rejected_docs = cursor.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'doctor' AND status = 'rejected'"
        ).fetchone()[0]
        
        # Total doctors
        total_docs = cursor.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'doctor'"
        ).fetchone()[0]
        
        # Total admins
        total_admins = cursor.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin'"
        ).fetchone()[0]
        
        # Total patients in the registry
        total_patients = cursor.execute(
            "SELECT COUNT(*) FROM patients"
        ).fetchone()[0]
        
        # Risk counts (high, moderate) from predictions cache
        high_risk = cursor.execute(
            "SELECT COUNT(*) FROM predictions WHERE risk_category = 'High'"
        ).fetchone()[0]
        
        mod_risk = cursor.execute(
            "SELECT COUNT(*) FROM predictions WHERE risk_category = 'Moderate'"
        ).fetchone()[0]
        
        # Pending follow-ups
        pending_followups = cursor.execute(
            "SELECT COUNT(*) FROM predictions WHERE follow_up_status = 'Pending'"
        ).fetchone()[0]
        
    return {
        "approved_doctors": approved_docs,
        "pending_doctors": pending_docs,
        "rejected_doctors": rejected_docs,
        "total_doctors": total_docs,
        "total_admins": total_admins,
        "total_patients": total_patients,
        "high_risk_patients": high_risk,
        "moderate_risk_patients": mod_risk,
        "pending_followups": pending_followups,
    }
