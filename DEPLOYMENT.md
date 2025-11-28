# PersonaMate Deployment Guide

## Deployment Options

PersonaMate offers two deployment modes to suit different use cases:

### 1. Full Stack Deployment
**Best for**: End users who want a complete AI chat experience

**Includes**:
- MCP Server (FastMCP) - AI integration layer
- Neo4j Database - Knowledge graph storage
- OpenWebUI - Web-based chat interface

**Access**:
- Chat Interface: http://localhost:3000
- MCP Server: http://localhost:8080/sse
- Neo4j Browser: http://localhost:7474

### 2. MCP-Only Deployment
**Best for**: Developers integrating PersonaMate into custom applications

**Includes**:
- MCP Server (FastMCP) - AI integration layer
- Neo4j Database - Knowledge graph storage

**Access**:
- MCP Server: http://localhost:8080/sse
- Neo4j Browser: http://localhost:7474

## Using the Deployment Scripts

### Windows (PowerShell)

1. **Interactive mode** (recommended for first-time users):
   ```powershell
   .\deploy.ps1
   ```
   Follow the on-screen prompts to choose your deployment mode.

2. **Direct deployment**:
   ```powershell
   # Full stack with OpenWebUI
   .\deploy.ps1 -Mode full
   
   # MCP-only deployment
   .\deploy.ps1 -Mode mcp-only
   ```

### Linux/macOS

1. **Make script executable** (first time only):
   ```bash
   chmod +x deploy.sh
   ```

2. **Interactive mode** (recommended for first-time users):
   ```bash
   ./deploy.sh
   ```
   Follow the on-screen prompts to choose your deployment mode.

3. **Direct deployment**:
   ```bash
   # Full stack with OpenWebUI
   ./deploy.sh full
   
   # MCP-only deployment
   ./deploy.sh mcp-only
   ```

## What the Script Does

1. **Checks prerequisites**: Verifies Docker and Docker Compose are installed
2. **Validates environment**: Checks for .env file and Docker daemon status
3. **Builds images**: Compiles the MCP server Docker image
4. **Starts services**: Launches selected services based on deployment mode
5. **Health checks**: Waits for services to be ready
6. **Displays access info**: Shows URLs and credentials

## Environment Configuration

Before deploying, ensure your `.env` file is configured:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Neo4j Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=personamate
NEO4J_DB=neo4j

# Optional: LangChain Tracing
LANGCHAIN_API_KEY=your_langchain_key
LANGCHAIN_TRACING_V2=false
```

## Post-Deployment Steps

### For Full Stack Deployment

1. **Access OpenWebUI**: Navigate to http://localhost:3000
2. **Create Admin Account**: First-time setup requires creating an admin user
3. **Configure MCP Connection**:
   - Go to Settings → Connections
   - Add MCP Server URL: `http://mcp:8080/sse`
   - Test connection
4. **Start Chatting**: Begin interacting with PersonaMate!

### For MCP-Only Deployment

1. **Connect Your MCP Client**: Configure your client to connect to `http://localhost:8080/sse`
2. **Test Connection**: Use MCP protocol tools to list available tools/resources
3. **Integrate**: Use PersonaMate tools in your application

## Managing Services

### View Service Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f mcp
docker compose logs -f neo4j
docker compose logs -f openwebui
```

### Restart Services
```bash
# All services
docker compose restart

# Specific service
docker compose restart mcp
```

### Stop Services
```bash
docker compose down
```

### Stop and Remove Data
```bash
docker compose down -v
```

## Troubleshooting

### Services Won't Start

**Check Docker daemon**:
```bash
docker ps
```

**View service logs**:
```bash
docker compose logs mcp --tail 50
docker compose logs neo4j --tail 50
```

### Neo4j Connection Issues

1. Wait 15-20 seconds after starting Neo4j
2. Check Neo4j logs: `docker compose logs neo4j`
3. Verify credentials in `.env` file
4. Test connection: http://localhost:7474

### MCP Server Not Responding

1. Check if service is running: `docker compose ps`
2. View MCP logs: `docker compose logs mcp -f`
3. Verify environment variables are set
4. Restart MCP service: `docker compose restart mcp`

### OpenWebUI Can't Connect to MCP

1. Ensure both services are running
2. Use internal Docker network name: `http://mcp:8080/sse` (not `localhost`)
3. Check firewall settings
4. Verify MCP server is in SSE mode (check logs)

## Advanced Configuration

### Custom Ports

Edit `docker-compose.yml` to change default ports:

```yaml
services:
  mcp:
    ports:
      - "8080:8080"  # Change first number for custom external port
  
  neo4j:
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
  
  openwebui:
    ports:
      - "3000:8080"  # Change first number for custom external port
```

### Resource Limits

Adjust memory/CPU limits in `docker-compose.yml`:

```yaml
services:
  neo4j:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2'
```

### Persistent Data

Neo4j data is persisted in Docker volumes. To backup:

```bash
# List volumes
docker volume ls

# Backup Neo4j data
docker run --rm -v personamate_neo4j_data:/data -v $(pwd):/backup alpine tar czf /backup/neo4j-backup.tar.gz /data
```

## Security Considerations

### Production Deployment

1. **Change default passwords**: Update Neo4j password in `.env`
2. **Use HTTPS**: Configure reverse proxy (nginx/traefik)
3. **API key security**: Never commit `.env` file to version control
4. **Network isolation**: Use Docker networks to isolate services
5. **Resource limits**: Set appropriate memory/CPU limits
6. **Regular backups**: Backup Neo4j data regularly

### OpenWebUI Security

- Enable authentication
- Use strong passwords
- Configure CORS properly
- Use HTTPS in production
- Keep OpenWebUI updated

## Getting Help

- **Documentation**: See README.md for detailed documentation
- **Issues**: Report bugs on GitHub Issues
- **Logs**: Always check service logs first for troubleshooting
- **Community**: Join discussions on GitHub Discussions
