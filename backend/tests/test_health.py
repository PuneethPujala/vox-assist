from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    # Depending on router mounting, it might be /health or /api/v1/health. Assuming it's mounted in routes/api.py
    # Oh wait, /health is in api.py which is prefixed with /api/v1
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
