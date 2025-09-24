from loguru import logger
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from urllib.parse import urlparse
import re
from config.settings import get_settings

custom_settings = get_settings()

# ---------- Hilfsfunktionen ----------

def _clean_heading_text(t: str) -> str:
    """Entfernt sichtbare Ankerreste (¶, {#...}) am Headingende."""
    t = re.sub(r"\s*\{#.*?\}\s*$", "", t or "")
    t = re.sub(r"\s*¶\s*$", "", t)
    return t.strip()

def _slugify(text: str) -> str:
    s = re.sub(r"\s+", "-", (text or "").strip().lower())
    s = re.sub(r"[^a-z0-9\-]", "", s)
    return s

def _infer_section_from_url(url: str | None) -> str:
    if not url:
        return custom_settings.SECTION_UNKNOWN
    path = urlparse(url).path.lower()
    for key in tuple(custom_settings.SECTION_CATEGORIES):
        if f"/{key}/" in path:
            return key
    return custom_settings.SECTION_UNKNOWN


# ---------- Hauptfunktion ----------

def html_to_text_string(html: str, *, source_url: str | None = None) -> str:
    """
    Wandelt HTML der FastAPI-Doku in „markdown-nahen“ Text um, mit:
      - Header-Kommentar: CANONICAL_URL, SECTION
      - ATX-Headings inkl. {#anchor}
      - Inline-Code in `backticks`
      - <pre><code> zu fenced code
      - Tabellen als Markdown-Pipes
      - aggressiv entfernte Boilerplate
    """
    log = logger.bind(module="parser", source_url=source_url)
    soup = BeautifulSoup(html or "", "lxml")

    # 1) Canonical + Section (für Metadaten im Header-Kommentar)
    canonical_url = (soup.find("link", rel="canonical") or {}).get("href") or (source_url or "") # type: ignore
    section = _infer_section_from_url(source_url)
    header_comment = f"<!-- CANONICAL_URL: {canonical_url} | SECTION: {section} -->"

    # 2) Boilerplate/Deko entfernen (Navigation, Footer, Suchleisten, etc.)
    for sel in [
        "nav","header","footer","aside","script","style","noscript",
        "div.sidebar","div.toctree","div.md-sidebar","div.related",
        "div.breadcrumbs","div.navbar","div.md-nav","div.md-search",
        "div.toc","div.table-of-contents","button","form","svg",
        "a.edit-this-page",".md-content__button",".prev-next-nav",".md-footer-meta",
        "[role='navigation']",".skip-link",".sr-only",".visually-hidden",
    ]:
        for n in soup.select(sel):
            n.decompose()

    # 3) Inline-<code> (außerhalb <pre>) vorverarbeiten → Backticks, ohne Separator
    for c in soup.find_all("code"):
        if c.find_parent("pre"):
            continue  # echte Codeblöcke später
        raw = (c.get_text("", strip=False) or "").replace("\xa0", " ")
        c.replace_with(NavigableString(f"`{raw}`"))

    # 4) Tabellen → Markdown-Pipes (Zellen OHNE Zwischen-Separator auslesen)
    for table in soup.find_all("table"):
        rows = []
        trs = table.find_all("tr") # type: ignore
        for i, tr in enumerate(trs): # type: ignore
            cells = []
            for cell in tr.find_all(["th", "td"]): # type: ignore
                cell_txt = cell.get_text("", strip=True)  # type: ignore # kein " " als Separator → vermeidet zerspaltete Tokens
                cells.append(cell_txt) # type: ignore
            if not cells:
                continue
            rows.append("| " + " | ".join(cells) + " |") # type: ignore
            if i == 0:
                rows.append("| " + " | ".join("---" for _ in cells) + " |") # type: ignore
        table.replace_with("\n".join(rows) + "\n") # type: ignore

    # 5) <pre><code> → fenced code (mit optionaler Sprache), Whitespaces beibehalten
    for pre in soup.find_all("pre"):
        code_tag = pre.find("code") # type: ignore
        code = (code_tag.get_text("", strip=False) if code_tag else pre.get_text("", strip=False)) # type: ignore
        code = code.replace("\xa0", " ") # type: ignore
        lang = None
        if code_tag and code_tag.has_attr("class"): # type: ignore
            for cls in code_tag["class"]: # type: ignore
                if cls.startswith(("language-", "highlight-")): # type: ignore
                    lang = cls.split("-", 1)[1]; break # type: ignore
        fence = ("```" + (lang or "")).rstrip() # type: ignore
        pre.replace_with(f"\n{fence}\n{code}\n```\n")

    # 6) Headings + Fließtext einsammeln (ATX mit separatem {#anchor})
    hprefix = {1:"#",2:"##",3:"###",4:"####",5:"#####",6:"######"}
    lines: list[str] = [header_comment]

    # H1 explizit (falls vorhanden)
    h1 = soup.find("h1")
    if h1:
        t_vis = _clean_heading_text(h1.get_text(" ", strip=True))
        if t_vis:
            anchor = h1.get("id") or _slugify(t_vis) # type: ignore
            lines.append(f"# {t_vis} {{#{anchor}}}")

    # H2–H6 + restlicher Text
    for el in soup.find_all(["h2","h3","h4","h5","h6","p","ul","ol","pre","article","main","section","div"]):
        name = el.name or "" # type: ignore
        if name.startswith("h") and name[1:].isdigit(): # type: ignore
            lvl = max(2, min(6, int(name[1]))) # type: ignore
            t_vis = _clean_heading_text(el.get_text(" ", strip=True))
            if not t_vis:
                continue
            anchor = el.get("id") or _slugify(t_vis) # type: ignore
            lines.append(f"{hprefix[lvl]} {t_vis} {{#{anchor}}}")
        elif name in {"ul","ol"}:
            bullet = "-" if name == "ul" else "1."
            for li in el.find_all("li", recursive=False): # type: ignore
                t = li.get_text(" ", strip=True) # type: ignore
                if t:
                    lines.append(f"{bullet} {t}")
        elif name == "pre":
            continue  # bereits ersetzt
        else:
            t = el.get_text(" ", strip=True)
            if t:
                lines.append(t)

    text = "\n\n".join(lines)

    # 7) Nur Textsegmente normalisieren (Codeblöcke unberührt lassen)
    parts = re.split(r"(?s)(```.*?```)", text)  # [text, code, text, code, ...]
    for i in range(0, len(parts), 2):
        s = parts[i]
        s = re.sub(r"[ \t]{2,}", " ", s)   # Mehrfach-Spaces reduzieren (nicht in Code)
        s = re.sub(r"\n{3,}", "\n\n", s)   # viele Leerzeilen kürzen
        parts[i] = s.strip()

    cleaned = "\n\n".join(p for p in parts if p.strip())
    log.info("Finished parse",
             output_len=len(cleaned),
             has_h1=bool(h1),
             section=section,
             canonical=bool(canonical_url)) # type: ignore
    return cleaned
