import httpx
import pytest
from fastapi.testclient import TestClient
from app import main, sourcing


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(sourcing, "DATABASE", tmp_path / "candidates.db")
    monkeypatch.setattr(main.settings, "pdl_api_key", "test-key")
    with TestClient(main.app) as client:
        yield client


INPUT = {"job_description": "We need a software engineer with Python and SQL skills", "location": "India", "limit": 5}


def test_criteria_extracts_known_role_and_skills_without_a_provider_call(client):
    result = client.post("/api/search/criteria", json=INPUT)
    assert result.status_code == 200
    assert result.json() == {"job_title": "software engineer", "location": "india", "skills": ["python", "sql"]}


def test_search_requires_separate_key(client, monkeypatch):
    monkeypatch.setattr(main.settings, "pdl_api_key", "")
    response = client.post("/api/search", json=INPUT)
    assert response.status_code == 503
    assert "PDL_API_KEY" in response.json()["detail"]


def test_search_uses_pdl_and_stores_only_returned_profiles(client, monkeypatch):
    async def post(_self, url, **kwargs):
        assert url == "https://api.peopledatalabs.com/v5/person/search"
        assert kwargs["headers"]["X-Api-Key"] == "test-key"
        assert kwargs["json"]["size"] == 5
        must = kwargs["json"]["query"]["query"]["bool"]["must"]
        assert {"term": {"skills": "python"}} in must
        return httpx.Response(200, json={"total": 1, "data": [{"id": "123", "full_name": "Test Person", "job_title": "software engineer", "skills": ["python"], "mobile_phone": "+919000000001"}]})
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    response = client.post("/api/search", json=INPUT)
    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["id"] == "pdl-123" and row["phone"] == "+919000000001"
    assert "match" not in row and "experience" not in row
    assert sourcing.get_candidate(row["id"])["custom_data"]["job_description"] == INPUT["job_description"]


def test_no_results_and_provider_errors_are_not_demo_data(client, monkeypatch):
    async def missing(*args, **kwargs): return httpx.Response(404)
    monkeypatch.setattr(httpx.AsyncClient, "post", missing)
    assert client.post("/api/search", json=INPUT).json()["results"] == []
    async def denied(*args, **kwargs): return httpx.Response(401)
    monkeypatch.setattr(httpx.AsyncClient, "post", denied)
    assert client.post("/api/search", json=INPUT).status_code == 503


def test_sourced_contact_can_reach_hunar_with_job_context(client, monkeypatch):
    sourcing.save_candidate({"id": "pdl-1", "name": "Test Person", "phone": "+919000000001", "custom_data": {"role_title": "software engineer", "key_skills": "python"}})
    sent = []
    async def provider(method, path, payload=None):
        if path.startswith("agents/"):
            return {"results": [{"id": "agent", "required_variables": ["role_title", "company"]}], "next": None}
        if path.startswith("calls/?"):
            return {"results": [], "next": None}
        sent.append(payload)
        return [{"id": "created", "status": "SCHEDULED"}]
    monkeypatch.setattr(main, "hunar", provider)
    monkeypatch.setattr(main.settings, "hunar_live_calls", True)
    body = {"candidate_ids": ["pdl-1"], "agent_id": "agent", "confirmed": True, "company": "Test Hiring Company"}
    assert client.post("/api/outreach", json=body).status_code == 200
    assert sent[0]["data"][0]["custom_data"]["company"] == "Test Hiring Company"
    assert sent[0]["data"][0]["custom_data"]["role_title"] == "software engineer"


def test_agent_missing_required_data_stops_before_call(client, monkeypatch):
    sourcing.save_candidate({"id": "pdl-2", "name": "Test Person", "phone": "+919000000001", "custom_data": {}})
    async def provider(method, path, payload=None):
        assert method == "GET"
        return {"results": [{"id": "agent", "required_variables": ["shift"]}] if path.startswith("agents/") else [], "next": None}
    monkeypatch.setattr(main, "hunar", provider)
    monkeypatch.setattr(main.settings, "hunar_live_calls", True)
    result = client.post("/api/outreach", json={"candidate_ids": ["pdl-2"], "agent_id": "agent", "confirmed": True, "company": "Company"})
    assert result.status_code == 422 and "shift" in result.json()["detail"]
