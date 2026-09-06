from __future__ import annotations

import asyncio
from contextvars import ContextVar
from time import monotonic

import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from .sourcing import SearchRequest, criteria, search_people, get_candidate

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    hunar_api_key: str = ""
    pdl_api_key: str = ""
    hunar_base_url: str = "https://api.voice.hunar.ai/external/v1"
    hunar_agent_id: str = ""
    hunar_live_calls: bool = True
    frontend_origin: str = "http://localhost:3000"
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")


settings = Settings()
app = FastAPI(title="Niyora Hunar API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


_client: ContextVar[httpx.AsyncClient | None] = ContextVar("hunar_client", default=None)
_dashboard_cache: dict = {}
_dashboard_task: asyncio.Task | None = None


async def hunar(method: str, path: str, payload: dict | None = None) -> Any:
    if not settings.hunar_api_key:
        raise HTTPException(503, "Hunar API key is not configured")
    base = settings.hunar_base_url.rstrip("/") + "/"
    url = urljoin(base, path)
    if (urlparse(url).scheme != urlparse(base).scheme
            or urlparse(url).netloc != urlparse(base).netloc
            or not urlparse(url).path.startswith(urlparse(base).path)):
        raise HTTPException(502, "Invalid Hunar pagination URL")
    try:
        client = _client.get()
        if client is not None:
            response = await client.request(method, url,
                headers={"X-API-Key": settings.hunar_api_key}, json=payload)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(method, url,
                    headers={"X-API-Key": settings.hunar_api_key}, json=payload)
        if response.is_error:
            raise HTTPException(502, f"Hunar API returned HTTP {response.status_code}. Check account access and configuration.")
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "Could not read Hunar API. Please retry.") from None


async def all_rows(path: str) -> list[dict]:
    rows = []
    seen = set()
    next_page = path + "?page_size=100"
    while next_page:
        if next_page in seen or len(seen) >= 1000:
            raise HTTPException(502, "Hunar pagination could not complete")
        seen.add(next_page)
        data = await hunar("GET", next_page)
        if isinstance(data, list):
            rows.extend(data)
            break
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise HTTPException(502, "Unexpected Hunar list response")
        rows.extend(data["results"])
        next_page = data.get("next")
    return rows


def normalize_call(row: dict) -> dict:
    transcript = row.get("transcript") or []
    if isinstance(transcript, str):
        transcript = [{"speaker": "Transcript", "text": transcript}]
    if not isinstance(transcript, list):
        transcript = []
    return {
        "id": str(row["id"]), "candidate_id": str(row["id"]),
        "candidate_name": row.get("callee_name") or "Unnamed contact",
        "phone": row.get("mobile_number") or "", "agent_id": row.get("agent_id") or "",
        "status": row.get("status") or row.get("lifecycle_status") or "UNKNOWN",
        "duration": round(row.get("duration_seconds") or 0),
        "recording_url": row.get("recording_url") or "",
        "transcript": [{"speaker": str(t.get("speaker") or t.get("role") or "Speaker"),
                        "text": str(t.get("text") or t.get("content") or "")}
                       for t in transcript if isinstance(t, dict)],
        "result": row.get("result") if isinstance(row.get("result"), dict) else {},
        "created_at": row.get("created_at") or "", "provider": "hunar",
    }


def contacts(rows: list[dict]) -> list[dict]:
    found = {}
    for row in sorted(rows, key=lambda r: r.get("created_at") or "", reverse=True):
        phone = row.get("mobile_number") or ""
        identity = phone or str(row["id"])
        if identity in found:
            continue
        custom = row.get("custom_data") or {}
        skills = custom.get("key_skills") or custom.get("skills") or []
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        name = row.get("callee_name") or "Unnamed contact"
        found[identity] = {
            "id": str(row["id"]), "name": name, "phone": phone,
            "role": custom.get("role_title") or custom.get("job_role") or "",
            "company": custom.get("company") or "", "location": custom.get("location") or "",
            "email": custom.get("email") or "", "skills": skills if isinstance(skills, list) else [],
            "status": row.get("status") or "UNKNOWN",
            "avatar": "".join(w[0] for w in name.split()[:2]).upper(),
        }
    return list(found.values())


@app.get("/api/health")
def health():
    return {"status": "ok", "hunar_configured": bool(settings.hunar_api_key),
            "live_calls": settings.hunar_live_calls, "source": "hunar"}


async def load_dashboard():
    async with httpx.AsyncClient(timeout=30) as client:
        token = _client.set(client)
        try:
            rows, agents = await asyncio.gather(all_rows("calls/"), all_rows("agents/"))
        finally:
            _client.reset(token)
    return {"candidates": contacts(rows), "calls": [normalize_call(r) for r in rows],
            "agents": [{"id": a["id"], "name": a.get("name") or a["id"],
                        "status": a.get("status") or "", "summary": a.get("summary") or ""} for a in agents],
            "source": "hunar", "live_calls": settings.hunar_live_calls,
            "default_agent_id": settings.hunar_agent_id}


@app.get("/api/dashboard")
async def dashboard(refresh: bool = False):
    global _dashboard_task
    if not refresh and _dashboard_cache.get("expires", 0) > monotonic():
        return _dashboard_cache["data"]
    if _dashboard_task is None or _dashboard_task.done():
        async def load():
            data = await load_dashboard()
            _dashboard_cache.update(data=data, expires=monotonic() + 30)
            return data
        _dashboard_task = asyncio.create_task(load())
    return await asyncio.shield(_dashboard_task)


@app.get("/api/candidates")
async def candidates():
    results = contacts(await all_rows("calls/"))
    return {"results": results, "total": len(results), "source": "hunar"}


@app.get("/api/search/config")
def search_config():
    return {"provider": "pdl", "configured": bool(settings.pdl_api_key)}


@app.post("/api/search/criteria")
def search_criteria(body: SearchRequest):
    return criteria(body)


@app.post("/api/search")
async def search(body: SearchRequest):
    return await search_people(body, settings.pdl_api_key)


@app.get("/api/hunar/agents")
async def agents():
    return {"results": await all_rows("agents/"), "configured": True}


@app.get("/api/calls")
async def calls():
    return {"results": [normalize_call(r) for r in await all_rows("calls/")], "source": "hunar"}


@app.get("/api/calls/{call_id}")
async def call_detail(call_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", call_id):
        raise HTTPException(422, "Invalid call ID")
    return normalize_call(await hunar("GET", f"calls/{call_id}/"))


class OutreachRequest(BaseModel):
    candidate_ids: list[str] = Field(min_length=1, max_length=100)
    agent_id: str
    confirmed: bool = False
    company: str = Field(default="", max_length=150)


@app.post("/api/outreach")
async def outreach(body: OutreachRequest):
    if not settings.hunar_live_calls or not body.confirmed:
        raise HTTPException(409, "Confirm live calling before launching outreach")
    available_agents = await all_rows("agents/")
    if body.agent_id not in {str(a["id"]) for a in available_agents}:
        raise HTTPException(422, "Select an available Hunar agent")
    rows = await all_rows("calls/")
    indexed = {str(r["id"]): r for r in rows}
    for cid in body.candidate_ids:
        if cid.startswith("pdl-"):
            candidate = get_candidate(cid)
            if candidate:
                custom = {**candidate.get("custom_data", {}), "company": body.company.strip()}
                if not custom["company"]:
                    raise HTTPException(422, "Enter the hiring company for sourced candidates")
                indexed[cid] = {"id": cid, "callee_name": candidate["name"],
                                "mobile_number": candidate["phone"], "custom_data": custom}
    if any(cid not in indexed for cid in body.candidate_ids):
        raise HTTPException(404, "Selected contact is no longer available")
    selected = [indexed[cid] for cid in dict.fromkeys(body.candidate_ids)]
    if any(not re.fullmatch(r"\+?[0-9]{7,15}", r.get("mobile_number") or "") for r in selected):
        raise HTTPException(422, "Each selected contact needs a valid phone number")
    agent = next(a for a in available_agents if str(a["id"]) == body.agent_id)
    required = agent.get("required_variables") or []
    for candidate in selected:
        missing = [name for name in required if name not in ("callee_name", "mobile_number")
                   and not candidate.get("custom_data", {}).get(name)]
        if missing:
            raise HTTPException(422, "Selected agent needs these contact fields: " + ", ".join(missing))
    created = await hunar("POST", "calls/bulk/", {
        "agent_id": body.agent_id,
        "data": [{"callee_name": r.get("callee_name") or "", "mobile_number": r["mobile_number"],
                  "custom_data": r.get("custom_data") or {}} for r in selected],
        "remove_invalid_rows": False, "remove_duplicate_phone_numbers": True,
        "request_id": f"niyora-{uuid.uuid4().hex}",
    })
    _dashboard_cache.clear()
    return {"calls": created, "mode": "live", "message": "Hunar accepted the outreach request"}
