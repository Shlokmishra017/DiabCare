<div align="center">

# 🩺 DiabCare AI
### *Next-Gen Clinical Decision-Support & 30-Day Readmission Intelligence Engine*

[![SIH 2026](https://img.shields.io/badge/Smart_India_Hackathon-2026-orange?style=for-the-badge&logo=target)](https://sih.gov.in)
[![MedTech](https://img.shields.io/badge/Theme-MedTech-red?style=for-the-badge&logo=medicalcross)](https://sih.gov.in)
[![Team Invicta](https://img.shields.io/badge/Team-Invicta-blueviolet?style=for-the-badge)](https://github.com)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![LightGBM](https://img.shields.io/badge/ML-LightGBM-339933?style=for-the-badge)](https://lightgbm.readthedocs.io/)
[![XAI SHAP](https://img.shields.io/badge/XAI-SHAP_Engine-FF6F00?style=for-the-badge)](https://shap.readthedocs.io/)

---

### 🚨 *Bridging the gap between raw healthcare big data and life-saving clinical action.* 🚨

</div>

---

## 💥 The Crisis & The Breakthrough

Diabetic readmissions cost millions and overburden healthcare infrastructure worldwide. While modern hospitals sit on mountains of EHR data (diagnoses, lab profiles, clinical visits), clinicians lack **real-time, trustworthy, and actionable intelligence** to flag high-risk patients before they walk out the door.

**DiabCare AI** isn't just another machine learning model wrapped in a script — it's an end-to-end, enterprise-grade decision-support ecosystem built specifically for clinicians.

### 🔥 Why DiabCare AI Dominates
* **👁️ Transparent & Trustworthy (XAI First):** Zero black-box predictions. Powered by **SHAP (`TreeExplainer`)**, every output provides the top 3 plain-language clinical factors driving the risk.
* **⚡ Instant Triaging Workflow:** Transforms raw statistical probabilities into high-priority actionable tiers (**HIGH / MEDIUM / LOW RISK**) instantly.
* **🎯 Uncompromising Realism:** No fake 99% accuracy hackathon claims. Built on realistic, peer-reviewed clinical benchmarks (**AUC ~0.65–0.69**) using 100k+ real patient records.
* **🔒 Enterprise-Grade Security & Roles:** Complete RBAC system with separate workflow dashboards for **Admins, Doctors, and Patients**.

---

## 🛠️ High-Performance Tech Stack

<div align="center">

| Layer | Powerhouse Stack |
| :--- | :--- |
| **Core AI Engine** | `LightGBM` (Primary Inference), `Logistic Regression` (Baseline) |
| **Model Interpretability** | `SHAP` (SHapley Additive exPlanations - `TreeExplainer`) |
| **Pipeline & Processing** | `scikit-learn` (`ColumnTransformer`, `Pipeline`), `Pandas`, `NumPy` |
| **Backend Orchestrator** | `FastAPI` (Python) |
| **Frontend UI** | HTML5, CSS3, Modern Dynamic JavaScript (Static / Zero-Bloat) |
| **Data Persistence** | `SQLite` / `MySQL` |
| **Production Deployment** | Cloud Services / Render Infrastructure |

</div>

---

## 🏗️ System Architecture & Workflow Pipeline

```
                              ┌──────────────────────────────────┐
                              │     Clinical User Access Gateway │
                              └────────────────┬─────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
             [ Direct User Login ]                          [ Access Request System ]
                       │                                               │
                       ▼                                               ▼
        ┌─────────────────────────────┐             ┌──────────────────────────────────┐
        │  Role-Based Routing Engine  │             │   Admin Access Control Panel     │
        └──────────────┬──────────────┘             │   (Review / Approve / Reject)    │
                       │                            └──────────────────┬───────────────┘
                       │                                               │
                       ├───────────────────────────────────────────────┘
                       ▼
        ┌─────────────────────────────┐
        │   Doctor Workspace Queue    │ ◄── [ Auto-Sorted by High Readmission Risk ]
        └──────────────┬──────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │   Selected Patient Profile  │
        └──────────────┬──────────────┘
                       │
                       ▼
     =======================================================
     ⚡ POST /predict (FastAPI ML + XAI Engine Pipeline)
     ├── LightGBM Model: Generates Risk Probability Score
     └── SHAP Explainer: Extracts Top 3 Risk Drivers
     =======================================================
                       │
                       ▼
        ┌─────────────────────────────┐
        │  Interactive Clinical Cards │ ──► (Risk %, Key Factors, Direct Action Protocol)
        └─────────────────────────────┘
```

---

## ⚡ Next-Level Features

* 📊 **Smart Priority Queue:** Automatically reorganizes incoming patient rosters based on predicted 30-day readmission threat levels.
* 🧬 **Real-Time SHAP Clinical Risk Cards:** Displays interactive UI cards pinpointing exactly *why* a patient is flagged (e.g., prior emergency visits, HbA1c spike, medication history).
* 🛡️ **Role-Based Security Gatekeeper:** Restricts access through admin-controlled request approvals to ensure complete HIPAA/EHR compliance readiness.
* 📝 **Active Clinical Trackers:** Allows medical teams to update follow-up statuses, log interventions, and track post-discharge care trajectories directly in the system.

---

## 📊 Dataset & Medical Literature Alignment

Engineered and rigorously evaluated against the landmark **UCI Diabetes 130-US Hospitals Dataset** (101,766 encounters spanning 10 years).

```
[ Baseline Model: Logistic Regression ] ──► AUC ~0.64
[ Primary Engine: LightGBM / XGBoost  ] ──► AUC ~0.65 - 0.69 (Matches Peak Literature)
```

* **Validated Against Clinical Literature:** Benchmarked direct alignment with top peer-reviewed PubMed readmission studies ([PubMed ID: 42121627](https://pubmed.ncbi.nlm.nih.gov/42121627/) & [PubMed ID: 40543277](https://pubmed.ncbi.nlm.nih.gov/40543277/)).

---

## 🚀 Quickstart Protocol (Local Deployment)

### System Requirements
* Python 3.9+
* Git Engine

```bash
# 1. Clone the repository
git clone https://github.com/your-team/diabcare-ai.git
cd diabcare-ai

# 2. Spin up an isolated virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Fire up all dependencies
pip install -r requirements.txt

# 4. Launch the high-performance FastAPI server
uvicorn main:app --reload
```

> 🌐 **Access Point:** Navigate to `http://127.0.0.1:8000` to launch the clinical portal.

---

## 💎 Maximum Healthcare Impact

```
┌─────────────────┬──────────────────────────────────────────────────────────────────┐
│   Stakeholder   │                        Transformative Benefit                    │
├─────────────────┼──────────────────────────────────────────────────────────────────┤
│ 👨‍⚕️ Clinicians   │ Rapid triaging, immediate insight into critical risk drivers.    │
│ 🩺 Patients     │ Targeted post-discharge care, preventing relapse & readmission.  │
│ 🏥 Hospitals    │ Optimized bed usage, drastically reduced readmission penalties.  │
└─────────────────┴──────────────────────────────────────────────────────────────────┘
```

---

<div align="center">

### 🏆 Team Invicta — SIH 2026
*Engineered with precision for Smart India Hackathon 2026.*

</div>
