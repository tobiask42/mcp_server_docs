from pathlib import Path
from scrapy.crawler import CrawlerProcess
from crawler.sitemap_crawler import DocsSpider
from loguru import logger
from content_processor.chunker import build_chunks
from vector_database.create_chromadb import ingest_chunks_to_chroma
from definitions.custom_enums import CtxKeys
from rag.qa import answer_question
from typing import Any
import sys, subprocess

# --- Blocking-Funktionen als Callables ---

def crawl_blocking(*, log_path: Path) -> None:
    # Scrapy strikt auf Datei und ohne STDOUT
    process = CrawlerProcess(settings={
        "LOG_ENABLED": True,
        "LOG_LEVEL": "INFO",
        "LOG_STDOUT": False,
        "LOG_FILE": str(log_path),   # <-- selbe Datei wie Job-Sink
    })
    # DocsSpider.crawl() baut selbst einen Process – also hier direkt laufen:
    try:
        process.crawl(DocsSpider)
        process.start()
    except Exception:
        raise

def chunk_blocking() -> None:
    logger.info("Chunking started")
    build_chunks()
    logger.info("Chunking finished")

def ingest_blocking() -> None:
    logger.info("Ingest started")
    ingest_chunks_to_chroma()
    logger.info("Ingest finished")

def ask_blocking(question: str) -> dict[str,Any]:
    logger.info(f"ASK(job): {question!r}")
    ans, used = answer_question(question=question)
    # kompaktes Quellenformat:
    sources: list[dict[str,Any]] = [{
        "url": it.get(CtxKeys.URL.value, ""),
        "title": it.get(CtxKeys.TITLE.value, ""),
        "heading": it.get(CtxKeys.HEADING.value, ""),
        "distance": float(it.get(CtxKeys.DISTANCE.value, 0.0)),
        "overlap": int(it.get(CtxKeys.OVERLAP.value, 0)),
    } for it in used]
    logger.info("ANSWER ready")
    return {"answer": ans, "sources": sources}

def pipeline_blocking(*,log_path:Path) -> None:
     # 1) Crawl als Subprozess – stdout/stderr in dasselbe Job-Log
    with log_path.open("a", encoding="utf-8", errors="ignore") as lf:
        rc = subprocess.call([sys.executable, "-u", "scraper_main.py"], stdout=lf, stderr=lf)
    if rc != 0:
        raise RuntimeError(f"crawl subprocess exit code {rc}")
    # 2) Chunking & Ingest
    chunk_blocking()
    ingest_blocking()