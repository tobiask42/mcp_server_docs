from typing import Sequence, Tuple
from definitions.custom_types import CtxItem
from definitions.custom_enums import CtxKeys
from vector_database.query_chroma import query_db
from rag.postprocess import postprocess_results
from definitions.constants import SYSTEM_PROMPT
from rag.llm_ollama import call_llm_ollama
from config.settings import AppSettings, get_settings

custom_settings: AppSettings = get_settings()


def build_user_prompt(question: str, ctx_items: Sequence[CtxItem]) -> str:
    if not ctx_items:
        return (
            f"Question:\n{question}\n\n"
            "Context:\nNo relevant context found.\n\n"
            "Answer the question strictly based on the context above."
        )

    blocks: list[str] = []
    for i, it in enumerate(ctx_items, start=1):
        header_parts = [it[CtxKeys.TITLE.value], it[CtxKeys.HEADING.value], it[CtxKeys.SECTION.value]]
        header = " - ".join(p for p in header_parts if p) or "Source"

        quote = it["doc"].strip()
        blocks.append(f"[{i}] {header}\n{quote}\n(URL: {it['url']})")

    context = "\n\n".join(blocks)
    return (
        f"Question:\n{question}\n\n"
        f"Context:\n{context}\n\n"
        "Answer the question strictly based on the context above."
    )


def answer_question(
    question: str,
    model: str = custom_settings.OLLAMA_MODEL,
    max_ctx_chars: int = custom_settings.RAG_MAX_CONTEXT_CHARS,
    max_per_url: int = custom_settings.RAG_MAX_CHUNKS_PER_URL,
    num_ctx: int = custom_settings.OLLAMA_CONTEXT_WINDOW_TOKENS,
    max_tokens: int = custom_settings.OLLAMA_MAX_TOKENS,
) -> Tuple[str, list[CtxItem]]:
    """
    Führt Retrieval -> Postprocessing -> LLM-Aufruf aus und gibt (Antwort, verwendete Kontexte) zurück.
    """
    raw = query_db(question)
    ctx_items: list[CtxItem] = postprocess_results(
        raw,
        question,
        max_ctx_chars=max_ctx_chars,
        max_per_url=max_per_url,
    )
    user_prompt = build_user_prompt(question, ctx_items)
    answer: str = call_llm_ollama(
        user_prompt=user_prompt,
        system_prompt=SYSTEM_PROMPT,
        model=model,
        temperature=custom_settings.OLLAMA_TEMPERATURE,
        num_ctx=num_ctx,
        max_tokens=max_tokens,
    )
    return answer, ctx_items
