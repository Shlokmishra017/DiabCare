import pytest
import os
import tempfile
import sqlite3
from fastapi.testclient import TestClient
from main import app, DB_PATH
from Src.database import init_db

@pytest.fixture(scope="session")
def client():
    app.state.limiter.enabled = False
    with TestClient(app) as c:
        yield c
