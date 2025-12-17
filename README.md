# videx

Local-first AI-assisted data annotation (Next.js + FastAPI — web app only)

## Dev

### Backend (FastAPI)
```bash
cd /Users/shohaib/videx
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
```

### Seed exemplars and index
```bash
cd /Users/shohaib/videx
source .venv/bin/activate
python -m backend.scripts.seed
```

### Frontend (Next.js)
```bash
cd frontend
# Optionally set backend url in .env.local
# NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
npm run dev
```

Note: Electron is currently not used. Run the web app via Next.js in the browser against the FastAPI backend.