# Architecture and product decisions

## Hiring flow

1. HR pastes a job description and optional filters.
2. FastAPI extracts search intent and queries the configured people provider. The included demo provider keeps the evaluator flow usable without a paid PDL/Apollo key.
3. HR reviews ranked candidates and explicitly selects who may be contacted.
4. FastAPI reads the key from its environment and sends Hunar's documented bulk-call payload to `POST /external/v1/calls/bulk/`.
5. Call events update SQLite through the webhook endpoint; the dashboard presents status, transcript, recording, and structured answers.

The integration also supports `GET /external/v1/agents/`, `GET /external/v1/calls/`, and `GET /external/v1/calls/{id}/`. The browser never contacts Hunar directly.

## Attendance challenge

The proposal intentionally avoids smartphones and apps. Each site receives a known IVR number or offline-first GSM terminal. Employees check in using their ID, a rotating spoken phrase, and consented voice verification. Caller/site binding and anomaly scoring limit buddy punching. The LLM gathers context for exceptions but cannot mutate payroll; HR approval and an audit log remain mandatory.

Failure modes are covered by encrypted store-and-forward events, daily paper fallback codes, supervisor batch submission, and reconciliation reports.

## Production hardening

- Put the API behind managed TLS and rate limiting.
- Validate Hunar webhook signatures once the account secret is configured.
- Encrypt candidate PII and recordings at rest; use role-based access and retention limits.
- Replace SQLite with Postgres and run outreach creation through a durable queue.
- Obtain candidate consent and respect DND/time-window rules before enabling live calls.
