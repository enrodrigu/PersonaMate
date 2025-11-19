This repository has been updated to use a separate backend service (FastAPI) and an OpenWebUI frontend, orchestrated with Docker Compose.

What was added
- `Dockerfile` - builds the backend image and runs the FastAPI app on port 8000.
- `docker-compose.yml` - brings up two services: `backend` and `openwebui`.
- `.dockerignore` - keeps Docker context small.

Notes and assumptions
- The backend is the original PersonaMate logic exposed as a JSON API at `/chat`.
- The OpenWebUI image name in `docker-compose.yml` is set to `ghcr.io/openwebui/open-webui:main`.
  Please adjust this to the correct image or tag if your environment uses a different registry or image name.
- OpenWebUI configuration varies between builds. You may need to configure OpenWebUI to call the backend API
  (for example, by setting an API endpoint in OpenWebUI's settings or by placing a simple proxy in front of both services).

Quick start (Docker Desktop / Docker Compose installed)

1. Build and run services:

```powershell
docker compose up --build
```

2. Backend will be exposed on http://localhost:8000

3. OpenWebUI (frontend) will be exposed on http://localhost:3000 (depending on the image/config)

If OpenWebUI doesn't automatically call the backend, either configure it in OpenWebUI's UI or use a HTTP proxy to forward certain paths from the UI to `http://backend:8000` in the compose network.

Environment variables and `.env`
- The Compose file now supports reading environment variables from a `.env` file via the `env_file` setting on services. Put your API keys and other secrets in a top-level `.env` file (next to `docker-compose.yml`) and they will be available inside the containers.

Example `.env` contents:

```env
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key
```

Be careful not to commit `.env` to version control. Add `.env` to your `.gitignore` if needed.

Next steps
- Verify OpenWebUI image name and its expected configuration options and update `docker-compose.yml` if necessary.
- Optionally add a reverse proxy (NGINX) service to route UI and API under the same domain.
