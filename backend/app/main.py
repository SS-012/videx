from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings

         
from .routers.documents import router as documents_router
from .routers.annotations import router as annotations_router
from .routers.chat import router as chat_router

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allow_origin, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize data directories on startup"""
    settings.ensure_directories()


@app.get("/health")
async def health():
    return {"status": "ok"}


                  
app.include_router(documents_router)
app.include_router(annotations_router)
app.include_router(chat_router)
