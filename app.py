"""
Coding Agent - Main Application Entrypoint
============================================
Ye single file FastAPI ko run karta hai jo:
  1. Frontend (static/) serve karta hai
  2. Backend API endpoints provide karta hai (/api/chat, /api/upload, /api/files)

Chalane ka tareeqa (ek hi command):
    python app.py

Ya:
    uvicorn app:app --reload
"""

import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from agent.llm_provider import has_active_provider
from agent.session import SessionManager

load_dotenv()

app = FastAPI(title="Coding Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# Har browser session ki apni alag files (disk par) aur agent hote hain.
# Chat history aur RAG index dono ChromaDB me persistent hain.
sessions = SessionManager(api_key=GOOGLE_API_KEY)

from agent.mcp_tools import get_mcp_tools
get_mcp_tools()  # startup par hi MCP server launch/verify kar lete hain


# ---------- Request/Response models ----------

class SessionRequest(BaseModel):
    session_id: str | None = None  # agar browser ke paas purani id ho (localStorage)


class SessionResponse(BaseModel):
    session_id: str
    resumed: bool
    history: list[dict]
    files: dict


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    files: dict


# ---------- API routes ----------

@app.post("/api/session", response_model=SessionResponse)
def create_session(req: SessionRequest = SessionRequest()):
    """
    Naya chat session shuru karta hai, YA agar browser ne apni purani
    session_id bheji ho (localStorage se), to us ki history + files
    persistent storage se wapas load kar deta hai.
    """
    session_id = req.session_id or str(uuid.uuid4())
    data = sessions.create_or_resume(session_id)
    return SessionResponse(**data)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """User ka message agent ko bhejta hai aur reply wapas karta hai."""
    if not has_active_provider():
        raise HTTPException(
            status_code=500,
            detail="Koi LLM provider configured nahi hai. .env file me "
                   "GOOGLE_API_KEY (Gemini ke liye) ya OPENAI_API_KEY "
                   "(OpenAI-compatible endpoint ke liye) set karein.",
        )
    try:
        reply = await sessions.send_message(req.session_id, req.message)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session nahi mila. Page reload karein.")
    except Exception as exc:  # surface a readable error to the frontend
        raise HTTPException(status_code=500, detail=str(exc))

    files = sessions.list_files(req.session_id)
    return ChatResponse(reply=reply, files=files)


@app.post("/api/upload")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    """Code file upload karke session ke file_store me add karta hai."""
    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Sirf text/code files support hoti hain.")

    try:
        sessions.add_file(session_id, file.filename, content)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session nahi mila. Page reload karein.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"filename": file.filename, "status": "uploaded"}

@app.get("/api/sessions")
def list_sessions():
    """Tamam purani chat sessions ki list deta hai (sidebar me dikhane ke liye)."""
    return sessions.chat_store.list_sessions()

@app.get("/api/files/{session_id}")
def get_files(session_id: str):
    """Session ki tamam files (naam + content) return karta hai."""
    try:
        return sessions.list_files(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session nahi mila.")
    
@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """Ek session ko hamesha ke liye delete karta hai (history + files + RAG index)."""
    sessions.delete_session(session_id)
    return {"status": "deleted"}


@app.get("/api/files/{session_id}/{filename}")
def download_file(session_id: str, filename: str):
    """Ek specific file ka content download/view ke liye deta hai."""
    try:
        files = sessions.list_files(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session nahi mila.")
    if filename not in files:
        raise HTTPException(status_code=404, detail="File nahi mili.")
    return {"filename": filename, "content": files[filename]}


# ---------- Frontend (static files) ----------
# Isay sab se aakhir me mount karte hain taky /api/* routes pehle match ho jayein.

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
