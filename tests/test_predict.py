import pytest

def test_predict_patient_flow(client):
    # First login to get token
    login_res = client.post("/auth/login", json={
        "email": "doctor1@diabcare.ai",
        "password": "doctor123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch patients list
    patients_res = client.get("/patients", headers=headers)
    assert patients_res.status_code == 200
    patients = patients_res.json()
    assert len(patients) > 0

    patient_id = patients[0]["patient_id"]

    # Predict risk for patient
    pred_res = client.post("/predict", json={"patient_id": patient_id}, headers=headers)
    assert pred_res.status_code == 200
    data = pred_res.json()
    assert data["patient_id"] == patient_id
    assert "risk_percent" in data
    assert "risk_category" in data
    assert len(data["top_factors"]) > 0
