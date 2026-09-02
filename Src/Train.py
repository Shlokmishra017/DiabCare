"""
Model training script for baseline and LightGBM models.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import pandas as pd
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

RANDOM_STATE = 42
TEST_SIZE = 0.20
MODEL_OUTPUT_PATH = "DATA/lgbm_pipeline.joblib"


def evaluate_pipeline(pipeline, X_test, y_test, label: str):
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    auc = roc_auc_score(y_test, y_prob)
    pr_auc = average_precision_score(y_test, y_prob)
    f1 = f1_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)

    print(f"\n--- {label} ---")
    print(f"ROC-AUC   : {auc:.4f}")
    print(f"PR-AUC    : {pr_auc:.4f}")
    print(f"F1 Score  : {f1:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"Precision : {precision:.4f}")
    print(f"\n{classification_report(y_test, y_pred)}")

    return auc


def main():
    print("Loading cleaned dataset...")
    X, y = load_data("DATA/CleanedDiabetic_data.csv")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Train set: {X_train.shape[0]} rows | Test set: {X_test.shape[0]} rows")

    print("\nTraining Logistic Regression baseline...")
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

    print("\nTraining LightGBM grid search...")
    param_grid = [
        {"num_leaves": 31,  "learning_rate": 0.05, "n_estimators": 200},
        {"num_leaves": 31,  "learning_rate": 0.10, "n_estimators": 150},
        {"num_leaves": 50,  "learning_rate": 0.05, "n_estimators": 200},
        {"num_leaves": 50,  "learning_rate": 0.10, "n_estimators": 150},
    ]

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    best_auc = -1
    best_params = None

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
        print(f"Params {params} -> CV-AUC: {mean_auc:.4f}")

        if mean_auc > best_auc:
            best_auc = mean_auc
            best_params = params

    print(f"\nBest CV-AUC: {best_auc:.4f} | Best params: {best_params}")

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
    lgbm_auc = evaluate_pipeline(best_lgbm_pipeline, X_test, y_test, "LightGBM Primary Model")

    os.makedirs("DATA", exist_ok=True)
    joblib.dump(best_lgbm_pipeline, MODEL_OUTPUT_PATH)
    print(f"\nModel saved to {MODEL_OUTPUT_PATH}")


if __name__ == "__main__":
    main()

