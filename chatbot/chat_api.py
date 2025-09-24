from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio

# Wir nutzen deine MCP-Tools / JobManager direkt
# Wichtig: relativer Importpfad von deinem Projekt-Root aus
from server.mcp_server import jobman, ask_job  # ask_job ist async und gibt {"job_id": "..."} zurück

app = FastAPI(title="Docs RAG Chat")


# Absoluter Pfad zu /chatbot/static
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    # hilft beim Debuggen, falls Verzeichnisname abweicht
    raise RuntimeError(f"Static dir not found: {STATIC_DIR}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Liefere die Chat-Seite
@app.get("/", response_class=HTMLResponse)
def home():
    html_path = Path(__file__).with_name("chatpage.html")
    return html_path.read_text(encoding="utf-8")

class AskReq(BaseModel):
    question: str
    timeout_s: int = 90

@app.post("/chat/ask")
async def chat_ask(request: AskReq):
    # 1) Job starten (MCP-Tool direkt als Funktion aufrufen)
    response = await ask_job(question=request.question)
    job_id = response["job_id"]

    # 2) Polling auf Ergebnis
    deadline = asyncio.get_event_loop().time() + request.timeout_s
    while True:
        meta = jobman.result(job_id)  # {"status": "...", "result": {...}|None, "error": ...}
        if meta["status"] == "success" and meta.get("result"):
            return meta["result"]            # -> {"answer": "...", "sources": [...]}
        if meta["status"] == "error":
            raise HTTPException(500, detail=meta.get("error", "error"))
        if asyncio.get_event_loop().time() > deadline:
            raise HTTPException(504, detail="timeout")
        await asyncio.sleep(0.5)
