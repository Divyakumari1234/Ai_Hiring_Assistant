# Architecture

Next.js proxies `/api/*` to FastAPI. FastAPI authenticates server-side to Hunar using `X-API-Key` from `backend/.env`.

`GET /api/dashboard` reads all pages of Hunar `calls/` and `agents/`. Contacts are derived from the newest call per phone number. Missing profile fields remain absent; no match or experience scores are invented. UI counters derive from returned records.

`GET /api/calls/{id}` reads provider call details. Results retain their original JSON types. Recordings and transcripts are shown only if returned by the provider. Refresh reads the account again; no local demo database or webhook is used.

`POST /api/outreach` requires live-call confirmation and an available account agent. Selected IDs resolve to Hunar contacts or saved People Data Labs profiles. Contact custom data is sent to Hunar `calls/bulk/`; the selected Hunar agent supplies the conversation script.

People search filters existing contacts or sends reviewed JD criteria to People Data Labs. Sourced profiles are persisted in SQLite and resolved server-side for outreach. The attendance screen documents the proposed IVR workflow; it does not collect live attendance records.

Provider failures return errors instead of demo data. Pagination is followed only within the configured provider API origin and path so credentials cannot be forwarded to a foreign host. No API secrets are sent to the browser.

The root deployment image serves Next.js publicly and binds FastAPI to loopback. Reviewer HTTP Basic authentication protects the hosted workspace and API proxy; HTTPS is provided by the hosting platform. The public `/healthz` response reports availability only.
