# job_manager.py
from __future__ import annotations

import uuid
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Optional, Dict

from loguru import logger


class JobManager:
    """
    Startet entweder:
      - eine Python-Funktion im ThreadPool (empfohlen für chunk/ingest/ask),
      - oder einen Subprozess (empfohlen für scrapy-crawl, Twisted-Reactor im Main-Thread).

    Pro Job wird ein eigenes Logfile geschrieben; Status und Ergebnis sind abfragbar.
    Die Worker-Funktion im Thread-Job sollte die Signatur `fn(*, log_path: Path) -> Any` unterstützen
    und darf ein Ergebnis zurückgeben, das unter jobs[jid]["result"] gespeichert wird.

    MCP-Hinweis:
      - Keine STDOUT-Ausgaben in Worker/Subprozessen – STDOUT ist für MCP reserviert.
      - Der JobManager fügt pro Job einen Loguru-Sink auf die Job-Logdatei hinzu und entfernt ihn am Ende.
    """

    def __init__(self, *, max_workers: int = 3, logs_dir: Path | None = None) -> None:
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self.logs_dir = (logs_dir or Path("./job_logs")).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ---------- intern ----------

    def _new_job(self, name: str, log_path: Path) -> str:
        jid = str(uuid.uuid4())
        with self._lock:
            self.jobs[jid] = {
                "id": jid,
                "name": name,
                "status": "queued",     # queued | running | success | error
                "log": str(log_path),
                "error": None,
                "pid": None,
                "cwd": str(Path.cwd()),
                "result": None,         # optionales Rückgabeobjekt der Thread-Worker-Funktion
            }
        return jid

    # ---------- public API ----------

    def submit(
        self,
        name: str,
        fn: Optional[Callable[..., Any]] = None,
        *,
        use_subprocess: bool = False,
        args: Optional[list[str]] = None,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Entweder `fn` im Thread ausführen ODER Subprozess mit `args` starten.

        - Thread-Job:
            submit("chunk", chunk_blocking)
            # chunk_blocking muss `(*, log_path: Path)` akzeptieren und darf returnen.

        - Subprozess-Job:
            submit("crawl", use_subprocess=True, args=[sys.executable, "-u", "scraper_main.py"])

        Rückgabe: job_id (str)
        """
        log_path = (self.logs_dir / f"job_{name}_{uuid.uuid4().hex[:8]}.log").resolve()
        sink_id = logger.add(str(log_path), level="INFO")
        jid = self._new_job(name, log_path)

        def run_thread():
            try:
                logger.info(f"[{jid}] START {name} (thread)")
                with self._lock:
                    self.jobs[jid]["status"] = "running"

                if fn is None:
                    raise ValueError("fn must be provided for thread jobs")

                # Konvention: Worker akzeptiert log_path als Keyword-Argument
                res = fn(log_path=log_path)
                with self._lock:
                    self.jobs[jid]["result"] = res
                    self.jobs[jid]["status"] = "success"

                logger.info(f"[{jid}] DONE {name}")
            except Exception as e:
                with self._lock:
                    self.jobs[jid]["status"] = "error"
                    self.jobs[jid]["error"] = repr(e)
                logger.exception(f"[{jid}] FAILED {name}: {e}")
            finally:
                logger.remove(sink_id)

        def run_subprocess():
            try:
                logger.info(f"[{jid}] START {name} (subprocess)")
                with self._lock:
                    self.jobs[jid]["status"] = "running"

                if not args:
                    raise ValueError("args must be provided for subprocess jobs")

                # STDOUT/STDERR in die Job-Logdatei umleiten
                with log_path.open("w", encoding="utf-8", errors="ignore") as lf:
                    proc = subprocess.Popen(
                        args,
                        stdout=lf,
                        stderr=lf,
                        cwd=str(cwd) if cwd else None,
                        env=env,   # None: erbt aktuelle ENV (EMAIL, SCRAPELIST, ...)
                        shell=False,
                    )
                    with self._lock:
                        self.jobs[jid]["pid"] = proc.pid
                    rc = proc.wait()

                if rc == 0:
                    with self._lock:
                        self.jobs[jid]["status"] = "success"
                    logger.info(f"[{jid}] DONE {name}")
                else:
                    raise RuntimeError(f"Subprocess exit code {rc}")
            except Exception as e:
                with self._lock:
                    self.jobs[jid]["status"] = "error"
                    self.jobs[jid]["error"] = repr(e)
                logger.exception(f"[{jid}] FAILED {name}: {e}")
            finally:
                logger.remove(sink_id)

        if use_subprocess:
            self.executor.submit(run_subprocess)
        else:
            self.executor.submit(run_thread)

        return jid

    def status(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            meta = self.jobs.get(job_id)
            return meta.copy() if meta else {"status": "unknown", "error": "job not found"}

    def result(self, job_id: str) -> Dict[str, Any]:
        """
        Liefert den aktuellen Status plus ggf. Ergebnis/Fehler:
          {"status": "running|success|error|queued", "result": {...} | None, "error": str | None}
        """
        with self._lock:
            meta = self.jobs.get(job_id)
        if not meta:
            return {"status": "unknown", "error": "job not found"}
        return {
            "status": meta["status"],
            "result": meta.get("result"),
            "error": meta.get("error"),
        }

    def log_tail(self, job_id: str, lines: int = 200) -> Dict[str, Any]:
        with self._lock:
            meta = self.jobs.get(job_id)
        if not meta:
            return {"error": "job not found"}
        p = Path(meta["log"])
        if not p.exists():
            return {"log": "", "note": "log not yet created"}
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            tail = text.splitlines(True)[-max(1, lines):]
            return {"log": "".join(tail)}
        except Exception as e:
            return {"error": repr(e)}

    def get_log_path(self, job_id: str) -> Optional[Path]:
        with self._lock:
            meta = self.jobs.get(job_id)
        if not meta:
            return None
        return Path(meta["log"])

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            # Logpfad nicht mitschicken (kann groß sein); bei Bedarf separat abfragen
            return [
                {
                    "id": jid,
                    "name": meta.get("name"),
                    "status": meta.get("status"),
                    "pid": meta.get("pid"),
                    "cwd": meta.get("cwd"),
                    "error": meta.get("error"),
                }
                for jid, meta in self.jobs.items()
            ]
