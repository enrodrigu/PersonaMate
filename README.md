# PersonaMate
PersonaMate is a personal assistant project that uses a langgraph-based agent and LLMs to answer questions, manage personal contact data, and create relations between entities.

This repository exposes a FastAPI backend (`src/python/app.py`) and a refactored core graph implementation (`src/python/core.py`) that provides programmatic helpers (`build_graph`, `chat_once`, and `interactive_loop`). The project includes Docker artifacts to run the backend and optionally an OpenWebUI frontend via Docker Compose.

## Current architecture

- Backend: FastAPI application in `src/python/app.py` which builds the langgraph graph at startup (via `core.build_graph`) and exposes a `/chat` POST endpoint that returns JSON: `{ "response": "..." }`.
- Core graph logic: `src/python/core.py` — contains `build_graph`, `chat_once`, and a CLI interactive loop.
- Tools: `src/python/tools/*` (e.g. `personalDataTool.py`, `linkingTool.py`) provide tool functions used by the assistant.
 - Utilities: `src/python/utils/*` contains helpers and a Neo4j wrapper (`neo4j_graph.py`). The project now uses Neo4j as the primary graph store.
- Docker: `Dockerfile` builds the backend image; `docker-compose.yml` can start the backend and an OpenWebUI container.

## Quick start — local (dev)

1. Create and activate a virtual environment (recommended):

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

2. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

3. Create a `.env` file in the repository root and add API keys if you plan to use real LLMs / Tavily:

```env
OPENAI_API_KEY=your_openai_key_here
TAVILY_API_KEY=your_tavily_key_here
# any other env vars you need
```

4. Run the backend directly (development):

```powershell
# from repo root
uvicorn src.python.app:app --host 0.0.0.0 --port 8000 --reload
```

5. Call the chat endpoint (PowerShell):

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -Body (@{message='Hello'} | ConvertTo-Json) -ContentType 'application/json'
```

The `/chat` endpoint returns JSON: `{ "response": "..." }`.

## Docker / Docker Compose

This repo includes a `Dockerfile` for the backend and a `docker-compose.yml` that can start two services:

- `backend`: builds the backend image and exposes port `8000`.
- `openwebui`: a helper entry that pulls an OpenWebUI image (configured in `docker-compose.yml`).

To run Compose (without OpenWebUI if you prefer):

```powershell
# run only the backend
docker compose up --build backend
```

To run both services (may require GHCR auth):

```powershell
docker compose up --build
```

Neo4j service

The compose setup includes a `neo4j` service. Set the password using `.env` or override `NEO4J_AUTH` in `docker-compose.yml`.

Example `.env` entries to connect the backend to Neo4j:

```env
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j
NEO4J_DB=neo4j
```

Run compose and the backend will connect to the embedded `neo4j` container:

```powershell
docker compose up --build
```