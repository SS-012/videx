# VIDEX

AI-assisted data annotation tool with RAG + ICL for smart suggestions.

## Installation

```bash
git clone https://github.com/SS-012/videx.git
cd videx

# Backend
cd backend
pip install -r requirements.txt

# ML Service
cd ../ml_service
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

## Configuration

Copy `.env.example` to `.env` and add your OpenAI API key:
```bash
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

## Running

Open 3 terminals from project root:

```bash
# Terminal 1 - Backend
uvicorn backend.app.main:app --reload --port 8000

# Terminal 2 - ML Service
uvicorn ml_service.main:app --reload --port 8001

# Terminal 3 - Frontend (from frontend/)
cd frontend && npm run dev
```

Open http://localhost:3000

---
@Shohaib Shah
