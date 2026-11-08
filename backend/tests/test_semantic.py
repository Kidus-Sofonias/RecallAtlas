from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hybrid_endpoint():
    r = client.get('/api/v1/search/hybrid', params={'q':'force'})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
