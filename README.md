# Reachly - Hunar voice workspace

The dashboard reads company agents and calls directly from the configured Hunar account. Contacts are deduplicated from Hunar call history. Counts are calculated from these records. There are no seeded contacts, demo calls, GitHub search results or invented match scores.

## Run locally (PowerShell)

Configure `backend/.env` from `.env.example` with the supplied Hunar key and agent ID. Keep the key on the backend.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Refresh retrieves the current provider data. Failed API requests display an error; empty accounts display empty states.

## Data and actions

- Overview: actual contact, completed-call, interested-response and agent counts from Hunar records. Interested responses count calls explicitly returning true/yes/high/interested, not unique people.
- People search: paste a job description, review extracted role/skills and location, then query People Data Labs. Switch between sourced profiles and existing Hunar contacts. Search is limited to 1-20 profiles per request, with no invented match scores.
- Conversations: fetches call details from Hunar on selection, showing structured results, recording and transcript only when provided.
- Outreach: select contacts and a company agent, tick the real-call confirmation, then click Launch live calls. This sends an actual bulk call request and may incur provider charges. The script and configuration belong to the Hunar agent. Set `HUNAR_LIVE_CALLS=false` to disable launches while still reading real data.
- Attendance plan: a clearly labelled feature proposal, not live attendance records.

Old local SQLite demo records are not read or changed. The browser never receives the API key. Live calls are not placed during tests.

## Validation

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Run `npm run lint` and `npm run build` in `frontend`.

Dashboard loading reuses provider connections and fetches agents and calls concurrently. Successful responses are cached in backend memory for 30 seconds; Refresh explicitly bypasses this cache. Concurrent requests share one fetch. Existing screen data remains visible during refresh, with an error notice if updating fails. No demo data is cached.

## Remaining assignment work

People Data Labs integration is implemented and tested with mocked provider responses. A valid Person Search key is required for live verification. A controlled real-call test and verification of a public deployment remain pending until account access and an authorized test number are available.


## People Data Labs setup

Add `PDL_API_KEY` to `backend/.env`, then restart the backend. This is separate from the Hunar key. The provider charges credits for returned profiles. Source: [PDL Person Search documentation](https://docs.peopledatalabs.com/docs/reference-person-search-api).

Select **Read job description** to extract supported title/skill keywords. Review and edit the filters before **Search new candidates**. This is deterministic keyword extraction, not an LLM ranking system. Missing phone numbers stay missing and those profiles cannot be selected for calling. Sourced profiles are saved in the local `backend/data/candidates.db`, which is ignored by Git. Enter your hiring company before launching outreach to sourced profiles.

## Deploy on Render

The root `Dockerfile` runs Next.js publicly and Python on loopback inside one container. The `render.yaml` Blueprint includes the required environment fields.

1. Open [Deploy to Render](https://render.com/deploy?repo=https://github.com/Divyakumari1234/Ai_Hiring_Assistant).
2. Connect your GitHub account and select this repository.
3. Enter `HUNAR_API_KEY`, `PDL_API_KEY`, and a strong `REVIEW_PASSWORD`. The login username defaults to `reviewer`. Keys belong in Render's secret environment fields, not GitHub.
4. Deploy and wait for `/healthz` to pass. Open the assigned HTTPS URL and log in.
5. Confirm candidate search, company data and one consented call before sharing the URL and reviewer login with HR.

Render's free service can sleep and its filesystem is ephemeral. Sourced candidate storage is lost on redeploy/restart; rerun search if a selected profile is no longer available. Do not claim a public deployment is verified until its actual URL has been tested. [Render Blueprint reference](https://render.com/docs/blueprint-spec).

For a local container check, set `$env:REVIEW_PASSWORD` in PowerShell and run `docker compose up --build` from the repository root. Open http://localhost:8080 and log in as `reviewer`. Docker Desktop must be running. Frontend tests run with `node --test tests/api.test.mjs tests/proxy.test.cjs` in `frontend` using Node 22.15+ with TypeScript stripping support (validated on Node 26).
