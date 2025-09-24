import re
from typing import Any, DefaultDict
from definitions.custom_enums import ChromaQueryKeys, ChunkKeys, CtxKeys
from definitions.custom_types import CtxItem
from config.settings import AppSettings, get_settings

custom_settings: AppSettings = get_settings()

def _keyword_overlap_score(query: str, doc: str) -> int:
    q_terms = set(re.findall(r"\w+", query.lower()))
    d_terms = set(re.findall(r"\w+", doc.lower()))
    return len(q_terms & d_terms)
def postprocess_results(
        raw: dict[str, Any],
        query: str,
        max_per_url: int = custom_settings.RAG_MAX_CHUNKS_PER_URL,
        max_ctx_chars: int = custom_settings.RAG_MAX_CONTEXT_CHARS
) -> list[CtxItem]:
    docs  = raw.get(ChromaQueryKeys.DOCS,  [[]])[0]
    metas = raw.get(ChromaQueryKeys.METAS, [[]])[0]
    dists = raw.get(ChromaQueryKeys.DISTS, [[]])[0]

    items: list[CtxItem] = []

    for doc, meta, dist in zip(docs, metas, dists):
        canon = (meta.get(ChunkKeys.CANONICAL_URL) or "").strip()
        url_  = (meta.get(ChunkKeys.URL) or "").strip()
        url   = canon or url_ or "unknown"
        items.append({
            CtxKeys.DOC.value: doc or "",
            CtxKeys.URL.value: url,
            CtxKeys.TITLE.value: meta.get(ChunkKeys.TITLE) or "",
            CtxKeys.SECTION.value: meta.get(ChunkKeys.SECTION) or "",
            CtxKeys.HEADING.value: meta.get(ChunkKeys.HEADING) or "",
            CtxKeys.HEADING_PATH.value: meta.get(ChunkKeys.HEADING_PATH) or "",
            CtxKeys.INDEX.value: meta.get(ChunkKeys.INDEX),
            CtxKeys.DISTANCE.value: float(dist),
            CtxKeys.OVERLAP.value: _keyword_overlap_score(query, doc or ""),
            CtxKeys.N_CHARS.value: meta.get(ChunkKeys.NCHARS) or len(doc or ""),
        })

    # --- ab hier NACH der Schleife ---
    from collections import defaultdict
    groups: DefaultDict[str, list[CtxItem]] = defaultdict(list)
    for x in items:
        groups[x[CtxKeys.URL.value]].append(x)

    selected: list[CtxItem] = []
    for url, grp in groups.items():
        # Achtung: CtxKeys.INDEX kann None sein -> als Fallback groß setzen
        grp.sort(key=lambda x: (
            -x[CtxKeys.OVERLAP.value],
             x[CtxKeys.DISTANCE.value],
             x[CtxKeys.INDEX.value] if x[CtxKeys.INDEX.value] is not None else 10**12
        ))
        selected.extend(grp[:max_per_url])

    # Globales Ranking
    selected.sort(key=lambda x: (x[CtxKeys.DISTANCE.value], -x[CtxKeys.OVERLAP.value]))

    # Kontext begrenzen
    ctx: list[CtxItem] = []
    acc = 0
    for x in selected:
        snippet = (x[CtxKeys.DOC.value] or "").strip()
        if not snippet:
            continue
        if acc + len(snippet) > max_ctx_chars:
            remain = max_ctx_chars - acc
            if remain <= 0:
                break
            snippet = snippet[:remain]
        acc += len(snippet)
        ctx.append({**x, CtxKeys.DOC.value: snippet})
        if acc >= max_ctx_chars:
            break

    return ctx
