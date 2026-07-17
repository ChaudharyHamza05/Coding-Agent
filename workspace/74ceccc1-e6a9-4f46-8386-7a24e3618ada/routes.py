"""
api/routes.py
-------------
All FastAPI route handlers.
Business logic lives in agents/ and services/ — routes are thin wrappers.
"""

import json
import tempfile
import os
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from markitdown import MarkItDown

from agents.agent  import detect_tools, run_tools, build_messages
from agents.memory import (
    save_conversation, load_all_conversations,
    delete_conversation, clear_all_memory,
)
from agents.tools  import wikipedia_search, search_memory, code_executor
from services.llm_service import get_llm
from services.rag_service  import (
    get_chroma_stats, ingest_text_to_chroma,
    extract_image_info,
    save_full_markdown, load_full_markdown, list_markdown_files,
)

router = APIRouter()


# ── Models Info ───────────────────────────────────────────────────────────────
@router.get("/models")
async def get_models():
    return {"models": {"llama-3.3-70b-versatile": "⚡ Llama 3.3 70B via Groq (Free)"}}


# ── Chat ──────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message:           str
    history:           List[dict]
    model:             str = "llama-3.3-70b-versatile"
    file_context:      Optional[str] = ""
    attached_filename: Optional[str] = ""   # exact name of file just uploaded in this turn
    auto_search:       bool = True


@router.post("/chat")
async def chat(req: ChatRequest):

    def generate():
        try:
            # 1. Detect & run tools
            tools_to_run = detect_tools(req.message, req.attached_filename or "")
            active_names = [t[0] for t in tools_to_run]

            if active_names:
                yield f"data: {json.dumps({'status': 'searching', 'tool': ', '.join(active_names)})}\n\n"

            tool_results = run_tools(tools_to_run)

            # 2. Build messages + call LLM
            messages = build_messages(
                req.message, req.history, tool_results, req.file_context or ""
            )
            llm      = get_llm()
            response = llm.invoke(messages)
            full     = response.content if hasattr(response, "content") else str(response)

            # 3. Stream to frontend
            yield f"data: {json.dumps({'chunk': full})}\n\n"
            yield f"data: {json.dumps({'done': True, 'full': full})}\n\n"

        except Exception as e:
            import traceback
            print("CHAT ERROR:", traceback.format_exc())
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Markitdown Helper ─────────────────────────────────────────────────────────
def convert_with_markitdown(data: bytes, suffix: str) -> str:
    """
    Save bytes to a temp file, convert with Markitdown, delete temp file.
    Works for PDF, DOCX, PPTX, XLSX, HTML.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        md     = MarkItDown()
        result = md.convert(tmp_path)
        return result.text_content or ""
    finally:
        os.unlink(tmp_path)  # always deleted even if conversion fails


# ── File Upload ───────────────────────────────────────────────────────────────
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    data  = await file.read()
    fname = file.filename
    ftype = file.content_type or ""

    # ── Image ──────────────────────────────────────────────────────────────────
    if ftype in ["image/png", "image/jpeg", "image/jpg"]:
        return extract_image_info(data, fname)

    # ── PDF — via Markitdown (preserves headings, tables, structure) ───────────
    elif ftype == "application/pdf":
        print(f"[UPLOAD] Processing PDF: {fname}")
        text = await convert_with_markitdown(data, ".pdf")
        print(f"[UPLOAD] Markitdown extracted {len(text)} chars from {fname}")
        save_full_markdown(fname, text)
        ingest_text_to_chroma(text, fname)
        return {
            "filename": fname,
            "type":     "pdf",
            "context":  f"FILE: {fname}\nFULL MARKDOWN CONTENT:\n{text}",
            "info":     f"{len(text):,} chars extracted",
        }

    # ── Word Document — via Markitdown ─────────────────────────────────────────
    elif "wordprocessingml" in ftype:
        text = await convert_with_markitdown(data, ".docx")
        save_full_markdown(fname, text)
        ingest_text_to_chroma(text, fname)
        return {
            "filename": fname,
            "type":     "docx",
            "context":  f"FILE: {fname}\nFULL MARKDOWN CONTENT:\n{text}",
            "info":     f"{len(text):,} chars extracted",
        }

    # ── PowerPoint — via Markitdown ────────────────────────────────────────────
    elif "presentationml" in ftype:
        text = await convert_with_markitdown(data, ".pptx")
        save_full_markdown(fname, text)
        ingest_text_to_chroma(text, fname)
        return {
            "filename": fname,
            "type":     "pptx",
            "context":  f"FILE: {fname}\nFULL MARKDOWN CONTENT:\n{text}",
            "info":     f"{len(text):,} chars extracted",
        }

    # ── Excel — via Markitdown ─────────────────────────────────────────────────
    elif "spreadsheetml" in ftype:
        text = await convert_with_markitdown(data, ".xlsx")
        save_full_markdown(fname, text)
        ingest_text_to_chroma(text, fname)
        return {
            "filename": fname,
            "type":     "xlsx",
            "context":  f"FILE: {fname}\nFULL MARKDOWN CONTENT:\n{text}",
            "info":     f"{len(text):,} chars extracted",
        }

    # ── HTML — via Markitdown ──────────────────────────────────────────────────
    elif ftype == "text/html":
        text = await convert_with_markitdown(data, ".html")
        save_full_markdown(fname, text)
        ingest_text_to_chroma(text, fname)
        return {
            "filename": fname,
            "type":     "html",
            "context":  f"FILE: {fname}\nFULL MARKDOWN CONTENT:\n{text}",
            "info":     f"{len(text):,} chars extracted",
        }

    # ── Plain Text / Code Files ────────────────────────────────────────────────
    else:
        text = data.decode("utf-8", errors="ignore")
        ingest_text_to_chroma(text, fname)
        return {
            "filename": fname,
            "type":     "text",
            "context":  f"File '{fname}' indexed. Ask me anything about it.",
            "info":     f"{len(text):,} chars indexed",
        }


# ── Wikipedia Search ──────────────────────────────────────────────────────────
@router.get("/search")
async def search(q: str):
    result  = wikipedia_search.invoke(q)
    context = f"\n\n[Wikipedia result for '{q}':\n{result[:1000]}]"
    return {"result": result, "context": context, "tool": "wikipedia_search"}


# ── Memory ────────────────────────────────────────────────────────────────────
@router.get("/memory")
async def get_memory():
    return {"conversations": load_all_conversations()}


class SaveMemoryRequest(BaseModel):
    title:    str
    messages: list

@router.post("/memory/save")
async def save_memory_route(req: SaveMemoryRequest):
    save_conversation(req.title, req.messages)
    return {"status": "saved"}

@router.get("/memory/search")
async def semantic_memory_search(q: str):
    result = search_memory.invoke(q)
    return {"result": result}

@router.delete("/memory/{title}")
async def delete_memory(title: str):
    delete_conversation(title)
    return {"status": "deleted"}

@router.delete("/memory")
async def clear_memory():
    clear_all_memory()
    return {"status": "cleared"}


# ── Code Executor ─────────────────────────────────────────────────────────────
class CodeRequest(BaseModel):
    code: str

@router.post("/code/run")
async def run_code(req: CodeRequest):
    result = code_executor.invoke(req.code)
    return {"result": result}


# ── ChromaDB Stats ────────────────────────────────────────────────────────────
@router.get("/chroma/stats")
async def chroma_stats():
    return get_chroma_stats()


# ── Full Markdown Retrieval (Option B) ────────────────────────────────────────
@router.get("/markdown/{filename}")
async def get_markdown(filename: str):
    text = load_full_markdown(filename)
    if not text:
        return {"error": f"No markdown found for '{filename}'. Please upload the file first."}
    return {"filename": filename, "markdown": text, "chars": len(text)}

@router.get("/markdown")
async def list_markdowns():
    files = list_markdown_files()
    return {"files": files, "count": len(files)}