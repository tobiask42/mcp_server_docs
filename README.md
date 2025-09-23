# MCP Server Docs

Dieses Projekt ist ein Prototyp für einen RAG-Workflow (Retrieval-Augmented Generation) basierend auf Daten, die aus Webseiten gecrawlt werden.  

## Voraussetzungen

- [Ollama](https://ollama.com/) installiert  
- Git  
- [uv](https://github.com/astral-sh/uv) für Virtual Environments & Paketmanagement  

### Ollama vorbereiten
```bash
ollama pull mistral:7b-instruct
ollama run mistral:7b-instruct
```
(Oder ein anderes Modell – dann die entsprechenden ENV-Variablen wie `OLLAMA_MODEL` anpassen.)

## Installation
```bash
git clone https://github.com/tobiask42/mcp_server_docs.git
cd mcp_server_docs

# Virtuelle Umgebung erstellen
uv venv mcp-env-uv
source mcp-env-uv/bin/activate   # Linux/Mac
mcp-env-uv\Scripts\activate      # Windows

# Abhängigkeiten installieren
uv pip install scrapy
uv pip install loguru
uv pip install beautifulsoup4
uv pip install pydantic
uv pip install pydantic-settings
uv pip install "pydantic[email]"
uv pip install chromadb
uv pip install mcp
uv pip install fastapi
```
## Konfiguration
Erstelle eine `.env`-Datei im Projektverzeichnis oder setze die Variablen als Environment Variablen.

### Pflichtwerte
```env
# Liste der Sitemap-URLs (JSON-Format)
SCRAPELIST=["https://fastapi.tiangolo.com/sitemap.xml"]

# Kontaktadresse (wird im User-Agent verwendet)
EMAIL=email@example.com
```
### Optionale Werte (mit Defaults)
```env
CHROMA_BATCH_SIZE=1000
CHUNK_MAX_CHARS=1000
CHUNK_OVERLAP=100

RAG_MAX_CONTEXT_CHARS=5000
RAG_MAX_CHUNKS_PER_URL=1

OLLAMA_MODEL=mistral:7b-instruct
OLLAMA_TEMPERATURE=0.0
OLLAMA_CONTEXT_WINDOW_TOKENS=4096
OLLAMA_MAX_TOKENS=384
OLLAMA_ENDPOINT="http://localhost:11434/api/chat"
OLLAMA_TIMEOUT_S=120

SPIDER_PRIORITY=spider
SPIDER_AUTOTHROTTLE_ENABLED=True
SPIDER_DOWNLOAD_DELAY=0.3
SPIDER_CONCURRENT_REQUESTS=8
SPIDER_HTTPCACHE_ENABLED=True

CRAWLER_LOG_LEVEL=INFO

# Optional für externe Dienste (Nutzung noch nicht implementiert)
API_KEY=
```
## Nutzung
Die Hauptskripte können in dieser Reihenfolge ausgeführt werden:
```bash
python scraper_main.py
python chunker_main.py
python db_creation_main.py
python rag_main.py
```
Um den mcp-Server zu starten kann `uv run mcp dev mcp_main.py` aufgerufen werden. Im MCP Inspector kann eine Verbindung über "Connect" hergestellt werden und unter Tools -> List Tools finden sich die folgenden Tools:
`start_crawl`: Das Webscraping wird ausgeführt
`start_chunk`: Das Chunking wird ausgeführt
`start_ingest`: Die Vektordatenbank wird befüllt
`start_pipeline`: Alle Schritte werden nacheinander ausgeführt.
`ask_job`: Ein Prompt wird beantwortet, die job_id wird zurückgegeben.

``
Dabei starten die Tools jeweils Jobs.
Mithilfe der job_id kann man über `job_status` den aktuellen Status und `job_log_tail` das Log aufrufen. Zudem werden alle Daten auch in der `mcp_server.log`-Datei gespeichert.
Die Antwort erhält man wenn man `job_result` mit der job_id aufruft.

Damit erhältst du einen **RAG-Workflow**, der Inhalte aus den angegebenen Webseiten crawlt, chunked, in eine Datenbank schreibt und anschließend für Fragen/Antworten in der Kommandozeile bereitstellt.
## Nutzung des Chatbots
Sobald die Vektordatenbank gefüllt wurde kann über `uvicorn chatbot.chat_api:app --reload` ein einfacher Chatbot geöffnet werden. Voraussetzung dafür ist dass der mcp-Server läuft.
## Status
Dies ist ein Prototyp - Konfiguration und Funktionsumfang können sich ändern.

## Lizenz
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
