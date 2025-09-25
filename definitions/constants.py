from typing import Final
from pathlib import Path


CONTENT_PROCESSOR:Final[str] = "content_processor"
CHUNK_FOLDER:Final[str] = "chunks"
CHUNK_DYNAMIC_NAME:Final[str] = "*_chunks.jsonl"
CHUNK_SUFFIX:Final[str] = "_chunks.jsonl"
CRAWLER_OUTPUT_DYNAMIC_NAME:Final[str] = "out_*.jsonl"
VECTOR_DATABASE:Final[str] = "vector_database"
VECTOR_DATABASE_DATA:Final[str] = "./chroma_data"
FEED_PATH: Final[Path] = Path("crawler") / "crawled_pages"
CHUNK_PATH: Final[Path] = Path("content_processor") / "chunks"

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent