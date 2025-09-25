# MCP Server Docs

Dieses Projekt ist ein Prototyp, der im Rahmen einer Take-Home-Challenge entwickelt wurde.  
Ziel ist es, einen **MCP-Server** bereitzustellen, der technische Dokumentationen automatisch crawlt, in handliche Chunks zerlegt, in einer Vektordatenbank speichert und über **Retrieval-Augmented Generation (RAG)** für Fragen und Antworten verfügbar macht.  
So können MCP-Clients (z. B. GitHub Copilot Chat) oder ein einfacher Web-Chatbot auf die Inhalte zugreifen.

## Architekturübersicht
### Pipeline zur Erstellung der Vektordatenbank
```mermaid
sequenceDiagram
  participant A as MCP-Schnittstelle
  participant B as Job-Manager
  participant H as Blocking Tasks
  participant C as Crawler
  participant F as Website
  participant I as HTML-Processor
  participant G as Speicher (JSONL)
  participant D as Chunker
  participant E as ChromaDB

  A->>B: (1) submit pipeline job
  B->>H: (2) start pipeline
  H->>C: (3) start crawler (subprocess)
  C->>F: (4) call website
  F-->>C: (5) send html
  C->>I: (6) send html
  I-->>C: (7) processed html
  C->>G: (8) store jsonl
  C-->>H: (9) unblock
  H->>D: (10) start chunker (subprocess)
  G-->>D: (11) get jsonl
  D->>G: (12) store chunked jsonl
  D-->>H: (13) unblock
  H->>E: (14) start database creation (subprocess)
  G->>E: (15) chunked jsonl → embed & store
  E-->>H: (16) unblock
```
### Pipeline in Kürze

1. **Start:** MCP → Job-Manager → Orchestrierung startet Crawler.  
2. **Extraktion & Aufbereitung:** Crawler lädt HTML, lässt es vom HTML-Processor bereinigen und schreibt **JSONL**.  
3. **Chunking:** Orchestrierung startet Chunker, der JSONL liest und **Chunked JSONL** zurückschreibt.  
4. **Vektordatenbank:** Orchestrierung startet DB-Schritt; Chunked JSONL wird eingebettet und in **ChromaDB** upserted.  
5. **Synchronisation:** Jeder Schritt meldet per *unblock* an die Orchestrierung zurück.

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
uv pip install scrapy loguru beautifulsoup4 pydantic pydantic-settings "pydantic[email]" chromadb mcp fastapi
```
## Konfiguration
Erstelle eine `.env`-Datei im Projektverzeichnis oder setze die Variablen als Umgebungsvariablen.

### Pflichtwerte
```env
# Sitemap-URL für crawling
SCRAPE_URL=https://fastapi.tiangolo.com/sitemap.xml

# Kontaktadresse (wird im User-Agent verwendet)
EMAIL=email@example.com
```
### Optionale Werte (mit Defaults)
```env
# Verhindert ein ungewolltes Löschen einer existierenden Datenbank (Auf True setzen um Löschen zu erlauben) 
CHROMA_REMOVE_OLD=False

CHROMA_BATCH_SIZE=1000
CHUNK_MAX_CHARS=1000
CHUNK_OVERLAP=100

# Werte für unbekannte Sections und Sections der Website, die nach Bedarf angepasst werden können.
SECTION_UNKNOWN=unknown
SECTION_CATEGORIES=["tutorial", "advanced", "reference", "alternatives", "deployment", "benchmarks"]


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
## MCP Server
Starte den MCP-Server
```bash
uv run mcp dev mcp_main.py
```
Im MCP Inspector kann eine Verbindung über "Connect" hergestellt werden.
Unter Tools → List Tools stehen die folgenden Tools bereit:

- `start_crawl`: Startet das Webscraping

- `start_chunk`: Führt das Chunking aus

- `start_ingest`: Befüllt die Vektordatenbank

- `start_pipeline`: Führt alle Schritte nacheinander aus

- `ask_job`: Beantwortet eine Frage, gibt job_id zurück

- `job_status`: Status des Jobs abfragen (queued, running, success, error)

- `job_log_tail`: Fortschritt/Logs eines Jobs ansehen

- `job_result`: Ergebnis eines Jobs abrufen (inkl. Antwort und Quellen)

## Beispielablauf mit MCP Inspector
1.  `start_pipeline` → gibt `{"job_id": "…"}` zurück

2.  `job_status <job_id>` → zeigt `running` / `success`

3.  `job_log_tail <job_id>` → zeigt den Fortschritt im Log

4.  `job_result <job_id>` → gibt die Antwort des RAG zurück
## Logs
- Server-Logs: `mcp_server.log`
- Pro-Job-Logs: `./job_logs/job_<name>_<id>.log`<br>
→ verhindert, dass der MCP Inspector einfriert, und erlaubt Debugging pro Job.
## Nutzung des Chatbots
Sobald die Vektordatenbank gefüllt wurde, kann ein einfacher Chatbot geöffnet werden:
```bash
uvicorn chatbot.chat_api:app --reload
```
Der Chatbot benötigt die Vektordatenbank und Ollama, aber nicht den MCP-Server.<br>
Die Weboberfläche steht unter http://127.0.0.1:8000<br>
Kopierbare Codefenster und LaTeX Darstellung sind integriert.
## Nächste Schritte
- Nutzung von anderen Datenquellen als gescrapeten Websites (Beispiel: Dokumentation von GitHub herunterladen und lokal in Vektordatenbank einfügen)
- Integration des Alters der Quelle in die Vektordatenbank (falls verfügbar)
- Nutzung von Scraper der keine Sitemaps benötigt
- Erweiterbarkeit der Vektordatenbank ermöglichen (statt löschen und ersetzen)
- Nutzung von LLMs über Web-API statt nur lokal
- Anpassung des durch ChromaDB genutzten LMs
- Antworten als Streaming im MCP Inspector anzeigen
- Automatisiertes Re-Crawling & Re-Ingest (Scheduler)
- Evaluation/Ranking der Antworten verbessern
- Granulare Steuerung des Scores für Kategorien um einen Fokus zu erlauben (Beispiel: Vektordatenbank zieht Einsteigerthemen vor)
- Steuerung für Scores nach Alter der Inhalte
- Steuerung von HTML-Processing über Konfigurationsdateien
## Status
Dies ist ein Prototyp - Konfiguration und Funktionsumfang können sich ändern. Aktuell ist das Crawling auf FastAPI optimiert, andere Seiten funktionieren, werden aber möglicherweise nicht alle Features verwenden (Beispiel Kubernetes: LaTeX wird übernommen, Codebeispiele nicht).

## Lizenz
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
