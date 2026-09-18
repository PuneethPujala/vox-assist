import sys
from pathlib import Path

# Ensure paths so tests run cleanly whether invoked from Project root or backend/
_backend_dir = Path(__file__).resolve().parent.parent
_project_dir = _backend_dir.parent
for p in (str(_project_dir), str(_backend_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient

try:
    from backend.main import app
except ImportError:
    from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to VOX-ASSIST API"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "vox-assist-backend"}

def test_api_v1_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
