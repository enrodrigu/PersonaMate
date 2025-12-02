# PersonaMate

PersonaMate is a personal knowledge graph assistant that uses AI and Model Context Protocol (MCP) to manage personal contact data and relationships. The project exposes an **MCP server** using FastMCP that integrates with OpenWebUI for a complete AI assistant experience.

![CI/CD Pipeline](https://github.com/enrodrigu/PersonaMate/workflows/CI%2FCD%20Pipeline/badge.svg)
[![codecov](https://codecov.io/gh/enrodrigu/PersonaMate/branch/main/graph/badge.svg)](https://codecov.io/gh/enrodrigu/PersonaMate)

## 🚀 Quick Start

Get PersonaMate running in minutes with our automated deployment script!

### Windows (PowerShell)
```powershell
.\deploy.ps1
```

### Linux/macOS
```bash
chmod +x deploy.sh && ./deploy.sh
```

**Choose your deployment mode:**
- **Full Stack**: MCP + Neo4j + OpenWebUI (complete chat interface at http://localhost:3000)
- **MCP Only**: MCP + Neo4j (for custom integrations at http://localhost:8080/sse)

📖 **Need more details?** See [Quick Start](docs/quickstart.md) for quick reference or [Deployment Guide](docs/deployment.md) for comprehensive guide.

---


## Architecture

### Core Components

- **MCP Server** (`src/python/mcp_server.py`): FastMCP-based server exposing tools and resources
- **Graph Store**: Neo4j database for storing entities and relationships
- **Tools** (`src/python/tools/*`): Modular tools for managing persons and relationships
- **OpenWebUI**: Web interface for interacting with the MCP server

### MCP Tools & Resources

PersonaMate exposes its functionality through the Model Context Protocol:

**Tools**:
- `fetch_person`: Look up person information
- `update_person`: Update person data
- `link_entities`: Create relationships between entities
- `get_entity_context`: Get rich relationship context

**Resources**:
- `graph://persons`: List all persons
- `graph://relationships`: List all relationships
- `graph://stats`: Graph statistics

**Prompts**:
- `person_lookup_prompt`: Comprehensive person information lookup
- `relationship_analysis_prompt`: Analyze relationships between people

## 📦 Deployment Options

PersonaMate offers flexible deployment to match your needs:

### Option 1: Automated Deployment (Recommended)

**Interactive mode** - Let the script guide you:
```bash
.\deploy.ps1        # Windows
./deploy.sh         # Linux/macOS
```

**Direct deployment**:
```bash
# Full Stack (MCP + Neo4j + OpenWebUI)
.\deploy.ps1 -Mode full    # Windows
./deploy.sh full           # Linux/macOS

# MCP Only (MCP + Neo4j)
.\deploy.ps1 -Mode mcp-only    # Windows
./deploy.sh mcp-only           # Linux/macOS
```

**What you get:**
- ✅ Prerequisites validation
- ✅ Automatic service configuration
- ✅ Health checks
- ✅ Access URLs and credentials
- ✅ Next steps guidance

### Option 2: Manual Docker Deployment

**1. Setup Environment**
```bash
cp .env-example .env
# Edit .env with your OPENAI_API_KEY and other settings
```

**2. Choose your stack**
```bash
# Full stack
docker compose up -d

# MCP only
docker compose up -d neo4j mcp
```

**3. Access Services**
- OpenWebUI: http://localhost:3000 (full stack only)
- MCP Server: http://localhost:8080/sse
- Neo4j Browser: http://localhost:7474

### Service URLs & Credentials

| Service | URL | Credentials |
|---------|-----|------------|
| OpenWebUI | http://localhost:3000 | Create on first visit |
| MCP Server | http://localhost:8080/sse | No authentication |
| Neo4j Browser | http://localhost:7474 | neo4j / personamate |
| Neo4j Bolt | bolt://localhost:7687 | neo4j / personamate |

📖 **For detailed deployment instructions, troubleshooting, and advanced configuration**, see [Deployment Guide](docs/deployment.md)

## 🎨 Using PersonaMate

### With OpenWebUI (Full Stack)

1. **Access OpenWebUI**: Navigate to http://localhost:3000
2. **Create Account**: First-time setup requires admin account creation
3. **Start Chatting**: Use natural language to:
   - Add people: "Add John Doe, age 35, email john@example.com"
   - Find people: "Who is John Doe?"
   - Create relationships: "Link John Doe and Jane Smith as friends"
   - Get context: "Show me John's relationships"

### With MCP Client (MCP-Only)

Connect your MCP-compatible client to `http://localhost:8080/sse` and use the available tools:
- `fetch_person` - Look up person information
- `update_person` - Create or update person data
- `link_entities` - Create relationships
- `get_entity_context` - Get relationship graph

### Viewing the Knowledge Graph

Access Neo4j Browser at http://localhost:7474:
- **Username**: `neo4j`
- **Password**: `personamate` (or from your `.env`)

**Example queries**:
```cypher
// View all persons
MATCH (p:Person) RETURN p LIMIT 25

// View all relationships
MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50

// Find a specific person's network
MATCH (p:Person {name: "John Doe"})-[r]-(connected)
RETURN p, r, connected
```

## 🛠️ Common Operations

### Managing Services
```bash
# View service status
docker compose ps

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f mcp
docker compose logs -f neo4j

# Restart a service
docker compose restart mcp

# Stop all services
docker compose down

# Stop and remove all data
docker compose down -v
```

### Quick Troubleshooting
```bash
# Check Neo4j is ready
docker exec personamate-neo4j cypher-shell -u neo4j -p personamate "RETURN 1"

# Check MCP server logs
docker compose logs mcp --tail 50

# Rebuild and restart MCP
docker compose build mcp && docker compose restart mcp
```

📖 **For more troubleshooting help**, see [Deployment Guide - Troubleshooting](docs/deployment.md#troubleshooting)

## 💻 Development

### Running Tests

**All tests in Docker** (recommended):
```bash
# Start services
docker compose up -d neo4j mcp

# Run all tests
docker compose run --rm pytest pytest /app/test/python/ -v

# Run specific test suite
docker compose run --rm pytest pytest /app/test/python/test_mcp_integration.py -v
docker compose run --rm pytest pytest /app/test/python/test_tools.py -v

# Run with coverage
docker compose run --rm pytest pytest /app/test/python/ -v --cov=/app/src/python --cov-report=term
```

**Test suite includes:**
- ✅ 6 MCP integration tests
- ✅ 14 tool implementation tests
- ✅ Cross-tool workflow validation
- ✅ Neo4j persistence checks

### Local Development (without Docker)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Neo4j**:
   ```bash
   docker compose up neo4j -d
   ```

3. **Set environment variables**:
   ```bash
   export NEO4J_URI=bolt://localhost:7687
   export NEO4J_USER=neo4j
   export NEO4J_PASSWORD=personamate
   export NEO4J_DB=neo4j
   export OPENAI_API_KEY=your_key_here
   ```

4. **Run the MCP server**:
   ```bash
   fastmcp run src/python/mcp_server.py --transport sse --port 8080
   ```

### CI/CD Pipeline

The project uses GitHub Actions for automated testing on every push/PR:
- Runs all 20 tests in Docker environment
- Code quality checks (flake8, black)
- Coverage reporting

📖 **See [CI/CD Pipeline](docs/workflows.md) for CI/CD documentation**

## 📁 Project Structure

```
PersonaMate/
├── deploy.ps1                  # Windows deployment script
├── deploy.sh                   # Linux/macOS deployment script
├── QUICKSTART.md              # Quick reference guide
├── DEPLOYMENT.md              # Comprehensive deployment guide
├── src/python/
│   ├── mcp_server.py          # FastMCP server (main entry point)
│   ├── fastmcp.json           # FastMCP configuration
│   ├── tools/
│   │   ├── personalDataTool.py # Person CRUD operations
│   │   └── linkingTool.py      # Relationship management
│   └── utils/
│       ├── neo4j_graph.py     # Neo4j wrapper
│       └── helper.py          # Utility functions
├── test/python/
│   ├── test_mcp_integration.py # MCP protocol tests
│   └── test_tools.py          # Tool implementation tests
├── .github/workflows/
│   ├── ci.yml                 # GitHub Actions pipeline
│   └── README.md              # CI/CD documentation
├── docker-compose.yml         # Docker services configuration
├── Dockerfile                 # MCP server container
└── requirements.txt           # Python dependencies
```

## ✨ Key Features

- 🤖 **MCP Protocol**: Standard interface for AI assistants
- 💬 **OpenWebUI**: Modern chat interface (optional)
- 🕸️ **Neo4j Graph**: Powerful relationship modeling
- 🐳 **Docker**: Easy deployment and scaling
- 🔧 **Modular Tools**: Extensible functionality
- ✅ **Comprehensive Tests**: 20 automated tests with CI/CD
- 📊 **Graph Visualization**: Neo4j Browser integration

## 📚 Documentation

Full documentation is available in the `docs/` folder and can be viewed as a website:

```bash
# Install documentation dependencies
pip install mkdocs mkdocs-material mkdocs-git-revision-date-localized-plugin

# Serve documentation locally
mkdocs serve

# Open http://127.0.0.1:8000 in your browser
```

**Quick Links:**
- **[Quick Start](docs/quickstart.md)** - Get started in 2 commands
- **[Deployment Guide](docs/deployment.md)** - Full deployment with troubleshooting
- **[Contributing Guide](docs/contributing.md)** - Development setup and guidelines
- **[Testing Guide](docs/testing.md)** - Running and writing tests
- **[CI/CD Pipeline](docs/workflows.md)** - GitHub Actions documentation
- **[Project Structure](docs/structure.md)** - Codebase organization
- **[MCP Protocol](docs/mcp.md)** - Model Context Protocol details
- **[MCP Tools](docs/mcp/tools.md)** - Available MCP tools
- **[MCP Resources](docs/mcp/resources.md)** - MCP resources and prompts

## 🤝 Contributing

Contributions are welcome! We use automated code formatting to maintain consistent style.

**Quick start:**
```bash
# Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/PersonaMate.git
cd PersonaMate

# Install pre-commit hooks (auto-formats on commit)
pip install pre-commit && pre-commit install

# Make your changes and commit
# Code is automatically formatted by hooks or CI!
```

**Code will be auto-formatted:**
- ✅ Locally with pre-commit hooks (recommended)
- ✅ Automatically by CI when you push (if you skip hooks)

📖 **See [Contributing Guide](docs/contributing.md) for detailed contribution guidelines, testing, and development setup.**

## 📄 License

See LICENSE file for details.

## 🆘 Need Help?

- 📖 Check [Deployment Guide](docs/deployment.md) for troubleshooting
- 💬 Open an issue on GitHub
- 📊 View logs: `docker compose logs -f`
- 📚 Browse the [documentation](docs/)

---

**Built with ❤️ using FastMCP, Neo4j, and OpenWebUI**
