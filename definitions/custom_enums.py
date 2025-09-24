from enum import IntEnum, StrEnum

# === Enums and Constants ===
class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1
    
class ChunkKeys(StrEnum):
    URL = "url"
    TITLE = "title"
    ID = "chunk_id"
    INDEX = "chunk_index"
    TEXT = "text"
    NCHARS = "n_chars"
    METADATA = "metadatas"
    ANCHOR = "anchor"
    HEADING = "heading"
    HEADING_PATH = "heading_path"
    SECTION = "section"
    CANONICAL_URL = "canonical_url"

class CrawlerOutputKeys(StrEnum):
    URL = "url"
    TITLE = "title"
    TEXT = "text"

class Names(StrEnum):
    VECTOR_DATABASE_COLLECTION = "docs"
    CHUNK = "*_chunks.jsonl"


class ChromaQueryKeys(StrEnum):
    DOCS = "documents"
    METAS = "metadatas"
    DISTS = "distances"

class CtxKeys(StrEnum):
    DOC = "doc"
    URL = "url"
    TITLE = "title"
    SECTION = "section"
    HEADING = "heading"
    HEADING_PATH = "heading_path"
    OVERLAP = "overlap"
    DISTANCE = "distance"
    INDEX = "chunk_index"
    N_CHARS = "n_chars"