# PersonaMate

PersonaMate is a personal knowledge graph assistant that uses AI and Model Context Protocol (MCP) to manage personal contact data and relationships. The project exposes an **MCP server** using FastMCP that integrates with OpenWebUI for a complete AI assistant experience.

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

## Quick Start with Docker

### 1. Setup Environment

```bash
cp .env-example .env
```

### 2. Start All Services

```bash
# Start Neo4j, MCP server, backend, and OpenWebUI
docker-compose up -d
```

This will start:
- **Neo4j** on ports 7474 (HTTP) and 7687 (Bolt)
- **MCP Server** on port 8080 (SSE transport)
- **OpenWebUI** on port 3000

### 3. Access OpenWebUI

Open your browser to `http://localhost:3000` and configure OpenWebUI to use the MCP server.

## OpenWebUI Configuration


## Viewing Graph Data

Access Neo4j Browser at `http://localhost:7474` to visualize your knowledge graph:
- Username: `neo4j`
- Password: (from your `.env` file)

## Common Operations

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mcp
docker-compose logs -f neo4j
```

### Restart Services
```bash
docker-compose restart mcp
```

### Stop All Services
```bash
docker-compose down
```

### Reset Graph Data
```bash
# Stop services and remove Neo4j data volume
docker-compose down -v

# Restart
docker-compose up -d
```

## Development

### Local Development (without Docker)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start Neo4j:
```bash
docker-compose up neo4j -d
```

3. Set environment variables:
```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your-password
export NEO4J_DB=neo4j
```

4. Run the MCP server:
```bash
python src/python/mcp_server.py --transport sse --port 8080
```

### Running Tests

```bash
# Run all tests
pytest test/

# Run specific test file
pytest test/python/utils/neo4j_integration_test.py

# Run tests in Docker
docker-compose up pytest
```

## Project Structure

```
PersonaMate/
├── src/python/
│   ├── mcp_server.py           # FastMCP server (main entry point)
│   ├── fastmcp.json            # FastMCP server configuration
│   ├── tools/
│   │   ├── personalDataTool.py # Person CRUD operations
│   │   └── linkingTool.py      # Relationship management
│   └── utils/
│       ├── neo4j_graph.py      # Neo4j wrapper
│       └── helper.py           # Utility functions
├── docs/
│   └── mcp.md                  # MCP documentation
├── test/
│   └── python/utils/
│       └── neo4j_integration_test.py
├── docker-compose.yml          # Docker services configuration
├── Dockerfile                  # Container image
├── requirements.txt            # Python dependencies
└── .env                        # Environment configuration (create this)
```

## Architecture Benefits

- ✅ **MCP Protocol**: Standard interface for AI assistants
- ✅ **OpenWebUI Integration**: Modern web interface
- ✅ **Neo4j Graph**: Powerful relationship modeling
- ✅ **Docker Deployment**: Easy setup and scaling
- ✅ **Modular Tools**: Extensible functionality

## Contributing

See `docs/mcp.md` for the complete MCP specification.

## License

See LICENSE file for details.

I recommend you to deactivate the openAI api link so that you only get PersonaMate custom model and it is easier to access. Or simply deactivate models you won't use.