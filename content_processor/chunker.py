# The processing logic was programmed with AI support
import json, re, hashlib
from pathlib import Path
from typing import Dict, Any, List, Final, Tuple  # <- Tuple ergänzt
from definitions import constants
from loguru import logger
from config.settings import get_settings
custom_settings = get_settings()

MAX_CHARS: Final[int] = custom_settings.CHUNK_MAX_CHARS
OVERLAP_CHARS: Final[int] = custom_settings.CHUNK_OVERLAP

DEFAULT_IN_DIR = Path(constants.FEED_PATH)
DEFAULT_OUT_DIR = Path(constants.CHUNK_PATH)

# --- Header-Kommentar & Metadaten ---

_HEADER_META_RE = re.compile(r"^\s*<!--\s*(.*?)\s*-->\s*", flags=re.DOTALL)
_KV_RE = re.compile(r"\b([A-Z_]+):\s*([^\|]+)")
_CLEAN_TAIL_RE = re.compile(r"\s*(?:¶\s*)?(?:\{#.*?\})\s*$")

def _clean_heading_for_meta(h: str) -> str:
    return _CLEAN_TAIL_RE.sub("", h or "").strip()

def _slugify(text: str) -> str:
    s = re.sub(r"\s+", "-", (text or "").strip().lower())
    s = re.sub(r"[^a-z0-9_.\-:]", "", s)
    return s.strip("-")

def _extract_page_meta(md: str, url_fallback: str) -> tuple[str, str, str]:
    """
    Erwartet am Anfang optional:
      <!-- CANONICAL_URL: ... | SECTION: tutorial -->
    Rückgabe: (clean_md, canonical_url, section)
    """
    canonical_url = url_fallback or ""
    section = "unknown"
    m = _HEADER_META_RE.match(md)
    if m:
        blob = m.group(1)
        for k, v in _KV_RE.findall(blob):
            val = (v or "").strip()
            if k == "CANONICAL_URL" and val:
                canonical_url = val
            elif k == "SECTION" and val:
                section = val
        md = md[m.end():]
    if section == custom_settings.SECTION_UNKNOWN:
        path = (url_fallback or "").lower()
        for key in tuple(custom_settings.SECTION_CATEGORIES):
            if f"/{key}/" in path:
                section = key
                break
    return md, canonical_url, section

# --- H2–H6 inkl. optionalem {#anchor} erkennen ---
# WICHTIG: Anker erlauben jetzt ., _, -, :
_HEADING_RE = re.compile(r"(?m)^(#{2,6})\s+(.+?)(?:\s*\{#([A-Za-z0-9_.\-:]+)\})?\s*$")

def _iter_sections(md: str) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    matches = list(_HEADING_RE.finditer(md))
    end_pos = len(md)

    if not matches:
        sections.append({"level": 1, "heading": "", "anchor": "", "body": md.strip()})
        return sections

    # Kopf vor erster H2–H6
    head_text = md[:matches[0].start()].strip()
    if head_text:
        sections.append({"level": 1, "heading": "", "anchor": "", "body": head_text})

    for i, m in enumerate(matches):
        level = len(m.group(1))
        heading = _clean_heading_for_meta((m.group(2) or "").strip())
        anchor = (m.group(3) or "").strip()
        if not anchor and heading:
            anchor = _slugify(heading)  # Fallback-Anchor
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else end_pos
        body = md[body_start:body_end].strip()
        sections.append({"level": level, "heading": heading, "anchor": anchor, "body": body})
    return sections

def _build_heading_paths(sections: List[Dict[str, Any]]) -> None:
    stack: List[Tuple[int, str]] = []
    for sec in sections:
        lvl = sec.get("level", 1)
        h = sec.get("heading", "")
        stack = [x for x in stack if x[0] < lvl]
        if h:
            stack.append((lvl, h))
        # Pfad säubern (keine ¶/{#...})
        path = " > ".join(_clean_heading_for_meta(txt) for _, txt in stack if txt)
        sec["heading_path"] = path

def _pack_with_overlap(text: str, max_chars: int, overlap: int) -> List[str]:
    paras = re.split(r"\n{2,}", text)
    out: List[str] = []
    buf = ""
    for p in paras:
        candidate = (buf + "\n\n" + p).strip() if buf else p
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                out.append(buf)
                tail = buf[-overlap:] if overlap > 0 else ""
                buf = (tail + "\n\n" + p)[-max_chars:]
            else:
                s = 0
                step = max_chars - overlap if overlap < max_chars else max_chars
                while s < len(p):
                    out.append(p[s : s + max_chars])
                    s += step
                buf = ""
    if buf:
        out.append(buf)
    return [c.strip() for c in out if c.strip()]

def _page_to_chunks(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = (rec.get("url") or "").strip()
    title = (rec.get("title") or "").strip()
    raw_text = rec.get("text") or ""

    # 1) Header-Metadaten + Fallbacks
    md, canonical_url, section = _extract_page_meta(raw_text, url)

    # 2) Sections + Heading-Pfade
    sections = _iter_sections(md)
    _build_heading_paths(sections)

    chunks: List[Dict[str, Any]] = []
    local_ord = 0

    for sec in sections:
        heading = (sec.get("heading") or "").strip()
        anchor = (sec.get("anchor") or "").strip()
        heading_path = (sec.get("heading_path") or "").strip()
        body = (sec.get("body") or "").strip()

        # Heading dem ersten Stück beilegen (einfach & robust)
        base_text = (f"{heading}\n\n{body}".strip() if heading else body)

        for piece in _pack_with_overlap(base_text, MAX_CHARS, OVERLAP_CHARS):
            basis = f"{url}|{anchor or heading}|{local_ord}"
            cid = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]

            chunks.append({
                "url": url,
                "title": title,
                "chunk_id": cid,
                "chunk_index": local_ord,
                "text": piece,
                "n_chars": len(piece),
                "anchor": anchor,
                "heading": heading,
                "heading_path": heading_path,
                "section": section,
                "canonical_url": canonical_url,
            })
            local_ord += 1

    return chunks

def _latest_jsonl(in_dir: Path) -> Path | None:
    files = sorted(in_dir.glob(constants.CRAWLER_OUTPUT_DYNAMIC_NAME))
    return files[-1] if files else None

def build_chunks(in_path: Path | None = None, out_dir: Path | None = None) -> Path:
    in_dir = DEFAULT_IN_DIR
    out_dir = (out_dir or DEFAULT_OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    src = in_path or _latest_jsonl(in_dir)
    if not src:
        raise FileNotFoundError(f"No input file found in {in_dir}")

    out_path = out_dir / (src.stem + constants.CHUNK_SUFFIX)
    logger.info(f"Chunking: {src} -> {out_path}")

    with src.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            page = json.loads(line)
            for ch in _page_to_chunks(page):
                fout.write(json.dumps(ch, ensure_ascii=False) + "\n")

    logger.info(f"Finished chunking: {out_path}")
    return out_path
