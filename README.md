# DiabCare AI 🩺

### Explainable 30-Day Hospital Readmission Risk Screening for Diabetic Patients

DiabCare AI is an **AI-powered clinical decision-support prototype** that estimates whether a diabetic patient is likely to be readmitted to the hospital within **30 days of discharge**, explains the factors contributing to the prediction, and assigns a follow-up priority.

The system is designed around a simple workflow:

**Patient → Risk Prediction → Explainability → Follow-up Priority**

> **Important:** DiabCare AI is a prototype decision-support system. It is not a medical diagnosis, treatment recommendation, or clinically validated risk assessment.

---

## 🚨 Problem

Hospitals collect large amounts of patient information, including previous admissions, diagnoses, medications, laboratory procedures, and healthcare utilization.

However, identifying patients who may require closer post-discharge follow-up can be difficult when assessment depends heavily on manual clinical judgment.

DiabCare AI aims to provide a simple and explainable way to:

* Identify patients at higher risk of 30-day readmission
* Provide an individual risk estimate
* Explain which patient features contributed most to the prediction
* Prioritize patients for follow-up based on their predicted risk

The goal is **risk stratification and explainability**, rather than attempting to make autonomous medical decisions.

---

## 💡 How It Works

The application follows a four-step workflow:

### 1. Select a Patient

A patient record is selected using the patient ID.

### 2. Predict Readmission Risk

The trained machine-learning model generates a probability of readmission within 30 days.

The prototype groups predictions into:

| Risk Category | Prototype Threshold |
| ------------- | ------------------: |
| 🟢 Low        |               < 30% |
| 🟡 Moderate   |              30–60% |
| 🔴 High       |               > 60% |

These thresholds are **prototype cutoffs and have not been clinically validated**.

### 3. Explain the Prediction

SHAP-based explainability identifies the most influential features for the individual prediction.

The application converts model features into human-readable explanations such as:

* Previous inpatient visits → increases risk
* Number of diagnoses → increases risk
* A1C test result normal → decreases risk

SHAP values represent feature contribution to the model's prediction. They **do not establish causation**.

### 4. Assign Follow-up Priority

Follow-up priority is derived directly from the risk category:

* **High Risk → High Priority**
* **Moderate Risk → Medium Priority**
* **Low Risk → Low Priority**

No separate clinical scoring model is used for this prioritization.

---

## 🧠 Machine Learning Pipeline

```text
Raw Patient Data
       │
       ▼
Data Cleaning
       │
       ▼
Feature Preprocessing
       │
       ▼
Logistic Regression
(Baseline)
       │
       ▼
LightGBM
(Primary Model)
       │
       ▼
Risk Probability
       │
       ▼
SHAP Explainability
       │
       ▼
Risk Category
       │
       ▼
Follow-up Priority
```

The preprocessing and model are combined into a single `scikit-learn Pipeline`, allowing the same preprocessing logic to be used during both training and inference.

### Preprocessing

* Missing values represented by `?` are converted to `NaN`
* Numeric features are processed using `StandardScaler`
* Categorical features are processed using `OneHotEncoder`
* `handle_unknown='ignore'` is used for inference-time robustness
* Identifier fields are excluded from model input
* Hospital admission/discharge/source IDs are treated as categorical codes rather than continuous numerical variables

### Models

**Baseline:** Logistic Regression

**Primary:** LightGBM (`LGBMClassifier`)

The LightGBM model uses class balancing to account for the dataset's approximately **11% positive class**.

A small amount of manual hyperparameter tuning is performed using stratified cross-validation.

---

## 🔍 Explainability with SHAP

DiabCare AI uses **SHAP TreeExplainer** with the trained LightGBM model.

For an individual patient, the system:

1. Transforms the patient's raw features using the fitted preprocessing pipeline
2. Generates SHAP values
3. Maps encoded features back to human-readable names
4. Sorts features by absolute contribution
5. Displays the top three contributing factors
6. Indicates whether each factor increases or decreases the model's predicted risk

Example:

```text
30-Day Readmission Risk: 78%

Why this score?

↑ Previous inpatient visits
  Increases risk

↑ Number of diagnoses
  Increases risk

↓ A1C test result normal
  Decreases risk
```

> SHAP explanations describe model behavior and feature contribution. They should not be interpreted as evidence that a particular factor causes readmission.

---

## 📊 Dataset

DiabCare AI uses the **UCI Diabetes 130-US Hospitals for Years 1999–2008** dataset.

### Dataset characteristics

* **101,766** hospital encounters
* **130** U.S. hospitals
* **47** features
* Approximately **10 years** of clinical data
* Includes a pre-labeled readmission outcome

The target is converted into a binary classification problem:

```text
1 → Readmitted within 30 days
0 → Not readmitted within 30 days
```

The `NO` and `>30` categories are therefore grouped into the negative class.

Key feature groups include:

* Demographics
* Hospital utilization history
* Length of hospital stay
* Laboratory procedures
* Medication information
* Diagnosis information
* Admission context
* Previous inpatient, emergency, and outpatient visits

The dataset is historical and U.S.-based. The current prototype does **not** represent live hospital deployment or validated performance across other healthcare systems.

---

## 📈 Model Evaluation

Because the dataset is highly imbalanced, **accuracy is not used as the primary evaluation metric**.

The main evaluation metrics are:

* ROC-AUC
* F1 Score
* Recall
* Precision
* High-risk recall

The expected realistic performance range for this dataset is approximately:

**ROC-AUC: 0.65–0.69**

This project intentionally does not optimize for artificially high performance through leakage, cherry-picked splits, or inappropriate evaluation.

The purpose of the model is to provide useful **risk stratification and explainability**, not perfect prediction.

---

## 🖥️ Application

The frontend is designed as a lightweight clinical dashboard.

### Patient Search

Users can:

* Search/select a patient
* View available patient records
* Start a risk assessment

### Risk Assessment

The risk screen displays:

* Patient identifier
* 30-day readmission risk percentage
* Risk category
* Top three contributing factors
* Direction of each factor's contribution
* Follow-up priority
* Prototype / clinical-use disclaimer

The interface is intentionally clean and clinical, with green, yellow/orange, and red indicators representing the three prototype risk categories.

---

## 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │   UCI Diabetes Data  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Data Processing    │
                    │ Pandas + NumPy       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Preprocessing        │
                    │ ColumnTransformer    │
                    │ Scaler + OneHot      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     LightGBM         │
                    │   Risk Prediction    │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    ▼                      ▼
          ┌─────────────────┐    ┌─────────────────┐
          │   SHAP          │    │    Risk %       │
          │ Explainability  │    │ Risk Category   │
          └────────┬────────┘    └────────┬────────┘
                   │                      │
                   └──────────┬───────────┘
                              ▼
                    ┌──────────────────────┐
                    │      FastAPI         │
                    │       Backend        │
                    └──────────┬───────────┘
                               │
                       ┌───────┴────────┐
                       ▼                ▼
                ┌─────────────┐  ┌─────────────┐
                │   SQLite    │  │  Frontend   │
                │  Database   │  │ HTML/CSS/JS │
                └─────────────┘  └─────────────┘
```

---

## ⚙️ Tech Stack

| Layer             | Technology            |
| ----------------- | --------------------- |
| Data Processing   | Python, Pandas, NumPy |
| Machine Learning  | scikit-learn          |
| Primary Model     | LightGBM              |
| Baseline Model    | Logistic Regression   |
| Explainability    | SHAP                  |
| Model Persistence | Joblib                |
| Backend           | FastAPI               |
| Database          | SQLite                |
| Frontend          | HTML, CSS, JavaScript |
| Deployment        | Render / Netlify      |

---

## 🔌 API

The backend exposes a simple API for connecting the frontend to the prediction system.

### `POST /predict`

Predicts readmission risk for a patient.

**Request**

```json
{
  "patient_id": "12345"
}
```

**Response**

```json
{
  "patient_id": "12345",
  "risk_percent": 42.3,
  "risk_category": "Moderate",
  "top_factors": [
    {
      "factor": "Number of prior inpatient visits",
      "direction": "increases risk"
    },
    {
      "factor": "Length of stay",
      "direction": "increases risk"
    },
    {
      "factor": "A1C test result normal",
      "direction": "decreases risk"
    }
  ],
  "follow_up_priority": "Medium"
}
```

### `GET /patients`

Returns available patients with a short summary for the frontend.

### `GET /stats`

Optional statistics endpoint for aggregating screened patients and risk categories.

---

## 🗄️ Database

SQLite is used as the lightweight persistence layer.

### `patients`

Stores patient records and relevant input features.

### `predictions`

Stores generated predictions including:

* Patient ID
* Risk percentage
* Risk category
* SHAP factors
* Follow-up priority
* Prediction timestamp

The system stores prediction results so repeated lookups do not require unnecessary SHAP recomputation.

---

## 📁 Project Structure

```text
DiabCare/
│
├── Src/
│   ├── ...
│
├── NoteBooks/
│   ├── ...
│
├── data/
│   └── ...
│
├── models/
│   └── ...
│
├── main.py
├── requirements.txt
├── README.md
└── ...
```

> The exact structure may evolve as development continues. The repository contains the implementation of the data pipeline, model, explainability layer, backend, database, and frontend.

---

## 🚀 Running the Project

### 1. Clone the repository

```bash
git clone <repository-url>
cd DiabCare
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the FastAPI backend

```bash
uvicorn main:app --reload
```

The API documentation can then be accessed through FastAPI's automatically generated Swagger interface at:

```text
/docs
```

### 5. Start the frontend

Open the frontend application according to the repository's frontend structure and ensure its API requests point to the running FastAPI backend.

---

## ⚠️ Limitations & Responsible Use

DiabCare AI has several important limitations.

### Historical Data

The model is trained using historical U.S. hospital encounter data. It has not been validated on live hospital data or across different healthcare systems.

### Model Performance

Readmission is influenced by factors that are not fully captured in the dataset, including social support, medication adherence, and outpatient access.

A realistic AUC for this dataset is approximately **0.65–0.69**.

### Prototype Thresholds

The 30% and 60% risk boundaries are prototype thresholds. They are **not clinically validated cutoffs**.

### Explainability

SHAP identifies features contributing to the model's prediction. These contributions should not be interpreted as causal relationships.

### Decision Support Only

DiabCare AI does not make autonomous medical decisions, prescribe treatment, or provide medical diagnoses.

---

## 🔮 Future Scope

Potential future extensions include:

* Multi-hospital deployment
* Integration with healthcare information systems
* ABDM integration
* Broader validation using geographically diverse datasets
* Model calibration and prospective evaluation
* Integration with real-world clinical workflows
* Additional monitoring and analytics capabilities

These are future possibilities and are **not part of the current prototype**.

---

## 🎯 Project Goal

DiabCare AI is built around a simple idea:

> **Don't just predict risk. Explain it, and help prioritize attention.**

The project focuses on combining machine-learning-based risk prediction with understandable explanations and a practical follow-up priority system, while being transparent about model limitations and clinical validity.

---

### ⚕️ Disclaimer

**DiabCare AI is a prototype clinical decision-support system developed for educational and hackathon purposes. It is not a medical device and must not be used to diagnose, treat, or make autonomous clinical decisions. Predictions are based on historical U.S. hospital data and have not been clinically validated.**
