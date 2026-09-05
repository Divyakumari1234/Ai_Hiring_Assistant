# Architecture

Next.js proxies `/api/*` to FastAPI. FastAPI authenticates server-side to Hunar using `X-API-Key` from `backend/.env`.

`GET /api/dashboard` reads all pages of Hunar `calls/` and `agents/`. Contacts are derived from the newest call per phone number. Missing profile fields remain absent; no match or experience scores are invented. UI counters derive from returned records.

`GET /api/calls/{id}` reads provider call details. Results retain their original JSON types. Recordings and transcripts are shown only if returned by the provider. Refresh reads the account again; no local demo database or webhook is used.

`POST /api/outreach` requires explicit live confirmation, an available account agent, and contacts present in current Hunar records. It forwards original contact custom data to Hunar `calls/bulk/`. The frontend does not pretend to configure agent scripts or unsupported SMS channels.

People search can filter existing contacts or send reviewed JD criteria to People Data Labs. Sourced profiles are persisted in a separate SQLite table and their IDs resolve server-side for Hunar outreach. No sample records are seeded. The attendance screen is a feature proposal. Attendance records are not fetched; that screen remains a proposal.

Provider failures return errors instead of demo data. Pagination is followed only within the configured provider API origin and path so credentials cannot be forwarded to a foreign host. No API secrets are sent to the browser.

The root deployment image serves Next.js publicly and binds FastAPI to loopback. Reviewer HTTP Basic authentication protects the hosted workspace and API proxy; HTTPS is provided by the hosting platform. The public `/healthz` response reports availability only.
