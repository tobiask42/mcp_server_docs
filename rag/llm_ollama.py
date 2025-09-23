from definitions.errors import LLMError
from config.settings import AppSettings, get_settings
from pydantic import HttpUrl

import requests
from typing import Any

custom_settings: AppSettings = get_settings()

def call_llm_ollama(
    user_prompt: str,
    system_prompt: str,
    *,
    model: str = custom_settings.OLLAMA_MODEL,
    temperature: float = custom_settings.OLLAMA_TEMPERATURE,
    num_ctx: int = custom_settings.OLLAMA_CONTEXT_WINDOW_TOKENS,
    max_tokens: int = custom_settings.OLLAMA_MAX_TOKENS,
    endpoint: HttpUrl = custom_settings.OLLAMA_ENDPOINT,
    timeout_s: int = custom_settings.OLLAMA_TIMEOUT_S,
) -> str:
    """Call Ollama's local /api/chat endpoint."""
    payload: dict[str,Any]= {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": max_tokens,
        },
    }
    endpoint_str: str = str(endpoint)
    try:
        r = requests.post(endpoint_str, json=payload, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {}).get("content", "")
        if not msg:
            raise LLMError(f"Ollama returned no content: {data}")
        return msg.strip()
    except requests.RequestException as e:
        raise LLMError(f"Ollama request failed: {e}") from e