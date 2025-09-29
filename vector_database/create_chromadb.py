# the code structure and docstrings were improved through AI generation
import json
import shutil
from pathlib import Path
from typing import Iterator, Any
from math import ceil

from chromadb import PersistentClient
from chromadb.api import ClientAPI
from loguru import logger
from typing import Any

from definitions.custom_enums import Names, ChunkKeys
from definitions import constants
from definitions.errors import ChromaError
from helpers.utils import count_lines

from config.settings import get_settings, AppSettings

custom_settings: AppSettings = get_settings()

def get_base_and_dirs() -> tuple[Path, Path, Path]:
    """
    Liefert:
      - base_dir: Projektwurzel
      - chunks_dir: Ordner mit .jsonl-Chunks
      - database_path: Pfad zum ChromaDB-Datenordner
    """
    base_dir = Path(__file__).resolve().parents[1]
    chunks_dir = base_dir / constants.CONTENT_PROCESSOR / constants.CHUNK_FOLDER
    database_path = base_dir / constants.VECTOR_DATABASE / constants.VECTOR_DATABASE_DATA

    if not chunks_dir.exists():
        raise FileNotFoundError(f"Chunks-folder is missing: {chunks_dir} (CWD={Path.cwd()})")

    return base_dir, chunks_dir, database_path


def get_latest_chunk_file(chunks_dir: Path) -> Path:
    """Ermittelt die neueste .jsonl-Datei im Chunks-Ordner."""
    files = sorted(chunks_dir.glob(Names.CHUNK))
    if not files:
        raise FileNotFoundError(f"No chunk files found in: {chunks_dir}")
    latest = files[-1]
    logger.info(f"Filepath: {latest}")
    return latest


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Zeilenweise JSONL lesen (robust gegen BOM und leere Zeilen)."""
    with path.open("r", encoding="utf-8") as jsonl_file:
        for raw_line in jsonl_file:
            line = raw_line.strip()
            if not line:
                continue
            if line[0] == "\ufeff":
                line = line.lstrip("\ufeff")  # BOM-Schutz
            try:
                yield json.loads(line)
            except json.JSONDecodeError as jde:
                logger.exception(jde)
                continue


def init_chroma_client(database_path: Path) -> ClientAPI:
    """Initialisiert den persistenten Chroma-Client."""
    client = PersistentClient(path=database_path)
    logger.info("Launched Chroma Client")
    return client


def get_collection(client: ClientAPI, name: str) -> Any:
    """Erstellt/öffnet die Zielsammlung."""
    collection = client.get_or_create_collection(name=name)
    logger.info("Created Chroma collection")
    return collection

def create_metadata(rec: dict[str, Any]) -> dict[str, Any]:
    def s(x:Any) -> str: return "" if x is None else str(x)
    def i(x:Any):
        try: return int(x)
        except Exception: return 0

    return {
        "url": s(rec.get("url")),
        "title": s(rec.get("title")),
        "chunk_index": i(rec.get("chunk_index")),
        "n_chars": i(rec.get("n_chars")),
        "section": s(rec.get("section")),
        "anchor": s(rec.get("anchor")),
        "heading": s(rec.get("heading")),
        "heading_path": s(rec.get("heading_path")),
        "canonical_url": s(rec.get("canonical_url")),
    }



def add_records_in_batches(filepath: Path, collection: Any, batch_size: int) -> None:
    """
    Liest Datensätze aus JSONL und fügt sie in Batches der Chroma-Sammlung hinzu.
    Erwartet Felder:
      - ChunkKeys.ID
      - ChunkKeys.TEXT
    """
    total_lines: int = count_lines(filepath)
    total_chunks: int = ceil(total_lines / batch_size)

    ids_part: list[Any] = []
    texts_part: list[Any] = []
    metadata_part: list[Any] = []
    chunk_counter: int = 0

    for line_counter, rec in enumerate(iter_jsonl(filepath), start=1):
        ids_part.append(rec.get(ChunkKeys.ID))
        texts_part.append(rec.get(ChunkKeys.TEXT))
        metadata_part.append(create_metadata(rec))
        if line_counter % batch_size == 0:
            chunk_counter += 1
            logger.info(f"Created chunk for collection (size: {len(texts_part)})")
            collection.add(ids=ids_part, documents=texts_part, metadatas=metadata_part)
            logger.info(f"Added chunk {chunk_counter}/{total_chunks} to collection")
            ids_part.clear()
            texts_part.clear()
            metadata_part.clear()

    # Restliche Elemente hinzufügen
    if ids_part or texts_part:
        chunk_counter += 1
        logger.info(f"Created chunk for collection (size: {len(texts_part)})")
        collection.add(ids=ids_part, documents=texts_part, metadatas=metadata_part)
        logger.info(f"Added chunk {chunk_counter}/{total_chunks} to collection")

    logger.info("Filled Chroma collection")


def ingest_chunks_to_chroma() -> None:
    """
    Verhalten:
      1) Löschen von alter Datenbank, falls sie existiert
      1) Auflösung der relevanten Pfade
      2) Neueste Chunk-Datei finden
      3) Chroma initialisieren und Collection öffnen/erstellen
      4) JSONL in Batches hinzufügen
    """
    _, chunks_dir, database_path = get_base_and_dirs()
    if database_path.exists() and custom_settings.CHROMA_REMOVE_OLD:
        logger.warning("Found vector database. Removing...")
        shutil.rmtree(database_path)
        logger.info("Successfully removed old database")
    elif database_path.exists():
        logger.error("Found vector database. Keeping existing data. Aborting ingestion.")
        raise ChromaError("Vector database already exists. Set CHROMA_REMOVE_OLD to True to overwrite.")
    filepath = get_latest_chunk_file(chunks_dir)
    client = init_chroma_client(database_path)
    collection = get_collection(client, name=Names.VECTOR_DATABASE_COLLECTION)
    add_records_in_batches(
        filepath=filepath,
        collection=collection,
        batch_size=custom_settings.CHROMA_BATCH_SIZE,
    )
