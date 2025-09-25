from __future__ import annotations
from typing import Annotated
from pydantic import Field, HttpUrl, TypeAdapter, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

_http_url = TypeAdapter(HttpUrl)

class AppSettings(BaseSettings):
    SCRAPE_URL: Annotated[HttpUrl, Field(..., description="Required")]
    # Pflicht: muss per ENV/.env gesetzt werden, Format wird geprüft
    EMAIL: EmailStr = Field(..., description="Kontaktadresse für den Crawler (User-Agent)")

    CHROMA_BATCH_SIZE: int = 1000
    CHROMA_REMOVE_OLD: bool = True

    CHUNK_MAX_CHARS: int = 1000
    CHUNK_OVERLAP: int = 100

    SECTION_UNKNOWN: str = "unknown"
    SECTION_CATEGORIES: list[str] = ["tutorial", "advanced", "reference", "alternatives", "deployment", "benchmarks"]

    RAG_MAX_CONTEXT_CHARS: int = 5000
    RAG_MAX_CHUNKS_PER_URL: int = 1

    OLLAMA_MODEL: str = "mistral:7b-instruct"
    OLLAMA_TEMPERATURE: float = 0.0
    OLLAMA_CONTEXT_WINDOW_TOKENS: int = 4096
    OLLAMA_MAX_TOKENS: int = 384

    OLLAMA_ENDPOINT: Annotated[
        HttpUrl,
        Field(default_factory=lambda: _http_url.validate_python("http://localhost:11434/api/chat"))
    ]
    OLLAMA_TIMEOUT_S: int = 120

    SPIDER_PRIORITY: str = "spider"

    SPIDER_AUTOTHROTTLE_ENABLED: bool = True
    SPIDER_DOWNLOAD_DELAY:float = 0.3
    SPIDER_CONCURRENT_REQUESTS:int = 8
    SPIDER_HTTPCACHE_ENABLED:bool = True

    CRAWLER_LOG_LEVEL: str = "INFO"


    API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

# Singleton
@lru_cache
def get_settings() -> AppSettings:
    return AppSettings() # type: ignore