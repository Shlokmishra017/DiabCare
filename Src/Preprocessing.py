"""
DiabCare AI — Preprocessing Module
====================================
Defines column lists, builds the ColumnTransformer preprocessor, and
provides a helper to load the cleaned dataset.

Usage:
    from Src.Preprocessing import load_data, build_preprocessor, NUMERIC_COLS, CATEGORICAL_COLS
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ---------------------------------------------------------------------------
# Column definitions
# NOTE: admission_type_id, discharge_disposition_id, admission_source_id are
# integer codes referencing IDS_mapping.csv — they are treated as categorical
# (not scaled), per the README spec.
# ---------------------------------------------------------------------------

NUMERIC_COLS = [
    "time_in_hospital",
    "num_lab_procedures",
    "num_procedures",
    "num_medications",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "number_diagnoses",
]

CATEGORICAL_COLS = [
    # Demographics / administrative
    "race",
    "gender",
    "age",
    # ID-code columns treated as categorical (not numeric)
    "admission_type_id",
    "discharge_disposition_id",
    "admission_source_id",
    # Diagnosis codes
    "diag_1",
    "diag_2",
    "diag_3",
    # Lab / glucose results
    "max_glu_serum",
    "A1Cresult",
    # Medication columns
    "metformin",
    "repaglinide",
    "nateglinide",
    "chlorpropamide",
    "glimepiride",
    "acetohexamide",
    "glipizide",
    "glyburide",
    "tolbutamide",
    "pioglitazone",
    "rosiglitazone",
    "acarbose",
    "miglitol",
    "troglitazone",
    "tolazamide",
    "examide",
    "citoglipton",
    "insulin",
    "glyburide-metformin",
    "glipizide-metformin",
    "glimepiride-pioglitazone",
    "metformin-rosiglitazone",
    "metformin-pioglitazone",
    "change",
    "diabetesMed",
]

TARGET_COL = "target"


def load_data(cleaned_csv_path: str = "DATA/CleanedDiabetic_data.csv"):
    """
    Load the cleaned dataset.

    Returns
    -------
    X : pd.DataFrame  — feature matrix (44 columns, no target)
    y : pd.Series     — binary target (1 = readmitted within 30 days)
    """
    df = pd.read_csv(cleaned_csv_path)
    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]
    return X, y


def build_preprocessor() -> ColumnTransformer:
    """
    Build the sklearn ColumnTransformer:
      - Numeric cols  : median imputation → StandardScaler
      - Categorical cols : most-frequent imputation → OneHotEncoder(handle_unknown='ignore')

    handle_unknown='ignore' is mandatory so that single-patient inference at
    demo time works even if a category value was not seen during training.

    Returns
    -------
    preprocessor : ColumnTransformer (unfitted)
    """
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer([
        ("numerical", numeric_pipeline, NUMERIC_COLS),
        ("categorical", categorical_pipeline, CATEGORICAL_COLS),
    ])

    return preprocessor
