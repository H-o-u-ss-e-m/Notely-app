from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


def _headers():
    return {"Authorization": f"Bearer {create_access_token({'sub': 'test-user'})}"}

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("online", "degraded")  # degraded : pas de PostgreSQL de test
    assert "device" in data
    assert "model" in data

def test_empty_recognition():
    payload = {
        "strokes": [],
        "options": {"debug": True},
        "canvasWidth": 1200,
        "canvasHeight": 800
    }
    response = client.post("/api/v1/recognition", json=payload, headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["lineCount"] == 0
    assert data["fullText"] == ""
