# README — DiabCare AI (Agent Instructions)

This file is written for any AI coding agent (or new contributor) picking up this project. Read this fully before writing any code. It describes what the project is, what "done" looks like at each phase, and the exact technical decisions already made — do not deviate from them without flagging it to the human first.

---

## 1. Project Overview

**Name:** DiabCare AI
**Category:** Chronic Disease Risk Prediction System (hackathon submission)

**What it does:** Given a diabetic patient's clinical record, the system predicts their 30-day hospital readmission risk, explains *why* the model gave that score (in plain language, using SHAP), and outputs a follow-up priority tier for hospital staff.

**Core demo flow (4 steps, this is the entire product surface):**
1. User selects/enters a patient record.
2. System returns risk % + category (Low <30%, Moderate 30–60%, High >60%).
3. System returns top factors driving that specific score (SHAP-based, plain language, not raw feature names/numbers).
4. System returns a follow-up priority recommendation.

**Dataset:** UCI "Diabetes 130-US Hospitals" dataset — 101,766 real encounters across 130 hospitals, pre-labeled with 30-day readmission outcome (`readmitted` column: `NO` / `<30` / `>30`). Public dataset, no access approval needed.

**Non-negotiable honesty constraints (apply to all phases, including any generated docs/UI copy):**
- Expected model performance is **AUC ~0.65–0.69**, not 90%+. This matches published research on this exact dataset. Never write code, comments, or UI text implying higher accuracy is the goal or expected outcome.
- SHAP output is feature *importance/correlation*, never describe it as *causation*. Never generate text like "X causes readmission."
- Risk thresholds (30%/60%) are prototype cutoffs, not clinically validated — do not present them as clinically derived.
- This is a prototype on historical US data — never generate claims about live hospital validation or non-US applicability.

**Explicit out-of-scope (do not build these unless a human explicitly asks):**
CNN/LSTM models, historical encounter timeline reconstruction, calibration curve UI, Maps API integration, multi-hospital live system, chatbot interface, image models, real-time streaming pipelines. A PyTorch MLP comparison model is optional/stretch only — never a default task.

---

## 2. Tech Stack (fixed — do not substitute without explicit instruction)

| Layer | Tool |
|---|---|
| Data handling | Pandas, NumPy |
| Preprocessing | scikit-learn (ColumnTransformer, Pipeline) |
| Baseline model | Logistic Regression |
| Primary model | LightGBM |
| Explainability | SHAP (TreeExplainer specifically — not KernelExplainer/DeepExplainer) |
| Backend | FastAPI |
| Database | SQLite |
| Frontend | HTML/CSS/JS (static, no framework unless instructed) |
| Deployment | Render |

---

## 3. Phase-by-Phase Instructions

### Phase 1 — Data Manipulation

**Goal:** produce a clean, model-ready dataset with a correctly defined binary target.

1. **Load** the raw CSV with Pandas. The dataset encodes missing values as the string `'?'`, not NaN — first operation must be `df.replace('?', np.nan)`.
2. **Understand coded columns** before touching them: `admission_type_id`, `discharge_disposition_id`, `admission_source_id` are integer codes referencing a separate IDs_mapping file, not raw categorical values. Map or document these; do not treat them as arbitrary integers for scaling.
3. **Define the target:** binary from the `readmitted` column — `1` if value is `<30`, else `0` (this covers both `NO` and `>30`). Do not build a 3-class classifier; the product spec is binary 30-day risk.
4. **Check class balance** (`value_counts(normalize=True)`). Expect strong imbalance (~11% positive class). This must inform every downstream modeling decision (stratified splits, class weighting, evaluation metric choice) — accuracy alone is an invalid metric here and must never be the headline number.
5. **Handle missing data:** drop columns with very high missing percentage (verify via `.isnull().mean()`, don't hardcode a list blindly — but `weight`, `payer_code`, and `medical_specialty` are known high-missingness columns in this dataset and are the expected candidates for dropping).
6. **Drop identifier columns from the feature set** (`encounter_id`, `patient_nbr`) — keep `encounter_id` around separately as a lookup key for the API/demo, never as a model input.
7. **Separate feature types**: numeric columns (e.g. `time_in_hospital`, `num_lab_procedures`, `num_medications`) vs categorical columns (e.g. `race`, `gender`, `diag_1`, `insulin`, `change`, `diabetesMed`). This split feeds directly into the preprocessing pipeline in Phase 2.
8. **Output of this phase:** a cleaned CSV/dataframe checkpoint, saved to disk, plus a short written note of what was dropped and why (for the eventual PPT/explanation, and for reproducibility).

**Do not** perform any scaling, encoding, or target leakage-prone transformations directly on the raw dataframe in this phase — that belongs inside the sklearn Pipeline in Phase 2, so it can be applied identically at inference time on single patients.

---

### Phase 2 — Model Training

**Goal:** a trained, saved pipeline (preprocessing + model) that beats the baseline and is ready for SHAP explanation.

**Step 2a — Preprocessing pipeline**
- Build a `ColumnTransformer`: `StandardScaler` on numeric columns, `OneHotEncoder(handle_unknown='ignore')` on categorical columns. `handle_unknown='ignore'` is mandatory — single-patient inference requests at demo time may contain category values not seen in training folds.
- Wrap preprocessing + model together in a single `sklearn.pipeline.Pipeline` object. This is required so the *entire* pipeline can be saved and reused at inference time without reimplementing preprocessing separately in the API layer.

**Step 2b — Train/test split**
- Use `train_test_split(..., stratify=y, test_size=0.2, random_state=<fixed seed>)`. Stratification is mandatory given class imbalance. Fix a random seed for reproducibility.

**Step 2c — Baseline model**
- Train `LogisticRegression` inside the pipeline.
- Evaluate using `roc_auc_score`, `f1_score`, `recall_score`, `precision_score` — never report `.score()` (accuracy) as a primary metric; if reported at all, it must be alongside AUC/F1 with a note on class imbalance.
- Record these numbers — they are the comparison baseline for the primary model.

**Step 2d — Primary model (LightGBM)**
- Swap the pipeline's model step for `LGBMClassifier`.
- Address class imbalance via `class_weight='balanced'` (do not implement manual oversampling/SMOTE unless explicitly instructed — out of scope for the timeline).
- Light tuning only: vary `num_leaves`, `learning_rate`, `n_estimators` across a small manual grid (3–5 combinations), evaluated via `StratifiedKFold` (5-fold) cross-validation on AUC. Do not run exhaustive/automated hyperparameter search (e.g. Optuna, GridSearchCV over large grids) — not needed at this scale and wastes time budget.
- Confirm LightGBM AUC exceeds the Logistic Regression baseline. If it does not, treat this as a bug signal in preprocessing/target definition, not as an acceptable result — investigate before proceeding.
- Expected final AUC range: **0.65–0.69**. If results land far outside this range (e.g. >0.85), suspect target leakage (a feature that directly encodes the outcome) and investigate before treating it as a win.

**Step 2e — Persist the model**
- Save the full pipeline (preprocessing + model together) via `joblib.dump`, not just the raw model. The API layer (Phase 4) loads this single artifact and must not need to reimplement any preprocessing logic.

**Output of this phase:** a saved pipeline artifact, a written comparison of baseline vs primary model metrics.

---

### Phase 3 — Explainability (SHAP)

**Goal:** a function that takes one patient's raw feature row and returns risk %, category, and top 3 plain-language factors.

1. SHAP's `TreeExplainer` requires the raw LightGBM model object, not the full sklearn `Pipeline` wrapper. Extract the fitted LightGBM step from the pipeline, and separately transform input data through the fitted preprocessor before passing to SHAP.
2. Compute SHAP values for the target patient(s): `explainer.shap_values(X_transformed)`.
3. Map SHAP values back to human-readable feature names using `preprocessor.get_feature_names_out()` — one-hot encoded columns will look like `cat__insulin_Up`; translate these into plain phrases (e.g. "Insulin dosage increased") rather than surfacing raw column names to the API/UI layer.
4. Sort by absolute SHAP value, take the top 3, and generate a sentence per factor: `"{plain-language feature} {'increases' if shap_val > 0 else 'decreases'} risk"`.
5. Sanity-check output against several real patient rows manually — confirm direction/sign makes clinical sense (e.g. more prior inpatient visits should increase risk). If signs look inverted, check the target's binary encoding direction (1 = readmitted within 30 days) against SHAP's convention before assuming the model is wrong.

**Output of this phase:** a reusable function `explain_patient(patient_row) -> {risk_percent, risk_category, top_factors, follow_up_priority}` — this is the core function the API layer wraps.

**Follow-up priority logic:** derive directly from `risk_category` (e.g. High → High priority, Moderate → Medium, Low → Low/None) unless a human specifies more nuanced logic — do not invent a separate model or scoring system for this.

---

### Phase 4 — Backend (FastAPI + SQLite)

**Goal:** a locally runnable API serving the exact contract below, backed by SQLite.

**Fixed API contract — do not change field names/shape without explicit instruction:**
```json
POST /predict
Request: { "patient_id": "12345" }
Response:
{
  "patient_id": "12345",
  "risk_percent": 42.3,
  "risk_category": "Moderate",
  "top_factors": [
    { "factor": "Number of prior inpatient visits", "direction": "increases risk" },
    { "factor": "Length of stay", "direction": "increases risk" },
    { "factor": "A1C test result normal", "direction": "decreases risk" }
  ],
  "follow_up_priority": "Medium"
}

GET /patients
Response: [ { "patient_id": "...", "summary": "..." }, ... ]
```

1. **SQLite schema:** a `patients` table (raw feature columns + patient_id/encounter_id), and a `predictions` table (patient_id, risk_percent, category, factors as JSON text, timestamp) to avoid recomputing SHAP on repeated lookups. Use the plain `sqlite3` module — do not add SQLAlchemy or an ORM; unnecessary overhead for this scope.
2. **`/predict` endpoint:** load patient row from DB → run through Phase 3's `explain_patient` function → store result in `predictions` table → return per the contract above.
3. **`/patients` endpoint:** list available patient IDs for the frontend's search/dropdown.
4. **CORS:** enable `fastapi.middleware.cors.CORSMiddleware` for all origins during development — the frontend is a separate static HTML/JS app that will call this API from the browser.
5. Test all endpoints via FastAPI's auto-generated `/docs` (Swagger UI) before any frontend integration work begins.

---

### Phase 5 — Frontend Linkage

**Goal:** connect the existing static HTML/CSS/JS frontend to the live backend.

1. Frontend calls `GET /patients` to populate a patient search/dropdown.
2. On selection, frontend calls `POST /predict` and renders: risk % + category badge, a SHAP bar chart from `top_factors`, and the follow-up priority.
3. Any mismatch between what the frontend expects and the actual API response shape must be resolved by updating the frontend to match the fixed contract in Phase 4 — not by changing the backend contract ad hoc, unless a human explicitly approves a contract change.
4. No additional UI features beyond the 4-step demo flow (see Section 1) unless explicitly requested.

---

### Phase 6 — Deployment

**Goal:** a live, publicly accessible URL running the full stack.

1. Push the repository to GitHub (backend + frontend together, or documented separately if split).
2. Deploy on Render: start command `uvicorn main:app --host 0.0.0.0 --port $PORT`, build command installs from `requirements.txt`.
3. Seed the deployed SQLite database with a fixed set of 5–6 demo patients (either commit a pre-seeded DB file, or run a seed script on service startup) — these should be selected to show a spread across Low/Moderate/High risk categories, not all clustered in one tier.
4. Run a full end-to-end test against the live URL (not just localhost) before considering this phase complete.

---

## 4. Definition of Done (per phase)

| Phase | Done when |
|---|---|
| Data Manipulation | Cleaned dataset saved, binary target defined, class imbalance documented, feature types split |
| Model Training | Saved pipeline artifact, LightGBM beats Logistic Regression baseline, AUC in expected 0.65–0.69 range, metrics written down |
| Explainability | `explain_patient()` function returns correct shape, sanity-checked on real patients |
| Backend | Both endpoints return contract-matching JSON, tested via `/docs` |
| Frontend Linkage | Full 4-step demo flow works locally against live backend |
| Deployment | Live URL works end-to-end for all seeded demo patients |

## 5. Rules for Any Agent Working on This Repo

- Never claim or optimize toward accuracy/AUC above the honestly expected ~0.65–0.69 range as if it were a target to hit by any means (e.g. via leakage, dropping the imbalance handling, or cherry-picked splits).
- Never present SHAP output as causal.
- Never expand scope beyond the fixed 4-step demo flow and fixed API contract without explicit human approval.
- Never substitute the fixed tech stack (Section 2) for alternatives, even if "better" in the abstract — the project timeline and team skillset assume this exact stack.
- If a phase's output metrics look suspiciously good (e.g. AUC > 0.85), stop and flag potential target leakage before proceeding — do not treat it as a win.
