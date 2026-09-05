# Architecture

Next.js proxies `/api/*` to FastAPI. FastAPI authenticates server-side to Hunar using `X-API-Key` from `backend/.env`.

`GET /api/dashboard` reads all pages of Hunar `calls/` and `agents/`. Contacts are derived from the newest call per phone number. Missing profile fields remain absent; no match or experience scores are invented. UI counters derive from returned records.

`GET /api/calls/{id}` reads provider call details. Results retain their original JSON types. Recordings and transcripts are shown only if returned by the provider. Refresh reads the account again; no local demo database or webhook is used.

`POST /api/outreach` requires explicit live confirmation, an available account agent, and contacts present in current Hunar records. It forwards original contact custom data to Hunar `calls/bulk/`. The frontend does not pretend to configure agent scripts or unsupported SMS channels.

People search filters existing company contacts. The attendance screen is a feature proposal. Neither view claims access to an unverified external sourcing or attendance endpoint.

Provider failures return errors instead of demo data. Pagination is followed only within the configured provider API origin and path so credentials cannot be forwarded to a foreign host. No API secrets are sent to the browser.
