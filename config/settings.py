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
    CHROMA_REMOVE_OLD: bool = False

    CHUNK_MAX_CHARS: int = 1000
    CHUNK_OVERLAP: int = 100

    CHROMA_N_RESULTS: int = 3

    SECTION_UNKNOWN: str = "unknown"
    SECTION_CATEGORIES: list[str] = ["tutorial", "advanced", "reference", "alternatives", "deployment", "benchmarks"]

    RAG_MAX_CONTEXT_CHARS: int = 9000
    RAG_MAX_CHUNKS_PER_URL: int = 3

    OLLAMA_MODEL: str = "mistral:7b-instruct"
    OLLAMA_TEMPERATURE: float = 0.1 # 0.0 = deterministic, 1.0 = creative
    OLLAMA_CONTEXT_WINDOW_TOKENS: int = 4096
    OLLAMA_MAX_TOKENS: int = 768

    OLLAMA_ENDPOINT: Annotated[
        HttpUrl,
        Field(default_factory=lambda: _http_url.validate_python("http://localhost:11434/api/chat"))
    ]
    OLLAMA_TIMEOUT_S: int = 120

    # This system prompt is AI generated
    SYSTEM_PROMPT: str = Field(
        "You are a precise assistant for question answering over technical documentation.\n"
        "Rules:\n"
        "- Only use the information contained in the provided context.\n"
        "- If the context does not contain the answer, respond: \"I cannot verify that.\"\n"
        "- Do not invent or assume information.\n"
        "- Be concise and factual.\n"
        "- If the context contains multiple relevant sections, synthesize them into a coherent answer.\n"
        "- If the context contains contradictory information, indicate the uncertainty in your answer.\n"
        "- Do NOT include source URLs in your answer. The system will display sources separately.",
        description="System prompt for the LLM"
    )

    NO_CONTEXT_PROMPT: str = Field(
                    "Context:\nNo relevant context found.\n\n"
            "Answer the question strictly based on the context above.",
        description="Prompt to use when no context is found")
    
    CONTEXT_PROMPT: str = Field(
                "Answer the question strictly based on the context above.",
        description="Prompt to use when no context is found")

    SPIDER_PRIORITY: str = "spider"

    SPIDER_AUTOTHROTTLE_ENABLED: bool = True
    SPIDER_DOWNLOAD_DELAY:float = 0.3
    SPIDER_CONCURRENT_REQUESTS:int = 8
    SPIDER_HTTPCACHE_ENABLED:bool = True

    CRAWLER_LOG_LEVEL: str = "INFO"


    API_KEY: str | None = None

    POLLING_INTERVAL_S: float = 0.5

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

# Singleton
@lru_cache
def get_settings() -> AppSettings:
    return AppSettings() # type: ignore