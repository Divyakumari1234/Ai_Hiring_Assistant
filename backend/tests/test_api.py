from fastapi.testclient import TestClient

from app.main import app


def test_health_and_search():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        response = client.post(
            "/api/search",
            json={
                "job_description": "Senior product designer with Figma and user research experience",
                "location": "India",
                "provider": "demo",
            },
        )
        assert response.status_code == 200
        assert response.json()["results"]
        assert response.json()["source"] == "demo"


def test_outreach_validation():
    with TestClient(app) as client:
        response = client.post("/api/outreach", json={"candidate_ids": ["missing"]})
        assert response.status_code == 404


def test_demo_outreach_and_call_dashboard():
    with TestClient(app) as client:
        response = client.post(
            "/api/outreach", json={"candidate_ids": ["c1"], "channel": "voice"}
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "demo"
        call_id = response.json()["calls"][0]["id"]
        detail = client.get(f"/api/calls/{call_id}")
        assert detail.status_code == 200
        assert detail.json()["candidate_name"] == "Aarav Mehta"


def test_hunar_webhook_updates_structured_result():
    with TestClient(app) as client:
        created = client.post("/api/outreach", json={"candidate_ids": ["c2"]}).json()[
            "calls"
        ][0]
        result = {"interest": "High", "notice_period": "30 days"}
        response = client.post(
            "/api/webhooks/hunar",
            json={
                "call_id": created["id"],
                "status": "COMPLETED",
                "duration_seconds": 120,
                "result": result,
            },
        )
        assert response.status_code == 200
        detail = client.get(f"/api/calls/{created['id']}").json()
        assert detail["status"] == "COMPLETED"
        assert detail["result"] == result
