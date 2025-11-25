# PersonaMate
PersonaMate is a personal assistant project that uses a langgraph-based agent and LLMs to answer questions, manage personal contact data, and create relations between entities.

This repository exposes a FastAPI backend (`src/python/app.py`) and a refactored core graph implementation (`src/python/core.py`) that provides programmatic helpers (`build_graph`, `chat_once`, and `interactive_loop`). The project includes Docker artifacts to run the backend and optionally an OpenWebUI frontend via Docker Compose.

## Current architecture

- Backend: FastAPI application in `src/python/app.py` which builds the langgraph graph at startup (via `core.build_graph`) and exposes a `/chat` POST endpoint that returns JSON: `{ "response": "..." }`.
- Core graph logic: `src/python/core.py` — contains `build_graph`, `chat_once`, and a CLI interactive loop.
- Tools: `src/python/tools/*` (e.g. `personalDataTool.py`, `linkingTool.py`) provide tool functions used by the assistant.
 - Utilities: `src/python/utils/*` contains helpers and a Neo4j wrapper (`neo4j_graph.py`). The project now uses Neo4j as the primary graph store.
- Docker: `Dockerfile` builds the backend image; `docker-compose.yml` can start the backend and an OpenWebUI container.

## Docker-based setup and configuration

Follow these steps to run PersonaMate with Docker (recommended for development and quick local deployment).

Prerequisites
- Install Docker and Docker Compose (Compose v2 or later).
- Optionally: docker login ghcr.io if you will pull the OpenWebUI image from GHCR.

1) Clone the repo
```bash
git clone /path/to/repo
cd PersonaMate
```

2) Create a .env file
Create a `.env` in the repo root to provide runtime configuration consumed by docker-compose and the backend. Example minimal `.env`:

```env
# Neo4j connection (when using the included neo4j service)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change_this_password
NEO4J_DB=neo4j

# Optional: override OpenWebUI image (if present in docker-compose)
OPENWEBUI_IMAGE=ghcr.io/openwebui/openwebui:latest

# Backend port mapping
BACKEND_PORT=8000
```

Notes:
- Set `NEO4J_PASSWORD` to a secure value. The compose file may use `NEO4J_AUTH` (format `neo4j/<password>`) for the Neo4j container — you can either set that in `docker-compose.yml` or export `NEO4J_AUTH` in `.env`.
- To use the compose-provided Neo4j, ensure `NEO4J_URI=bolt://neo4j:7687` and the `NEO4J_USER`/`NEO4J_PASSWORD` match the Neo4j service auth.

3) Start services with Docker Compose
- Start only the backend (fast iteration, uses external Neo4j if configured):
```bash
docker compose up --build backend
```

- Start the full stack (backend + neo4j + optional openwebui as defined):
```bash
docker compose up --build
```

If OpenWebUI is pulled from GHCR and requires auth:
```bash
docker login ghcr.io
```

4) Common commands
- Tail logs:
```bash
docker compose logs -f backend
```
- Stop and remove containers (preserve volumes unless `-v`):
```bash
docker compose down
```
- Remove volumes (will delete Neo4j data):
```bash
docker compose down -v
```
- Rebuild the backend after code changes:
```bash
docker compose up --build backend
```

5) Accessing the API
- By default, the backend listens on port 8000. Example POST to chat endpoint:
```bash
curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"Hello"}'
```
Response: JSON like `{ "response": "..." }`.

6) Neo4j persistence and data
- The compose config normally maps a Docker volume for Neo4j data. If you change or remove volumes you may lose stored graph data.
- To connect the backend to an external Neo4j instance, update `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, and `NEO4J_DB` in `.env` before starting the backend container.

7) Customizing behavior
- To override images or ports, edit `docker-compose.yml` or set the corresponding `.env` keys (e.g., `OPENWEBUI_IMAGE`, `BACKEND_PORT`).
- If you need a different Neo4j auth scheme, set `NEO4J_AUTH` (for the Neo4j container) to `neo4j/<password>`.

Troubleshooting tips
- If the backend fails to connect to Neo4j, verify `NEO4J_URI` and credentials, and inspect Neo4j logs (`docker compose logs neo4j`).
- If OpenWebUI image pull fails, ensure you have internet access and, if required, authenticated to GHCR.

This should be sufficient to run and configure PersonaMate with Docker. Adjust `.env` values and compose options based on your environment and security requirements.

### OpenWebUI configuration

To link openwebui to the backend API use go the configuration panel and add a connection to the backend with the url `http://backend:8000/v1`
I recommend you to deactivate the openAI api link so that you only get PersonaMate custom model and it is easier to access. Or simply deactivate models you won't use.