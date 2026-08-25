"""
DiabCare AI — Model Training Script
======================================
Phase 2: Trains a Logistic Regression baseline and a LightGBM primary model,
both wrapped in full sklearn Pipelines. Saves the best LightGBM pipeline via
joblib.dump.

Run from the project root:
    python -m Src.Train
    # or
    cd d:/DiabCare && .venv/Scripts/python.exe -m Src.Train

Outputs:
    DATA/lgbm_pipeline.joblib   — full preprocessing + LightGBM pipeline
    Metric comparison table printed to stdout
"""

import sys
import os

# Allow running from project root without package install
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pyrefly: ignore [missing-import]
import joblib
import pandas as pd
# pyrefly: ignore [missing-import]
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

from Src.Preprocessing import build_preprocessor, load_data

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
RANDOM_STATE = 42
TEST_SIZE = 0.20
MODEL_OUTPUT_PATH = "DATA/lgbm_pipeline.joblib"


def evaluate_pipeline(pipeline, X_test, y_test, label: str):
    """Print a standard metric block and return the AUC score."""
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    auc = roc_auc_score(y_test, y_prob)
    pr_auc = average_precision_score(y_test, y_prob)
    f1 = f1_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)

    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    print(f"  ROC-AUC   : {auc:.4f}")
    print(f"  PR-AUC    : {pr_auc:.4f}")
    print(f"  F1 Score  : {f1:.4f}")
    print(f"  Recall    : {recall:.4f}")
    print(f"  Precision : {precision:.4f}")
    print(f"\n{classification_report(y_test, y_pred)}")

    return auc


def main():
    print("=" * 55)
    print("  DiabCare AI -- Phase 2: Model Training")
    print("=" * 55)

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    print("\n[1/5] Loading cleaned dataset ...")
    X, y = load_data("DATA/CleanedDiabetic_data.csv")
    print(f"      X shape : {X.shape}")
    print(f"      y distribution (%):\n{y.value_counts(normalize=True).mul(100).round(2).to_string()}")

    # ------------------------------------------------------------------
    # 2. Train / test split  (stratified, fixed seed)
    # ------------------------------------------------------------------
    print("\n[2/5] Splitting data (80/20, stratified) ...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"      Train : {X_train.shape[0]} rows  |  Test : {X_test.shape[0]} rows")

    # ------------------------------------------------------------------
    # 3. Baseline — Logistic Regression inside full Pipeline
    # ------------------------------------------------------------------
    print("\n[3/5] Training Logistic Regression baseline ...")
    lr_pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("model", LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=RANDOM_STATE,
            solver="liblinear",
        )),
    ])
    lr_pipeline.fit(X_train, y_train)
    baseline_auc = evaluate_pipeline(lr_pipeline, X_test, y_test, "Logistic Regression Baseline")

    # ------------------------------------------------------------------
    # 4. Primary model — LightGBM with light manual grid search
    # ------------------------------------------------------------------
    print("\n[4/5] Training LightGBM (manual grid + StratifiedKFold CV) ...")

    # Small manual grid: 4 combinations (README: 3–5 combos, no exhaustive search)
    param_grid = [
        {"num_leaves": 31,  "learning_rate": 0.05, "n_estimators": 200},
        {"num_leaves": 31,  "learning_rate": 0.10, "n_estimators": 150},
        {"num_leaves": 50,  "learning_rate": 0.05, "n_estimators": 200},
        {"num_leaves": 50,  "learning_rate": 0.10, "n_estimators": 150},
    ]

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    best_auc = -1
    best_params = None

    print(f"\n  {'num_leaves':>12} {'lr':>8} {'n_est':>8} {'CV-AUC':>10}")
    print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*10}")

    for params in param_grid:
        lgbm_pipeline = Pipeline([
            ("preprocessor", build_preprocessor()),
            ("model", LGBMClassifier(
                class_weight="balanced",
                random_state=RANDOM_STATE,
                verbose=-1,
                **params,
            )),
        ])
        cv_scores = cross_val_score(
            lgbm_pipeline, X_train, y_train,
            cv=cv, scoring="roc_auc", n_jobs=-1
        )
        mean_auc = cv_scores.mean()
        print(f"  {params['num_leaves']:>12} {params['learning_rate']:>8.2f} {params['n_estimators']:>8} {mean_auc:>10.4f}")

        if mean_auc > best_auc:
            best_auc = mean_auc
            best_params = params

    print(f"\n  Best CV-AUC : {best_auc:.4f}  |  Best params : {best_params}")

    assert best_params is not None, "No best params found — param_grid is empty."

    # Retrain best config on full training set
    print("\n  Retraining best config on full training set ...")
    best_lgbm_pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("model", LGBMClassifier(
            class_weight="balanced",
            random_state=RANDOM_STATE,
            verbose=-1,
            **best_params,
        )),
    ])
    best_lgbm_pipeline.fit(X_train, y_train)
    lgbm_auc = evaluate_pipeline(best_lgbm_pipeline, X_test, y_test, "LightGBM (Primary Model)")

    # ------------------------------------------------------------------
    # 5. Leakage / sanity checks
    # ------------------------------------------------------------------
    print("\n[5/5] Sanity checks ...")

    if lgbm_auc > 0.85:
        print("  [WARNING] LightGBM AUC > 0.85 — suspect target leakage!")
        print("       Investigate features before treating this as a win.")
    elif lgbm_auc < 0.60:
        print("  [WARNING] LightGBM AUC < 0.60 — below expected range (0.65-0.69).")
        print("       Check preprocessing / target definition for bugs.")
    else:
        print(f"  [OK] LightGBM AUC {lgbm_auc:.4f} is in the expected 0.65-0.69 range.")

    if lgbm_auc > baseline_auc:
        print(f"  [OK] LightGBM AUC ({lgbm_auc:.4f}) > Logistic Regression AUC ({baseline_auc:.4f})")
    else:
        print(f"  [WARNING] LightGBM AUC ({lgbm_auc:.4f}) did NOT exceed baseline ({baseline_auc:.4f})")
        print("       Treat as a bug signal — investigate preprocessing/target before proceeding.")

    # ------------------------------------------------------------------
    # 6. Save full pipeline
    # ------------------------------------------------------------------
    os.makedirs("DATA", exist_ok=True)
    joblib.dump(best_lgbm_pipeline, MODEL_OUTPUT_PATH)
    print(f"\n  [SAVED] Full pipeline saved -> {MODEL_OUTPUT_PATH}")

    # ------------------------------------------------------------------
    # 7. Summary comparison table
    # ------------------------------------------------------------------
    print("\n" + "=" * 55)
    print("  METRIC COMPARISON SUMMARY")
    print("=" * 55)
    summary = pd.DataFrame({
        "Model": ["Logistic Regression (baseline)", f"LightGBM ({best_params})"],
        "Test AUC": [round(baseline_auc, 4), round(lgbm_auc, 4)],
    })
    print(summary.to_string(index=False))
    print("\n  Expected AUC range: 0.65 – 0.69")
    print("  Phase 2 DONE [OK]")


if __name__ == "__main__":
    main()
