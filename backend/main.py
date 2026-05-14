"""
FastAPI application entrypoint.
On startup: runs DB migration and RAG ingestion if needed.
"""
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import ENVIRONMENT
from backend.db.migrate import run_migration
from backend.rag.ingest import run_ingest
from backend.agent.orchestrator import chat

logging.basicConfig(
    level="DEBUG" if ENVIRONMENT == "development" else "INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# In-memory session store: session_id → message history
# For production use Redis or a proper session backend
_sessions: dict[str, list[dict]] = {}


def _ingest_in_background():
    try:
        run_ingest()
        logger.info("RAG ingest complete.")
    except Exception as e:
        logger.warning(f"RAG ingest failed — knowledge base unavailable: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Car Concierge...")
    run_migration()
    # Run ingest in background so uvicorn binds the port immediately
    # and Render's health check scanner can reach /health without waiting
    threading.Thread(target=_ingest_in_background, daemon=True).start()
    logger.info("Ready.")
    yield


app = FastAPI(
    title="AI Car Concierge",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-car-concierge"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    history = _sessions.get(req.session_id, [])

    try:
        response_text, updated_history = chat(req.message.strip(), history)
    except Exception as e:
        logger.exception(f"Chat error for session {req.session_id}: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")

    _sessions[req.session_id] = updated_history

    return ChatResponse(response=response_text, session_id=req.session_id)


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"cleared": session_id}
