# DiabCare AI — Remediation & Feature Implementation Playbook

This document serves as a detailed step-by-step guide for an AI agent or developer to remediate the identified codebase issues (excluding the gitignore issue) and implement the proposed new features.

---

## 🛠️ Section 1: Security & Critical Issues Remediation

### 1. Secure Seed Passwords & Demolish Demo Credentials Panel
* **Goal**: Stop hardcoding passwords in source code and conditionally hide/disable demo accounts in production.
* **Steps**:
  1. Open [`database.py`](file:///D:/DiabCare/Src/database.py). Locate `_seed_users()`.
  2. Modify the user seeding logic to read hashed passwords from environment variables (e.g., `SEED_DOC_1_HASH`, `SEED_DOC_2_HASH`, `SEED_ADMIN_HASH`) or fall back to securely generated hashes if not provided. DO NOT store plaintext passwords like `"doctor123"` in code.
  3. Open [`index.html`](file:///D:/DiabCare/static/index.html). Wrap the `<div class="login-demo-accounts">` in a conditional block or dynamically remove it from DOM using JavaScript if `window.location.hostname !== 'localhost'` or if an environment variable `SHOW_DEMO_ACCOUNTS=false` is detected via an endpoint.
  4. Create a config check endpoint `/api/config` that returns whether demo mode is active.

---

### 2. Tighten CORS Configuration
* **Goal**: Restrict `allow_origins` based on the running environment.
* **Steps**:
  1. Open [`main.py`](file:///D:/DiabCare/main.py). Locate `app.add_middleware(CORSMiddleware, ...)`.
  2. Replace `allow_origins=["*"]` with an environment variable lookup:
     ```python
     allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
     ```
  3. Ensure `allow_credentials=True` is only paired with specific trusted origins.

---

### 3. Make JWT Secret Mandatory in Production
* **Goal**: Avoid session invalidation on server restarts by forcing a persistent `JWT_SECRET` key in production.
* **Steps**:
  1. Open [`main.py`](file:///D:/DiabCare/main.py).
  2. Modify the secret logic:
     ```python
     JWT_SECRET = os.getenv("JWT_SECRET")
     ENV = os.getenv("APP_ENV", "development")
     if not JWT_SECRET:
         if ENV == "production":
             raise RuntimeError("JWT_SECRET environment variable is MANDATORY in production mode!")
         import secrets
         JWT_SECRET = secrets.token_hex(32)
     ```

---

### 4. Delete Empty Code Artifacts
* **Goal**: Remove dead files from the repository.
* **Steps**:
  1. Delete the 0-byte file [`Predict.py`](file:///D:/DiabCare/Src/Predict.py).
  2. Verify no active files import anything from `Src.Predict` (none do, but check anyway).

---

### 5. Enforce Password Strength Validation
* **Goal**: Require new doctors to register with secure passwords.
* **Steps**:
  1. Open [`main.py`](file:///D:/DiabCare/main.py). Go to `register()`.
  2. Implement a validation helper:
     ```python
     import re
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
     ```
  3. Raise an `HTTPException(status_code=400, detail="...")` if validation fails.

---

### 6. Introduce Rate Limiting
* **Goal**: Protect auth endpoints from brute-force attacks.
* **Steps**:
  1. Add `slowapi` to `requirements.txt`.
  2. Import and initialize the Limiter in `main.py`:
     ```python
     from slowapi import Limiter, _rate_limit_exceeded_handler
     from slowapi.util import get_remote_address
     from slowapi.errors import RateLimitExceeded

     limiter = Limiter(key_func=get_remote_address)
     app.state.limiter = limiter
     app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
     ```
  3. Annotate `/auth/login` and `/auth/register` with `@limiter.limit("5/minute")`.

---

### 7. Email and Pydantic Model Validation
* **Goal**: Ensure inputs are syntactically valid before they reach database operations.
* **Steps**:
  1. Add `pydantic[email]` to `requirements.txt`.
  2. Change type definitions in `main.py` models (e.g., `RegisterRequest` and `LoginRequest`):
     ```python
     from pydantic import EmailStr
     
     class RegisterRequest(BaseModel):
         name: str
         email: EmailStr
         password: str
     ```

---

### 8. Implement Token Refresh Flow
* **Goal**: Prevent forced logouts every 60 minutes.
* **Steps**:
  1. Create a `refresh_tokens` table in SQLite:
     ```sql
     CREATE TABLE IF NOT EXISTS refresh_tokens (
         token_id TEXT PRIMARY KEY,
         user_id TEXT,
         token TEXT UNIQUE,
         expires_at TEXT,
         FOREIGN KEY(user_id) REFERENCES users(user_id)
     );
     ```
  2. Add `/auth/refresh` endpoint in `main.py`. This endpoint should verify a submitted refresh token, delete it (to prevent reuse), generate a new access token, and return a new refresh token.

---

## 🟡 Section 2: Code Quality Improvements

### 9. Migrate to FastAPI Lifespan Events
* **Goal**: Replace the deprecated `@app.on_event("startup")` decorator.
* **Steps**:
  1. Open [`main.py`](file:///D:/DiabCare/main.py).
  2. Declare the lifespan context manager:
     ```python
     from contextlib import asynccontextmanager

     @asynccontextmanager
     async def lifespan(app: FastAPI):
         global _pipeline
         init_db(DB_PATH)
         _pipeline = joblib.load(MODEL_PATH)
         # Run startup checks, seed/cache logic
         yield
         # Shutdown cleanup actions (e.g., close DB connection pool)
         
     app = FastAPI(lifespan=lifespan, ...)
     ```

---

### 10. Refactor Global Mutable State
* **Goal**: Eliminate global pipeline references.
* **Steps**:
  1. Store the loaded pipeline in `app.state.pipeline` during lifespan initialization.
  2. Define a dependency function to retrieve the pipeline:
     ```python
     def get_pipeline(request: Request):
         return request.app.state.pipeline
     ```
  3. Use this dependency in all endpoint route handlers that require the ML model:
     ```python
     @app.post("/predict")
     def predict(request: PredictRequest, pipeline = Depends(get_pipeline)):
         # use pipeline instead of global _pipeline
     ```

---

### 11. Implement Database Connection Pooling
* **Goal**: Improve database access times and eliminate connection management overhead.
* **Steps**:
  1. Integrate a simple connection pool or helper inside `database.py`.
  2. Implement an dependency helper in `main.py` to yield a database session context manager:
     ```python
     def get_db():
         conn = sqlite3.connect(DB_PATH)
         conn.row_factory = sqlite3.Row
         try:
             yield conn
         finally:
             conn.close()
     ```
  3. Pass `conn` instead of `DB_PATH` to database service helper operations.

---

### 12. Eliminate Code Duplications (`_INT_COLS`)
* **Goal**: Establish a single source of truth for schema variables.
* **Steps**:
  1. Open [`Preprocessing.py`](file:///D:/DiabCare/Src/Preprocessing.py).
  2. Export a global list:
     ```python
     INT_COLS = [
         "admission_type_id", "discharge_disposition_id", "admission_source_id",
         "time_in_hospital", "num_lab_procedures", "num_procedures",
         "num_medications", "number_outpatient", "number_emergency",
         "number_inpatient", "number_diagnoses",
     ]
     ```
  3. Import `INT_COLS` into `database.py` and `main.py` and delete duplicate local definitions.

---

### 13. Replace Standard Print Statements with Structured Logging
* **Goal**: Standardize log files and audit logs.
* **Steps**:
  1. Configure logging inside `main.py` startup:
     ```python
     import logging
     logging.basicConfig(
         level=logging.INFO,
         format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
     )
     logger = logging.getLogger("diabcare")
     ```
  2. Replace all instances of `print(...)` with `logger.info(...)`, `logger.warning(...)`, or `logger.error(...)`.

---

## 🔵 Section 3: Architecture & Design Gaps

### 14. Establish Test Suite
* **Goal**: Add robust test coverage.
* **Steps**:
  1. Create a `tests/` directory at the project root.
  2. Add `pytest`, `httpx`, and `pytest-cov` to `requirements.txt`.
  3. Write `tests/conftest.py` containing fixtures for a mock SQLite database and a test client:
     ```python
     import pytest
     from fastapi.testclient import TestClient
     from main import app
     
     @pytest.fixture
     def client():
         # Override settings/paths to point to test database
         with TestClient(app) as c:
             yield c
     ```
  4. Implement `tests/test_auth.py` (registration and login flows) and `tests/test_predict.py` (verification of prediction logic, mock model outputs, caching).

---

### 15. Containerize the Application (Docker)
* **Goal**: Standardize application environment setup.
* **Steps**:
  1. Create a [`Dockerfile`](file:///D:/DiabCare/Dockerfile) in the project root:
     ```dockerfile
     FROM python:3.12-slim
     WORKDIR /app
     COPY requirements.txt .
     RUN pip install --no-cache-dir -r requirements.txt
     COPY . .
     EXPOSE 8000
     CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
     ```
  2. Create a [`docker-compose.yml`](file:///D:/DiabCare/docker-compose.yml) to spin up the app and bind volumes for SQLite database tracking.

---

### 16. Modularize Monolithic Frontend Javascript (`app.js`)
* **Goal**: Enhance frontend structure and maintainability.
* **Steps**:
  1. Create a subdirectory `/static/js/`.
  2. Split `app.js` into separate ES Modules:
     - `auth.js`: Handles token session management, logins, registrations.
     - `dashboard.js`: Manages list rendering, sorting, dashboard indicators.
     - `screening.js`: Manages prediction evaluations, form bindings.
     - `api.js`: Handles standard fetch wrapper configurations with Bearer headers.
  3. In `index.html`, load the controller script as a module:
     ```html
     <script type="module" src="/static/js/main.js"></script>
     ```

---

## 🟢 Section 4: Feature Implementation Strategies

### 17. Audit Trail / Activity Logging Database Implementation
* **Goal**: Track sensitive user interactions.
* **Steps**:
  1. Add table schema in [`database.py`](file:///D:/DiabCare/Src/database.py):
     ```sql
     CREATE TABLE IF NOT EXISTS audit_logs (
         log_id TEXT PRIMARY KEY,
         user_id TEXT,
         action TEXT,
         target TEXT,
         timestamp TEXT,
         ip_address TEXT
     );
     ```
  2. Write a decorator helper to wrap critical routes in `main.py` and record access activities in the background.

---

### 18. Patient Readmission Evaluation Timeline
* **Goal**: Show history and trajectories of risk assessment for a patient.
* **Steps**:
  1. Update `predictions` schema to allow multiple historical records per patient instead of replacing the entry (remove `PRIMARY KEY` on `patient_id` or implement a secondary composite mapping using `prediction_id` as the primary key).
  2. Implement an endpoint `GET /patients/{patient_id}/timeline` returning all risk records sorted by `created_at` DESC.
  3. Render a vertical timeline component in the frontend patient detail view.

---

### 19. Bulk CSV Upload Predictions
* **Goal**: Enable processing of batches of patient files.
* **Steps**:
  1. Create endpoint `POST /predict/bulk` accepting `UploadFile` from FastAPI:
     ```python
     @app.post("/predict/bulk")
     async def predict_bulk(file: UploadFile, current_user = Depends(get_current_user)):
         # read CSV, parse features, execute pipeline
     ```
  2. Parse the CSV file using Pandas, align the columns with the model's preprocessing schema, calculate risks, and return an array of JSON prediction payloads.

---

### 20. PDF Export Framework
* **Goal**: Generate high-fidelity patient clinical reports.
* **Steps**:
  1. Add `reportlab` or similar rendering engine to `requirements.txt`.
  2. Implement a route `/patients/{patient_id}/report/pdf` generating a structured PDF containing:
     - Patient demographic summary.
     - Readmission Risk Category (color-coded).
     - SHAP factors translated to narrative summaries.
     - Actionable clinical steps and follow-up status scheduling information.

---

### 21. Model Drift and Health Check Improvements
* **Goal**: Monitor model behavior over time.
* **Steps**:
  1. Enhance `/health` endpoint to pull statistics on classification distributions from the cache:
     ```python
     @app.get("/health")
     def health():
         # Calculate ratio of High / Moderate / Low predictions in database
         # Return ok status only if DB connection is active and pipeline is loaded
     ```

---

### 22. Dark Mode CSS Toggle
* **Goal**: Improve user experience in low-light clinical environments.
* **Steps**:
  1. Add CSS variables for colors in [`style.css`](file:///D:/DiabCare/static/style.css) (define light-theme defaults and a `.dark-theme` class overrides).
  2. Add a simple toggle button in the sidebar header in `index.html`.
  3. Listen to click events in Javascript, toggle the `.dark-theme` class on the `<body>` element, and write user configuration preference to `localStorage`.
