import pytest

def test_patient_login_success(client):
    response = client.post("/auth/login", json={
        "email": "patient1@diabcare.ai",
        "password": "patient123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "patient1@diabcare.ai"
    assert data["user"]["role"] == "patient"
    assert data["user"]["reference_id"] == "2552952"

def test_patient_dashboard_endpoint(client):
    # 1. Log in to get token
    login_resp = client.post("/auth/login", json={
        "email": "patient1@diabcare.ai",
        "password": "patient123"
    })
    token = login_resp.json()["access_token"]
    
    # 2. Call patient dashboard API
    response = client.get("/api/patient/dashboard", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "2552952"
    assert data["name"] == "David Miller"
    assert "appointment" in data
    assert "assigned_doctor" in data
    assert "Dr. Alice Smith" in data["assigned_doctor"]["name"]

def test_patient_access_restrictions(client):
    # 1. Log in to get token
    login_resp = client.post("/auth/login", json={
        "email": "patient1@diabcare.ai",
        "password": "patient123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Patients list should return 403
    resp_patients = client.get("/patients", headers=headers)
    assert resp_patients.status_code == 403
    
    # 3. Predict endpoint should return 403
    resp_predict = client.post("/predict", json={"patient_id": "2552952"}, headers=headers)
    assert resp_predict.status_code == 403

    # 4. Predict new endpoint should return 403
    resp_predict_new = client.post("/predict_new", json={
        "name": "Sarah Connor",
        "race": "Caucasian",
        "gender": "Female",
        "age": "[70-80)",
        "admission_type_id": 1,
        "discharge_disposition_id": 1,
        "admission_source_id": 1,
        "time_in_hospital": 3,
        "num_lab_procedures": 40,
        "num_procedures": 0,
        "num_medications": 15,
        "number_outpatient": 0,
        "number_emergency": 0,
        "number_inpatient": 0,
        "diag_1": "250",
        "diag_2": "428",
        "diag_3": "276",
        "number_diagnoses": 9
    }, headers=headers)
    assert resp_predict_new.status_code == 403
    
    # 5. Timeline history for other patient should return 403
    resp_timeline = client.get("/patients/149190/timeline", headers=headers)
    assert resp_timeline.status_code == 403

    # 6. Report PDF for other patient should return 403
    resp_pdf = client.get("/patients/149190/report/pdf", headers=headers)
    assert resp_pdf.status_code == 403
