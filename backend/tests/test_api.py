import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import main


@pytest.fixture(autouse=True)
def clear_dashboard_cache():
    main._dashboard_cache.clear()
    main._dashboard_task = None
    yield
    main._dashboard_cache.clear()
    main._dashboard_task = None


@pytest.fixture
def provider(monkeypatch):
    requests = []
    row = {"id": "call-real", "callee_name": "Test Contact", "mobile_number": "+919000000001",
           "agent_id": "agent-real", "status": "COMPLETED", "duration_seconds": 12.5,
           "created_at": "2026-09-05T10:00:00Z", "custom_data": {"role_title": "Engineer", "key_skills": "Python, SQL"},
           "result": {"interested": True, "salary_expectation": {"amount": 10}},
           "transcript": [{"role": "assistant", "content": "Hello"}]}
    async def fake(method, path, payload=None):
        requests.append((method, path, payload))
        if method == "POST": return [{"id": "new-call", "status": "SCHEDULED"}]
        if path.startswith("agents/"): return {"results": [{"id": "agent-real", "name": "Hiring agent"}], "next": None}
        if path == "calls/call-real/": return row
        if "page=2" in path: return {"results": [{**row, "id": "older-call", "created_at": "2026-09-04T10:00:00Z"}], "next": None}
        return {"results": [row], "next": "https://api.voice.hunar.ai/external/v1/calls/?page=2"}
    monkeypatch.setattr(main, "hunar", fake)
    monkeypatch.setattr(main.settings, "hunar_live_calls", True)
    return requests


def test_dashboard_reads_all_pages_and_deduplicates_contacts(provider):
    with TestClient(main.app) as client:
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "hunar"
        assert len(data["calls"]) == 2
        assert len(data["candidates"]) == 1
        contact = data["candidates"][0]
        assert contact["role"] == "Engineer"
        assert "match" not in contact and "experience" not in contact
        assert contact["skills"] == ["Python", "SQL"]
        assert data["calls"][0]["result"]["interested"] is True
        assert all(method == "GET" for method, _, _ in provider)


def test_failure_is_error_without_demo_fallback(monkeypatch):
    async def fail(*args, **kwargs): raise HTTPException(502, "Hunar unavailable")
    monkeypatch.setattr(main, "hunar", fail)
    with TestClient(main.app) as client:
        for endpoint in ["/api/dashboard", "/api/candidates", "/api/calls"]:
            r = client.get(endpoint)
            assert r.status_code == 502
            assert "results" not in r.json()


def test_detail_keeps_nested_results_and_transcript(provider):
    with TestClient(main.app) as client:
        data = client.get("/api/calls/call-real").json()
        assert data["result"]["salary_expectation"] == {"amount": 10}
        assert data["transcript"] == [{"speaker": "assistant", "text": "Hello"}]


def test_outreach_requires_confirmation_and_real_contact(provider):
    with TestClient(main.app) as client:
        payload = {"candidate_ids": ["call-real"], "agent_id": "agent-real"}
        assert client.post("/api/outreach", json=payload).status_code == 409
        assert not provider
        payload["confirmed"] = True
        response = client.post("/api/outreach", json=payload)
        assert response.status_code == 200
        assert response.json()["mode"] == "live"
        method, path, sent = provider[-1]
        assert method == "POST" and path == "calls/bulk/"
        assert sent["data"][0]["custom_data"]["role_title"] == "Engineer"
        payload["candidate_ids"] = ["c1"]
        assert client.post("/api/outreach", json=payload).status_code == 404


def test_empty_account_stays_empty(monkeypatch):
    async def empty(*args, **kwargs): return {"results": [], "next": None}
    monkeypatch.setattr(main, "hunar", empty)
    with TestClient(main.app) as client:
        data = client.get("/api/dashboard").json()
        assert data["calls"] == data["candidates"] == data["agents"] == []


def test_provider_does_not_send_key_to_foreign_pagination_url(monkeypatch):
    import asyncio
    monkeypatch.setattr(main.settings, "hunar_api_key", "test-secret")
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.hunar("GET", "https://example.com/calls/"))
    assert error.value.status_code == 502


def test_network_failure_becomes_bad_gateway(monkeypatch):
    import asyncio
    monkeypatch.setattr(main.settings, "hunar_api_key", "test-secret")
    async def fail(*args, **kwargs): raise httpx.ConnectError("unreachable")
    monkeypatch.setattr(httpx.AsyncClient, "request", fail)
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.hunar("GET", "calls/"))
    assert error.value.status_code == 502


def test_dashboard_cache_and_explicit_refresh(provider):
    with TestClient(main.app) as client:
        assert client.get("/api/dashboard").status_code == 200
        first = len(provider)
        assert client.get("/api/dashboard").status_code == 200
        assert len(provider) == first
        assert client.get("/api/dashboard?refresh=true").status_code == 200
        assert len(provider) > first


def test_expired_dashboard_cache_fetches_new_data(provider):
    with TestClient(main.app) as client:
        client.get("/api/dashboard")
        first = len(provider)
        main._dashboard_cache["expires"] = 0
        client.get("/api/dashboard")
        assert len(provider) > first


def test_concurrent_dashboard_requests_share_provider_fetch(monkeypatch):
    import asyncio
    count = 0
    async def load():
        nonlocal count
        count += 1
        await asyncio.sleep(0.01)
        return {"source": "hunar"}
    monkeypatch.setattr(main, "load_dashboard", load)
    async def check():
        responses = await asyncio.gather(main.dashboard(), main.dashboard())
        assert responses == [{"source": "hunar"}, {"source": "hunar"}]
    asyncio.run(check())
    assert count == 1
