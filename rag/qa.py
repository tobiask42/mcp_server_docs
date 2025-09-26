from typing import Sequence, Tuple
from definitions.custom_types import CtxItem
from definitions.custom_enums import CtxKeys
from vector_database.query_chroma import query_db
from rag.postprocess import postprocess_results
from rag.llm_ollama import call_llm_ollama
from config.settings import AppSettings, get_settings

custom_settings: AppSettings = get_settings()


def build_user_prompt(question: str, ctx_items: Sequence[CtxItem]) -> str:
    if not ctx_items:
        return (
            f"Question:\n{question}\n\n"
            f"{custom_settings.NO_CONTEXT_PROMPT}"
        )

    blocks: list[str] = []
    for i, item in enumerate(ctx_items, start=1):
        header_parts = [item[CtxKeys.TITLE.value], item[CtxKeys.HEADING.value], item[CtxKeys.SECTION.value]]
        header = " - ".join(p for p in header_parts if p) or "Source"

        quote = item["doc"].strip()
        blocks.append(f"[{i}] {header}\n{quote}\n(URL: {item['url']})")

    context = "\n\n".join(blocks)
    return (
        f"Question:\n{question}\n\n"
        f"Context:\n{context}\n\n"
        f"{custom_settings.CONTEXT_PROMPT}"
    )


def answer_question(question: str,) -> Tuple[str, list[CtxItem]]:
    """
    Führt Retrieval -> Postprocessing -> LLM-Aufruf aus und gibt (Antwort, verwendete Kontexte) zurück.
    """
    raw = query_db(question)
    ctx_items: list[CtxItem] = postprocess_results(raw, question)
    user_prompt = build_user_prompt(question, ctx_items)
    answer: str = call_llm_ollama(user_prompt=user_prompt)
    unique_ctx_items:list[CtxItem] = deduplicate_urls(ctx_items)
    return answer, unique_ctx_items

def deduplicate_urls(ctx_items: list[CtxItem]) -> list[CtxItem]:
    seen_urls: set[str] = set()
    unique_ctx_items: list[CtxItem] = []
    for item in ctx_items:
        url = item[CtxKeys.URL.value]
        if url not in seen_urls:
            seen_urls.add(url)
            unique_ctx_items.append(item)
    return unique_ctx_items