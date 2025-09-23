from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio

# Wir nutzen deine MCP-Tools / JobManager direkt
# Wichtig: relativer Importpfad von deinem Projekt-Root aus
from server.mcp_server import jobman, ask_job  # ask_job ist async und gibt {"job_id": "..."} zurück

app = FastAPI(title="Docs RAG Chat")

# Liefere die Chat-Seite
@app.get("/", response_class=HTMLResponse)
def home():
    html_path = Path(__file__).with_name("chatpage.html")
    return html_path.read_text(encoding="utf-8")

class AskReq(BaseModel):
    question: str
    model: str | None = None
    temperature: float | None = None
    num_ctx: int | None = None
    max_tokens: int | None = None
    max_ctx_chars: int | None = None
    max_per_url: int | None = None
    timeout_s: int = 90

@app.post("/chat/ask")
async def chat_ask(req: AskReq):
    # 1) Job starten (MCP-Tool direkt als Funktion aufrufen)
    res = await ask_job(
        question=req.question,
        model=req.model,
        temperature=req.temperature,
        num_ctx=req.num_ctx,
        max_tokens=req.max_tokens,
        max_ctx_chars=req.max_ctx_chars,
        max_per_url=req.max_per_url,
    )
    jid = res["job_id"]

    # 2) Polling auf Ergebnis
    deadline = asyncio.get_event_loop().time() + req.timeout_s
    while True:
        meta = jobman.result(jid)  # {"status": "...", "result": {...}|None, "error": ...}
        if meta["status"] == "success" and meta.get("result"):
            return meta["result"]            # -> {"answer": "...", "sources": [...]}
        if meta["status"] == "error":
            raise HTTPException(500, detail=meta.get("error", "error"))
        if asyncio.get_event_loop().time() > deadline:
            raise HTTPException(504, detail="timeout")
        await asyncio.sleep(0.5)
