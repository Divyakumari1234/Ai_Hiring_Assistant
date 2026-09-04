from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "reachly.db"


class Settings(BaseSettings):
    hunar_api_key: str = ""
    hunar_base_url: str = "https://api.voice.hunar.ai/external/v1"
    hunar_agent_id: str = ""
    hunar_live_calls: bool = False
    frontend_origin: str = "http://localhost:3000"
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")


settings = Settings()
SEARCHED_CANDIDATES: dict[str, dict[str, Any]] = {}


SEED_CANDIDATES = [
    {
        "id": "c1",
        "name": "Aarav Mehta",
        "role": "Senior Product Designer",
        "company": "Razorpay",
        "location": "Bengaluru, India",
        "experience": 7,
        "match": 96,
        "phone": "+919876540101",
        "email": "aarav.mehta@example.com",
        "skills": ["Figma", "Design systems", "Research"],
        "status": "Qualified",
        "avatar": "AM",
    },
    {
        "id": "c2",
        "name": "Meera Nair",
        "role": "Product Designer II",
        "company": "CRED",
        "location": "Bengaluru, India",
        "experience": 5,
        "match": 93,
        "phone": "+919876540102",
        "email": "meera.nair@example.com",
        "skills": ["Figma", "Prototyping", "Fintech"],
        "status": "Interested",
        "avatar": "MN",
    },
    {
        "id": "c3",
        "name": "Kabir Shah",
        "role": "Senior UX Designer",
        "company": "Groww",
        "location": "Mumbai, India",
        "experience": 6,
        "match": 89,
        "phone": "+919876540103",
        "email": "kabir.shah@example.com",
        "skills": ["UX strategy", "Research", "Mobile"],
        "status": "New",
        "avatar": "KS",
    },
    {
        "id": "c4",
        "name": "Ishita Rao",
        "role": "Product Designer",
        "company": "Swiggy",
        "location": "Hyderabad, India",
        "experience": 4,
        "match": 86,
        "phone": "+919876540104",
        "email": "ishita.rao@example.com",
        "skills": ["Interaction", "Figma", "B2C"],
        "status": "Call scheduled",
        "avatar": "IR",
    },
    {
        "id": "c5",
        "name": "Rohan Verma",
        "role": "Lead Product Designer",
        "company": "Flipkart",
        "location": "Delhi, India",
        "experience": 9,
        "match": 82,
        "phone": "+919876540105",
        "email": "rohan.verma@example.com",
        "skills": ["Leadership", "Systems", "Discovery"],
        "status": "Not connected",
        "avatar": "RV",
    },
    {
        "id": "c6",
        "name": "Sana Khan",
        "role": "UX Designer",
        "company": "PhonePe",
        "location": "Pune, India",
        "experience": 5,
        "match": 80,
        "phone": "+919876540106",
        "email": "sana.khan@example.com",
        "skills": ["Research", "Accessibility", "Figma"],
        "status": "New",
        "avatar": "SK",
    },
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS calls (
            id TEXT PRIMARY KEY, candidate_id TEXT, candidate_name TEXT, status TEXT,
            duration INTEGER DEFAULT 0, recording_url TEXT, transcript TEXT,
            result TEXT, created_at TEXT, updated_at TEXT, provider TEXT
        )""")
        if not db.execute("SELECT 1 FROM calls LIMIT 1").fetchone():
            samples = [
                (
                    "call-101",
                    "c1",
                    "Aarav Mehta",
                    "COMPLETED",
                    248,
                    "",
                    json.dumps(
                        [
                            {
                                "speaker": "AI",
                                "text": "Hi Aarav, is this a good time to discuss a product design role?",
                            },
                            {
                                "speaker": "Candidate",
                                "text": "Yes, I have a few minutes. I am actively exploring senior product design roles.",
                            },
                        ]
                    ),
                    json.dumps(
                        {
                            "interest": "High",
                            "notice_period": "30 days",
                            "current_ctc": "24 LPA",
                            "expected_ctc": "30 LPA",
                            "availability": "Weekdays after 6 PM",
                        }
                    ),
                    now(),
                    now(),
                    "demo",
                ),
                (
                    "call-102",
                    "c2",
                    "Meera Nair",
                    "COMPLETED",
                    194,
                    "",
                    json.dumps(
                        [
                            {
                                "speaker": "AI",
                                "text": "What kind of product problems are you looking to solve next?",
                            },
                            {
                                "speaker": "Candidate",
                                "text": "I want to own zero-to-one fintech products and mentor junior designers.",
                            },
                        ]
                    ),
                    json.dumps(
                        {
                            "interest": "High",
                            "notice_period": "45 days",
                            "current_ctc": "21 LPA",
                            "expected_ctc": "27 LPA",
                            "availability": "Saturday morning",
                        }
                    ),
                    now(),
                    now(),
                    "demo",
                ),
                (
                    "call-103",
                    "c5",
                    "Rohan Verma",
                    "NOT_CONNECTED",
                    0,
                    "",
                    json.dumps([]),
                    json.dumps({}),
                    now(),
                    now(),
                    "demo",
                ),
            ]
            db.executemany("INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?)", samples)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Reachly API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    job_description: str = Field(min_length=20, max_length=12000)
    location: str = "India"
    experience_min: int = Field(0, ge=0, le=30)
    experience_max: int = Field(15, ge=0, le=40)
    limit: int = Field(6, ge=1, le=50)
    provider: Literal["github", "demo"] = "github"


class OutreachRequest(BaseModel):
    candidate_ids: list[str] = Field(min_length=1, max_length=100)
    agent_id: str | None = None
    channel: Literal["voice", "voice+sms"] = "voice"


def candidate_rows(query: str = "", location: str = "") -> list[dict[str, Any]]:
    words = {w.lower().strip(".,()") for w in query.split() if len(w) > 3}
    rows = []
    for person in SEED_CANDIDATES:
        haystack = " ".join(
            [person["role"], person["company"], *person["skills"]]
        ).lower()
        overlap = min(8, sum(1 for word in words if word in haystack))
        copy = dict(person)
        copy["match"] = min(99, copy["match"] + overlap)
        if (
            location
            and location.lower() not in "india"
            and location.lower() not in copy["location"].lower()
        ):
            copy["match"] = max(60, copy["match"] - 9)
        rows.append(copy)
    return sorted(rows, key=lambda row: row["match"], reverse=True)


def role_from_jd(text: str) -> str:
    lowered = text.lower()
    roles = [
        "product designer",
        "frontend engineer",
        "backend engineer",
        "data scientist",
        "devops engineer",
        "product manager",
        "software engineer",
    ]
    return next((role for role in roles if role in lowered), "software engineer")


async def github_people_search(body: SearchRequest) -> list[dict[str, Any]]:
    """Real public-profile search adapter backed by GitHub's public API."""
    role = role_from_jd(body.job_description)
    query = f'"{role}" location:"{body.location}"'
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "reachly-hiring-assistant",
    }
    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        search = await client.get(
            "https://api.github.com/search/users",
            params={"q": query, "per_page": body.limit},
        )
        search.raise_for_status()
        profiles = await __import__("asyncio").gather(
            *(client.get(item["url"]) for item in search.json().get("items", []))
        )
    results: list[dict[str, Any]] = []
    for index, response in enumerate(profiles):
        if response.is_error:
            continue
        profile = response.json()
        candidate_id = f"github-{profile['id']}"
        candidate = {
            "id": candidate_id,
            "name": profile.get("name") or profile["login"],
            "role": (profile.get("bio") or role.title())[:100],
            "company": (profile.get("company") or "Independent").lstrip("@"),
            "location": profile.get("location") or body.location,
            "experience": max(
                body.experience_min, min(body.experience_max, 4 + index % 5)
            ),
            "match": max(72, 94 - index * 3),
            "phone": "",
            "email": profile.get("email") or "",
            "skills": [role.title(), "GitHub", "Open source"],
            "status": "New",
            "avatar": "".join(
                (profile.get("name") or profile["login"]).split()[:2][i][0].upper()
                for i in range(
                    min(2, len((profile.get("name") or profile["login"]).split()[:2]))
                )
            ),
            "profile_url": profile.get("html_url"),
            "source": "GitHub",
        }
        SEARCHED_CANDIDATES[candidate_id] = candidate
        results.append(candidate)
    return results


async def hunar(method: str, path: str, payload: dict | None = None) -> Any:
    if not settings.hunar_api_key:
        raise HTTPException(503, "Hunar API key is not configured")
    headers = {"X-API-Key": settings.hunar_api_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(
            method,
            f"{settings.hunar_base_url.rstrip('/')}/{path.lstrip('/')}",
            headers=headers,
            json=payload,
        )
    if response.is_error:
        detail = "Hunar request failed"
        try:
            detail = response.json()
        except (json.JSONDecodeError, ValueError):
            detail = f"Hunar request failed with status {response.status_code}"
        raise HTTPException(response.status_code, detail)
    return response.json()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "hunar_configured": bool(settings.hunar_api_key),
        "live_calls": settings.hunar_live_calls,
    }


@app.get("/api/candidates")
def candidates(q: str = "", location: str = ""):
    return {
        "results": candidate_rows(q, location),
        "source": "demo",
        "total": len(SEED_CANDIDATES),
    }


@app.post("/api/search")
async def search(body: SearchRequest):
    source = body.provider
    if body.provider == "github":
        try:
            results = await github_people_search(body)
        except (httpx.HTTPError, KeyError):
            results = []
        if results:
            return {
                "results": results,
                "total": len(results),
                "source": "github-public-profiles",
                "criteria": {
                    "location": body.location,
                    "experience": f"{body.experience_min}-{body.experience_max} years",
                },
            }
        source = "demo-fallback"
    results = [
        r
        for r in candidate_rows(body.job_description, body.location)
        if body.experience_min <= r["experience"] <= body.experience_max
    ][: body.limit]
    return {
        "results": results,
        "total": len(results),
        "source": source,
        "criteria": {
            "location": body.location,
            "experience": f"{body.experience_min}-{body.experience_max} years",
        },
    }


@app.get("/api/hunar/agents")
async def agents():
    if not settings.hunar_api_key:
        return {"results": [], "configured": False}
    data = await hunar("GET", "agents/?page_size=100")
    data["configured"] = True
    return data


@app.post("/api/outreach")
async def outreach(body: OutreachRequest):
    selected = [
        c
        for c in [*SEED_CANDIDATES, *SEARCHED_CANDIDATES.values()]
        if c["id"] in body.candidate_ids
    ]
    if not selected:
        raise HTTPException(404, "No matching candidates found")
    agent_id = body.agent_id or settings.hunar_agent_id
    live = settings.hunar_live_calls and bool(settings.hunar_api_key and agent_id)
    if live and any(not c.get("phone") for c in selected):
        raise HTTPException(
            422,
            "Live outreach requires a verified phone number for every selected candidate",
        )
    created = []
    if live:
        payload = {
            "agent_id": agent_id,
            "data": [
                {
                    "callee_name": c["name"],
                    "mobile_number": c["phone"],
                    "custom_data": {
                        "job_role": c["role"],
                        "company": "Acme India",
                        "location": c["location"],
                    },
                }
                for c in selected
            ],
            "remove_invalid_rows": True,
            "remove_duplicate_phone_numbers": True,
            "request_id": f"reachly-{uuid.uuid4().hex[:12]}",
        }
        created = await hunar("POST", "calls/bulk/", payload)
    else:
        created = [
            {
                "id": f"demo-{uuid.uuid4().hex[:10]}",
                "callee_name": c["name"],
                "mobile_number": c["phone"],
                "status": "SCHEDULED",
            }
            for c in selected
        ]
    with connect() as db:
        for call in created:
            candidate = next(
                (c for c in selected if c["name"] == call.get("callee_name")),
                selected[0],
            )
            db.execute(
                "INSERT OR REPLACE INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    call["id"],
                    candidate["id"],
                    candidate["name"],
                    call.get("status", "SCHEDULED"),
                    0,
                    "",
                    json.dumps([]),
                    json.dumps({"channel": body.channel}),
                    now(),
                    now(),
                    "hunar" if live else "demo",
                ),
            )
        db.commit()
    return {
        "calls": created,
        "mode": "live" if live else "demo",
        "message": f"{len(created)} outreach call(s) queued",
    }


@app.get("/api/calls")
def calls(status: str | None = Query(None)):
    with connect() as db:
        query = (
            "SELECT * FROM calls"
            + (" WHERE status = ?" if status else "")
            + " ORDER BY created_at DESC"
        )
        rows = db.execute(query, (status,) if status else ()).fetchall()
    return {
        "results": [
            {
                **dict(r),
                "result": json.loads(r["result"] or "{}"),
                "transcript": json.loads(r["transcript"] or "[]"),
            }
            for r in rows
        ]
    }


@app.get("/api/calls/{call_id}")
async def call_detail(call_id: str, refresh: bool = False):
    with connect() as db:
        row = db.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Call not found")
    if refresh and row["provider"] == "hunar":
        data = await hunar("GET", f"calls/{call_id}/")
        return data
    return {
        **dict(row),
        "result": json.loads(row["result"] or "{}"),
        "transcript": json.loads(row["transcript"] or "[]"),
    }


@app.post("/api/webhooks/hunar")
async def webhook(request: Request):
    payload = await request.json()
    call_id = str(payload.get("id") or payload.get("call_id") or "")
    if call_id:
        with connect() as db:
            db.execute(
                "UPDATE calls SET status=?, duration=?, recording_url=?, result=?, updated_at=? WHERE id=?",
                (
                    payload.get("status", "COMPLETED"),
                    payload.get("duration_seconds", 0),
                    payload.get("recording_url", ""),
                    json.dumps(payload.get("result", {})),
                    now(),
                    call_id,
                ),
            )
            db.commit()
    return {"received": True}
