# Quick Deployment Reference

## TL;DR - Get Started in 2 Commands

### Windows
```powershell
# Run as Administrator if execution policy is restricted
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\deploy.ps1
```

### Linux/macOS
```bash
chmod +x deploy.sh && ./deploy.sh
```

## Deployment Modes

| Mode | Services | Best For | Access |
|------|----------|----------|--------|
| **Full Stack** | MCP + Neo4j + OpenWebUI | End users wanting chat interface | http://localhost:3000 |
| **MCP Only** | MCP + Neo4j | Developers, custom integrations | http://localhost:8080/sse |

## Quick Commands

### Deploy
```bash
# Interactive (choose during deployment)
./deploy.sh              # Linux/macOS
.\deploy.ps1             # Windows

# Direct
./deploy.sh full         # Full stack
./deploy.sh mcp-only     # MCP only
```

### Manage
```bash
docker compose ps                    # View status
docker compose logs -f               # View all logs
docker compose logs -f mcp           # View MCP logs
docker compose restart mcp           # Restart MCP
docker compose down                  # Stop all
docker compose down -v               # Stop and remove data
```

## Access URLs

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| OpenWebUI | http://localhost:3000 | Create on first visit |
| MCP Server | http://localhost:8080/sse | No auth |
| Neo4j Browser | http://localhost:7474 | neo4j / personamate |

## Common Issues

### "Docker daemon not running"
→ Start Docker Desktop

### "Permission denied" (Linux/macOS)
→ Run: `chmod +x deploy.sh`

### "Execution policy restricted" (Windows)
→ Run as Admin: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Neo4j connection fails
→ Wait 15-20 seconds after deployment, Neo4j needs time to initialize

### OpenWebUI can't connect to MCP
→ Use `http://mcp:8080/sse` not `http://localhost:8080/sse` in OpenWebUI settings

## Need More Help?

- Full guide: `DEPLOYMENT.md`
- Documentation: `README.md`
- CI/CD info: `.github/workflows/README.md`
