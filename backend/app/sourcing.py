"""People Data Labs search and storage for candidates selected for outreach."""

import json
import re
import sqlite3
from pathlib import Path

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

DATABASE = Path(__file__).resolve().parents[1] / "data" / "candidates.db"


class SearchRequest(BaseModel):
    job_description: str = Field(min_length=20, max_length=12000)
    job_title: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=20)
    limit: int = Field(default=5, ge=1, le=20)


def criteria(body: SearchRequest) -> dict:
    roles = ["senior product designer", "product designer", "frontend engineer",
             "backend engineer", "software engineer", "data scientist", "data analyst",
             "product manager", "sales executive", "warehouse associate", "recruiter"]
    title = body.job_title.strip() or next(
        (role for role in roles if role in body.job_description.lower()), "")
    if not title:
        raise HTTPException(422, "Enter a job title to search for this job description")
    known_skills = ["python", "react", "typescript", "javascript", "sql", "figma",
                    "java", "excel", "sales", "recruiting", "kubernetes", "docker"]
    skills = body.skills or [skill for skill in known_skills
                            if re.search(r"\b" + re.escape(skill) + r"\b", body.job_description.lower())]
    return {"job_title": title.lower(), "location": body.location.strip().lower(),
            "skills": list(dict.fromkeys(s.strip().lower() for s in skills if s.strip()))}


def save_candidate(candidate: dict) -> None:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE) as db:
        db.execute("CREATE TABLE IF NOT EXISTS sourced_candidates (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
        db.execute("INSERT OR REPLACE INTO sourced_candidates VALUES (?, ?)",
                   (candidate["id"], json.dumps(candidate)))


def get_candidate(candidate_id: str) -> dict | None:
    if not DATABASE.exists():
        return None
    with sqlite3.connect(DATABASE) as db:
        row = db.execute("SELECT data FROM sourced_candidates WHERE id=?", (candidate_id,)).fetchone()
    return json.loads(row[0]) if row else None


async def search_people(body: SearchRequest, api_key: str) -> dict:
    if not api_key:
        raise HTTPException(503, "People Data Labs is not configured. Add PDL_API_KEY on the server to search new candidates.")
    filters = criteria(body)
    must = [{"match": {"job_title": {"query": filters["job_title"], "operator": "and"}}}]
    if filters["location"]:
        must.append({"match": {"location_name": filters["location"]}})
    must.extend({"term": {"skills": skill}} for skill in filters["skills"])
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.peopledatalabs.com/v5/person/search",
                headers={"X-Api-Key": api_key},
                json={"query": {"query": {"bool": {"must": must}}}, "size": body.limit},
            )
        if response.status_code == 404:
            return {"results": [], "total": 0, "source": "pdl", "criteria": filters}
        if response.status_code in (401, 403):
            raise HTTPException(503, "People Data Labs key or Person Search access is invalid. Check your provider account.")
        if response.status_code in (402, 429):
            raise HTTPException(503, "People Data Labs credits or rate limit reached. Check your provider account before retrying.")
        if response.is_error:
            raise HTTPException(502, f"People Data Labs search failed (HTTP {response.status_code})")
        data = response.json()
        if not isinstance(data.get("data"), list):
            raise ValueError("Invalid search response")
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "Could not read People Data Labs. No demo results were substituted.") from None
    results = []
    for person in data["data"]:
        if not person.get("id"):
            continue
        name = person.get("full_name") or "Unnamed candidate"
        numbers = [person.get("mobile_phone"), *(person.get("phone_numbers") or [])]
        phone = next((number for number in numbers if isinstance(number, str)
                      and re.fullmatch(r"\+?[0-9]{7,15}", number)), "")
        candidate = {
            "id": "pdl-" + str(person["id"]), "name": name,
            "phone": phone, "email": person.get("work_email") or "",
            "role": person.get("job_title") or "", "company": person.get("job_company_name") or "",
            "location": person.get("location_name") or "", "skills": person.get("skills") or [],
            "status": "Ready for review" if phone else "Phone unavailable",
            "avatar": "".join(part[0] for part in name.split()[:2]).upper(),
            "source": "pdl", "custom_data": {"role_title": filters["job_title"],
                "job_description": body.job_description, "key_skills": ", ".join(filters["skills"]),
                "location": filters["location"]},
        }
        save_candidate(candidate)
        results.append(candidate)
    return {"results": results, "total": data.get("total", len(results)),
            "source": "pdl", "criteria": filters}
