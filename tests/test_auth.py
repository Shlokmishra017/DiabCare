import pytest

def test_config_endpoint(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "show_demo_accounts" in data

def test_login_success(client):
    response = client.post("/auth/login", json={
        "email": "doctor1@diabcare.ai",
        "password": "doctor123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "doctor1@diabcare.ai"

def test_login_invalid_password(client):
    response = client.post("/auth/login", json={
        "email": "doctor1@diabcare.ai",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_register_weak_password(client):
    response = client.post("/auth/register", json={
        "name": "Dr. Test",
        "email": "testdoc@diabcare.ai",
        "password": "simple"
    })
    assert response.status_code == 400
    assert "Password must be at least 8 characters" in response.json()["detail"]

def test_register_valid_password(client):
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:6]}@diabcare.ai"
    response = client.post("/auth/register", json={
        "name": "Dr. Test Valid",
        "email": unique_email,
        "password": "StrongPassword123"
    })
    assert response.status_code == 200
    assert "submitted" in response.json()["message"]
