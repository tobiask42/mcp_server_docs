from mcp.server.fastmcp import FastMCP
from loguru import logger
from server.job_manager import JobManager
from server.blocking_tasks import chunk_blocking, ingest_blocking, ask_blocking
from typing import Any
import sys
from pathlib import Path
from config.settings import get_settings, AppSettings

custom_settings: AppSettings = get_settings()


# Loguru nur Datei und WARN auf STDERR
logger.remove()
logger.add("mcp_server.log", rotation="10 MB", level="INFO", backtrace=False, diagnose=False)
logger.add(sys.stderr, level="WARNING", backtrace=False, diagnose=False)

mcp = FastMCP("Doc RAG")
jobman = JobManager(max_workers=3, logs_dir=Path("./job_logs"))

# --- MCP Tools (nicht blockierend) ---
@mcp.tool()
async def start_crawl() -> dict[str, Any]:
    # Subprozess: ruft bestehendes CLI auf (keine stdout-Ausgabe dort)
    jid = jobman.submit(
            "crawl",
            use_subprocess=True,
            args=[sys.executable, "-u", "scraper_main.py"],  # -u = unbuffered (ok, gehen in Logdatei)
            cwd=Path("."),
        )
    return {"job_id": jid}


@mcp.tool()
async def start_chunk() -> dict[str,Any]:
    """Startet Chunking im Hintergrund. Gibt job_id zurück."""
    jid = jobman.submit("chunk", chunk_blocking)
    return {"job_id": jid}

@mcp.tool()
async def start_ingest() -> dict[str,Any]:
    """Startet Ingest im Hintergrund. Gibt job_id zurück."""
    jid = jobman.submit("ingest", ingest_blocking)
    return {"job_id": jid}


@mcp.tool()
async def start_pipeline() -> dict[str,Any]:
    # Einfach: mehrere Jobs nacheinander in EINEM Thread-Job
    def pipeline(*, log_path: Path):
        chunk_blocking()  # wenn Crawl separat als eigener Job läuft
        ingest_blocking()
    jid = jobman.submit("pipeline", pipeline)
    return {"job_id": jid}


@mcp.tool()
async def job_status(job_id: str) -> dict[str,Any]:
    """Status eines Jobs: queued | running | success | error."""
    return jobman.status(job_id)

@mcp.tool()
async def job_log_tail(job_id: str, lines: int = 200) -> dict[str,Any]:
    """Letzte Logzeilen eines Jobs (aus dem Job-Logfile)."""
    return jobman.log_tail(job_id, lines=lines)


@mcp.tool()
async def list_jobs() -> list[dict[str,Any]]:
    return jobman.list_jobs()



@mcp.tool()
async def job_result(job_id: str) -> dict[str,Any]:
    """Gibt Ergebnis (answer + sources) zurück, sobald Status=success."""
    return jobman.result(job_id)

@mcp.tool()
async def ask_job(
    question: str,
    model: str | None = None,
    temperature: float | None = None,
    num_ctx: int | None = None,
    max_tokens: int | None = None,
    max_ctx_chars: int | None = None,
    max_per_url: int | None = None,
) -> dict[str,str]:
    """Startet Q&A als Hintergrund-Job und gibt job_id zurück."""
    overrides = dict(
        model=model or custom_settings.OLLAMA_MODEL,
        temperature=temperature if temperature is not None else custom_settings.OLLAMA_TEMPERATURE,
        num_ctx=num_ctx or custom_settings.OLLAMA_CONTEXT_WINDOW_TOKENS,
        max_tokens=max_tokens or custom_settings.OLLAMA_MAX_TOKENS,
        max_ctx_chars=max_ctx_chars or custom_settings.RAG_MAX_CONTEXT_CHARS,
        max_per_url=max_per_url or custom_settings.RAG_MAX_CHUNKS_PER_URL,
    )
    def runner(*, log_path: Path):
        return ask_blocking(log_path=log_path, question=question, overrides=overrides)
    jid = jobman.submit("ask", runner)
    return {"job_id": jid}