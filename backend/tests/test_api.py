from fastapi.testclient import TestClient
from app.main import app


def test_health_and_search():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        response = client.post("/api/search", json={"job_description":"Senior product designer with Figma and user research experience", "location":"India"})
        assert response.status_code == 200
        assert response.json()["results"]


def test_outreach_validation():
    with TestClient(app) as client:
        response = client.post("/api/outreach", json={"candidate_ids":["missing"]})
        assert response.status_code == 404

