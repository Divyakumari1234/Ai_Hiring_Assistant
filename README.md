# Reachly — AI Hiring Assistant

End-to-end hiring workflow built for the Hunar assignment: paste a job description, find matching people, launch Hunar voice outreach, and review structured answers in one dashboard. It also includes a concrete feature proposal for attendance tracking across 100 locations without smartphones or apps.

## Stack

- Frontend: Next.js App Router, React, TypeScript, shadcn/ui primitives, Lucide icons
- Backend: Python, FastAPI, SQLite
- Integrations: Hunar Voice API, optional People Data Labs adapter, CSV import

## Run locally

1. Copy `backend/.env.example` to `backend/.env` and add the Hunar key.
2. Backend:

   ```bash
   cd backend
   python -m venv .venv
   .venv/Scripts/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

3. Frontend (new terminal):

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Open http://localhost:3000. People search uses real GitHub public profiles by default and falls back to the bundled evaluator dataset during provider outages. Live Hunar calls are only made when `HUNAR_LIVE_CALLS=true`, preventing accidental calls during evaluation.

## Security

Secrets stay in `backend/.env`, which is gitignored. The browser only talks to FastAPI and never receives the Hunar key. Rotate the assignment key after testing because it was shared through an image.

## API routes

- `GET /api/health`
- `POST /api/search`
- `GET /api/candidates`
- `POST /api/outreach`
- `GET /api/calls`
- `GET /api/calls/{id}`
- `GET /api/hunar/agents`
- `POST /api/webhooks/hunar`
