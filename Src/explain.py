"""
Model explainability and SHAP feature extraction helpers.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import pandas as pd
import shap

# ---------------------------------------------------------------------------
# IDS_mapping lookup tables (from DATA/IDS_mapping.csv)
# ---------------------------------------------------------------------------

ADMISSION_TYPE_MAP = {
    "1": "Emergency admission",
    "2": "Urgent admission",
    "3": "Elective admission",
    "4": "Newborn admission",
    "5": "Admission type not available",
    "6": "Admission type not recorded",
    "7": "Trauma center admission",
    "8": "Admission type not mapped",
}

DISCHARGE_DISPOSITION_MAP = {
    "1":  "Discharged to home",
    "2":  "Transferred to another short-term hospital",
    "3":  "Transferred to skilled nursing facility",
    "4":  "Transferred to intermediate care facility",
    "5":  "Transferred to another inpatient care institution",
    "6":  "Discharged to home with home health service",
    "7":  "Left against medical advice",
    "8":  "Discharged to home under Home IV care",
    "9":  "Admitted as inpatient to this hospital",
    "10": "Neonate discharged to another hospital",
    "11": "Patient expired during stay",
    "12": "Still a patient / expected return for outpatient services",
    "13": "Discharged to hospice (home)",
    "14": "Discharged to hospice (medical facility)",
    "15": "Transferred to Medicare swing bed",
    "16": "Transferred for outpatient services (other institution)",
    "17": "Referred for outpatient services (this institution)",
    "18": "Discharge disposition not recorded",
    "19": "Expired at home (Medicaid hospice)",
    "20": "Expired in medical facility (Medicaid hospice)",
    "21": "Expired, place unknown (Medicaid hospice)",
    "22": "Transferred to rehab facility",
    "23": "Transferred to long-term care hospital",
    "24": "Transferred to Medicaid-certified nursing facility",
    "25": "Discharge disposition not mapped",
    "26": "Discharge disposition unknown",
    "27": "Transferred to federal health care facility",
    "28": "Transferred to psychiatric hospital",
    "29": "Transferred to Critical Access Hospital",
    "30": "Transferred to other health care institution",
}

ADMISSION_SOURCE_MAP = {
    "1":  "Referred by physician",
    "2":  "Referred by clinic",
    "3":  "Referred by HMO",
    "4":  "Transferred from hospital",
    "5":  "Transferred from skilled nursing facility",
    "6":  "Transferred from another health care facility",
    "7":  "Admitted via emergency room",
    "8":  "Court or law enforcement",
    "9":  "Admission source not available",
    "10": "Transferred from critical access hospital",
    "11": "Normal delivery",
    "12": "Premature delivery",
    "13": "Sick newborn",
    "14": "Extramural birth",
    "15": "Admission source not available",
    "17": "Admission source not recorded",
    "18": "Transferred from home health agency",
    "19": "Readmission to same home health agency",
    "20": "Admission source not mapped",
    "21": "Admission source unknown",
    "22": "Transferred from hospital (same facility, separate claim)",
    "23": "Born inside this hospital",
    "24": "Born outside this hospital",
    "25": "Transferred from ambulatory surgery center",
    "26": "Transferred from hospice",
}

# ---------------------------------------------------------------------------
# Medication dosage value translations
# Applies to all 23 medication columns (insulin, metformin, etc.)
# ---------------------------------------------------------------------------

MEDICATION_VALUE_MAP = {
    "No":     "not prescribed",
    "Steady": "maintained at current dose",
    "Up":     "dosage increased",
    "Down":   "dosage decreased",
}

# Lab result value translations
A1C_VALUE_MAP = {
    "None": "not tested",
    "Norm": "within normal range",
    ">7":   "above 7% (elevated)",
    ">8":   "above 8% (high)",
}

GLU_VALUE_MAP = {
    "None": "not tested",
    "Norm": "within normal range",
    ">200": "above 200 mg/dL (elevated)",
    ">300": "above 300 mg/dL (very high)",
}

# Medication columns (used to identify medication vs other categorical)
_MEDICATION_COLS = {
    "metformin", "repaglinide", "nateglinide", "chlorpropamide",
    "glimepiride", "acetohexamide", "glipizide", "glyburide",
    "tolbutamide", "pioglitazone", "rosiglitazone", "acarbose",
    "miglitol", "troglitazone", "tolazamide", "examide",
    "citoglipton", "insulin", "glyburide-metformin",
    "glipizide-metformin", "glimepiride-pioglitazone",
    "metformin-rosiglitazone", "metformin-pioglitazone",
}

# Numeric feature plain names
_NUMERIC_PLAIN = {
    "numerical__time_in_hospital":    "Length of hospital stay",
    "numerical__num_lab_procedures":  "Number of lab procedures",
    "numerical__num_procedures":      "Number of procedures performed",
    "numerical__num_medications":     "Number of medications prescribed",
    "numerical__number_outpatient":   "Prior outpatient visits",
    "numerical__number_emergency":    "Prior emergency visits",
    "numerical__number_inpatient":    "Number of prior inpatient visits",
    "numerical__number_diagnoses":    "Number of diagnoses recorded",
}


# ---------------------------------------------------------------------------
# Feature name -> plain language
# ---------------------------------------------------------------------------

def _feature_name_to_plain(feature_name: str) -> str:
    """
    Convert a ColumnTransformer feature name to a human-readable phrase.

    Numeric features:  "numerical__time_in_hospital" -> "Length of hospital stay"
    Categorical OHE:   "categorical__insulin_Up"     -> "Insulin: dosage increased"
                       "categorical__discharge_disposition_id_11" -> "Patient expired during stay"
    """
    # --- Numeric features ------------------------------------------------
    if feature_name in _NUMERIC_PLAIN:
        return _NUMERIC_PLAIN[feature_name]

    # --- Categorical OHE features: "categorical__<col>_<value>" ----------
    if not feature_name.startswith("categorical__"):
        return feature_name  # fallback

    remainder = feature_name[len("categorical__"):]

    # Helper: match longest column prefix so "glyburide-metformin" wins
    # over "glyburide" when the feature is "glyburide-metformin_No"
    best_col = None
    best_len = 0
    all_cols = list(_MEDICATION_COLS) + [
        "race", "gender", "age",
        "admission_type_id", "discharge_disposition_id", "admission_source_id",
        "diag_1", "diag_2", "diag_3",
        "max_glu_serum", "A1Cresult",
        "change", "diabetesMed",
    ]
    for col in all_cols:
        if remainder.startswith(col + "_") and len(col) > best_len:
            best_col = col
            best_len = len(col)

    if best_col is None:
        return remainder  # fallback

    value = remainder[best_len + 1:]  # strip "<col>_"

    # ---- Admission type -------------------------------------------------
    if best_col == "admission_type_id":
        return ADMISSION_TYPE_MAP.get(value, f"Admission type {value}")

    # ---- Discharge disposition ------------------------------------------
    if best_col == "discharge_disposition_id":
        return DISCHARGE_DISPOSITION_MAP.get(value, f"Discharge disposition {value}")

    # ---- Admission source -----------------------------------------------
    if best_col == "admission_source_id":
        return ADMISSION_SOURCE_MAP.get(value, f"Admission source {value}")

    # ---- Diagnosis codes (ICD-9) ----------------------------------------
    diag_label = {"diag_1": "Primary", "diag_2": "Secondary", "diag_3": "Additional"}
    if best_col in diag_label:
        return f"{diag_label[best_col]} diagnosis code {value}"

    # ---- Lab results ----------------------------------------------------
    if best_col == "A1Cresult":
        desc = A1C_VALUE_MAP.get(value, value)
        return f"HbA1c test result {desc}"

    if best_col == "max_glu_serum":
        desc = GLU_VALUE_MAP.get(value, value)
        return f"Max glucose serum level {desc}"

    # ---- Medication columns ---------------------------------------------
    if best_col in _MEDICATION_COLS:
        med_name = best_col.replace("-", "/").title()
        dose_desc = MEDICATION_VALUE_MAP.get(value, value)
        return f"{med_name} {dose_desc}"

    # ---- Medication change flag -----------------------------------------
    if best_col == "change":
        if value == "Ch":
            return "Medication regimen was changed"
        return "Medication regimen was not changed"

    # ---- Diabetes medication flag ----------------------------------------
    if best_col == "diabetesMed":
        if value == "Yes":
            return "On diabetes medication"
        return "Not on diabetes medication"

    # ---- Demographics ---------------------------------------------------
    if best_col == "race":
        return f"Patient race: {value}"

    if best_col == "gender":
        label = {"Male": "Male patient", "Female": "Female patient"}.get(value, f"Gender: {value}")
        return label

    if best_col == "age":
        # value like "[70-80)" -> "Patient aged 70-80"
        clean = value.replace("[", "").replace(")", "").replace("-", " to ")
        return f"Patient aged {clean}"

    # Fallback
    return f"{best_col}: {value}"


# ---------------------------------------------------------------------------
# Risk category + follow-up priority
# ---------------------------------------------------------------------------

def _risk_category(risk_percent: float) -> str:
    """Map probability % to Low / Moderate / High (prototype thresholds, not clinically validated)."""
    if risk_percent < 30:
        return "Low"
    elif risk_percent <= 60:
        return "Moderate"
    return "High"


def _follow_up_priority(risk_category: str) -> str:
    """Derive follow-up priority directly from risk category (per README spec)."""
    return {"Low": "Low", "Moderate": "Medium", "High": "High"}[risk_category]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_patient(
    patient_row: pd.DataFrame,
    pipeline=None,
    model_path: str = "DATA/lgbm_pipeline.joblib",
    top_n: int = 3,
) -> dict:
    """
    Given a single patient's raw feature row, return risk prediction and SHAP
    explanation.

    Parameters
    ----------
    patient_row : pd.DataFrame
        A single-row DataFrame containing the same columns as the training data
        (44 feature columns, no 'target' column).
    pipeline : fitted sklearn Pipeline, optional
        If not provided, loaded from `model_path`.
    model_path : str
        Path to the saved joblib pipeline (used if `pipeline` is None).
    top_n : int
        Number of top SHAP factors to return (default 3).

    Returns
    -------
    dict with keys:
        risk_percent        : float (0-100, 1 decimal place)
        risk_category       : str   ("Low" | "Moderate" | "High")
        top_factors         : list of {"factor": str, "direction": str}
        follow_up_priority  : str   ("Low" | "Medium" | "High")
    """
    if pipeline is None:
        pipeline = joblib.load(model_path)

    preprocessor = pipeline.named_steps["preprocessor"]
    lgbm_model = pipeline.named_steps["model"]

    X_transformed = preprocessor.transform(patient_row)

    risk_prob = pipeline.predict_proba(patient_row)[0, 1]
    risk_percent = round(float(risk_prob) * 100, 1)

    global _explainer_cache
    if '_explainer_cache' not in globals():
        _explainer_cache = {}
    
    model_key = id(lgbm_model)
    if model_key not in _explainer_cache:
        _explainer_cache[model_key] = shap.TreeExplainer(lgbm_model)
    explainer = _explainer_cache[model_key]

    shap_values = explainer.shap_values(X_transformed)

    if isinstance(shap_values, list):
        sv = shap_values[1][0] if shap_values[1].ndim > 1 else shap_values[1]
    else:
        sv = shap_values[0] if shap_values.ndim > 1 else shap_values

    feature_names = preprocessor.get_feature_names_out()
    assert len(sv) == len(feature_names), (
        f"SHAP values length {len(sv)} != feature names length {len(feature_names)}"
    )

    if hasattr(X_transformed, "toarray"):
        x_dense = X_transformed.toarray()[0]
    else:
        x_dense = X_transformed[0]

    filtered_shap_pairs = []
    for feat_name, shap_val, val in zip(feature_names, sv, x_dense):
        if feat_name.startswith("numerical__") or (feat_name.startswith("categorical__") and val > 0.5):
            filtered_shap_pairs.append((feat_name, shap_val))

    shap_pairs = sorted(filtered_shap_pairs, key=lambda x: abs(x[1]), reverse=True)

    top_factors = []
    for feat_name, shap_val in shap_pairs[:top_n]:
        direction = "increases risk" if shap_val > 0 else "decreases risk"
        plain_name = _feature_name_to_plain(feat_name)
        top_factors.append({
            "factor": plain_name,
            "direction": direction,
            "shap_value": float(shap_val)
        })

    category = _risk_category(risk_percent)
    priority = _follow_up_priority(category)

    return {
        "risk_percent": risk_percent,
        "risk_category": category,
        "top_factors": top_factors,
        "follow_up_priority": priority,
    }


# ---------------------------------------------------------------------------
# Clinical sanity check (run as script)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from Src.Preprocessing import load_data

    print("Loading pipeline and data for sanity check ...")
    pipeline = joblib.load("DATA/lgbm_pipeline.joblib")
    X, y = load_data("DATA/CleanedDiabetic_data.csv")

    # --- Broad sample: Low / Moderate / High risk spread ------------------
    # Pick patients with known properties for clinical validation
    sample_indices = [0, 100, 500, 1000, 2000, 5000, 8000, 10000, 15000, 20000]

    results = []
    print("\n--- Sanity check: 10 sample patients ---\n")
    for idx in sample_indices:
        row = X.iloc[[idx]]
        true_label = y.iloc[idx]
        result = explain_patient(row, pipeline=pipeline)
        results.append({
            "idx": idx,
            "true_label": true_label,
            "risk_percent": result["risk_percent"],
            "risk_category": result["risk_category"],
            "top_factors": result["top_factors"],
        })

        label_str = "readmitted <30d" if true_label == 1 else "not readmitted"
        print(f"Patient #{idx}  |  True: {label_str}  |  Predicted: {result['risk_percent']}% ({result['risk_category']})  |  Priority: {result['follow_up_priority']}")
        for f in result["top_factors"]:
            print(f"    - {f['factor']} -> {f['direction']}")
        print()

    # --- Clinical direction checks ----------------------------------------
    print("=" * 60)
    print("  CLINICAL DIRECTION CHECKS")
    print("=" * 60)

    # Check 1: Patients with high prior inpatient visits should have higher risk
    high_inpatient = X[X["number_inpatient"] >= 3].iloc[:5]
    low_inpatient = X[X["number_inpatient"] == 0].iloc[:5]

    high_risks = [explain_patient(high_inpatient.iloc[[i]], pipeline=pipeline)["risk_percent"] for i in range(len(high_inpatient))]
    low_risks = [explain_patient(low_inpatient.iloc[[i]], pipeline=pipeline)["risk_percent"] for i in range(len(low_inpatient))]

    avg_high = sum(high_risks) / len(high_risks)
    avg_low = sum(low_risks) / len(low_risks)

    status = "[PASS]" if avg_high > avg_low else "[FAIL]"
    print(f"\n{status} Prior inpatient visits >= 3 vs 0:")
    print(f"       Avg risk with high inpatient visits : {avg_high:.1f}%")
    print(f"       Avg risk with low  inpatient visits : {avg_low:.1f}%")
    print(f"       Expected: high > low (more hospitalizations = higher readmission risk)")

    # Check 2: "Expired" discharge (code 11) should strongly decrease risk
    expired_patients = X[X["discharge_disposition_id"] == 11].iloc[:5]
    if len(expired_patients) > 0:
        expired_risks = [explain_patient(expired_patients.iloc[[i]], pipeline=pipeline)["risk_percent"] for i in range(len(expired_patients))]
        avg_expired = sum(expired_risks) / len(expired_risks)
        status = "[PASS]" if avg_expired < 20 else "[REVIEW]"
        print(f"\n{status} 'Patient expired' discharge disposition (code 11):")
        print(f"       Avg predicted risk: {avg_expired:.1f}%")
        print(f"       Expected: very low (patient died -- cannot be readmitted)")
    else:
        print("\n[SKIP] No expired patients found in sample.")

    # Check 3: Longer hospital stays should tend toward higher risk
    long_stay = X[X["time_in_hospital"] >= 10].iloc[:5]
    short_stay = X[X["time_in_hospital"] <= 2].iloc[:5]
    long_risks = [explain_patient(long_stay.iloc[[i]], pipeline=pipeline)["risk_percent"] for i in range(len(long_stay))]
    short_risks = [explain_patient(short_stay.iloc[[i]], pipeline=pipeline)["risk_percent"] for i in range(len(short_stay))]
    avg_long = sum(long_risks) / len(long_risks)
    avg_short = sum(short_risks) / len(short_risks)
    status = "[PASS]" if avg_long > avg_short else "[REVIEW]"
    print(f"\n{status} Long stay (>=10 days) vs short stay (<=2 days):")
    print(f"       Avg risk long  stays : {avg_long:.1f}%")
    print(f"       Avg risk short stays : {avg_short:.1f}%")
    print(f"       Expected: long > short (more severe illness = higher readmission risk)")

    print("\nSanity check complete [OK]")
