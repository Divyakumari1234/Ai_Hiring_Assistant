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
- People search: filters existing Hunar call contacts by text; it does not source new candidates or calculate AI match scores.
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

External candidate sourcing from a job description is not implemented. A controlled real-call test covering outreach through returned answers, and verification of a public deployment, remain pending.
