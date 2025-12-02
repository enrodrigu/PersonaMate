# MCP Tools Reference

PersonaMate exposes its functionality through Model Context Protocol (MCP) tools. These tools can be called by AI assistants and other MCP clients to manage personal data and relationships in the knowledge graph.

!!! info "Not a REST API"
    PersonaMate uses the Model Context Protocol, not traditional HTTP REST endpoints. Tools are invoked via MCP protocol, not HTTP requests. See [MCP Protocol](../mcp.md) for protocol details.

## Tool Overview

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| `fetch_person` | Retrieve person information | `name: str` | Person data with graph context |
| `update_person` | Create or update person | `name: str`, optional fields | Success message |
| `link_entities` | Create relationship | `from_entity: str`, `to_entity: str`, `relationship_type: str` | Success message |
| `get_entity_context` | Get relationship context | `entity_name: str`, optional `depth: int` | JSON with nodes, edges, summary |

## fetch_person

Retrieve comprehensive information about a person from the knowledge graph.

### Function Signature

```python
def fetch_person(name: str) -> str
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Person's name to look up (case-insensitive) |

### Return Value

Returns a JSON string containing:

```json
{
  "name": "John Doe",
  "age": 30,
  "email": "john@example.com",
  "phone": "123-456-7890",
  "address": {
    "street": "123 Main St",
    "city": "Boston",
    "state": "MA",
    "zip": "02101"
  },
  "graph_context": [
    {
      "name": "Jane Smith",
      "labels": ["Person"],
      "rel": "FRIEND_OF",
      "direction": "out"
    }
  ]
}
```

If person not found: `"Person not found"`

### Features

- **Case-insensitive matching**: "john doe" matches "John Doe"
- **Normalized name matching**: Handles diacritics and punctuation
- **Graph context**: Includes immediate neighbors and relationships
- **Nested objects**: Address stored as structured data

### Example Usage

**Request:**
```json
{
  "tool": "fetch_person",
  "arguments": {
    "name": "John Doe"
  }
}
```

**Response:**
```json
{
  "name": "John Doe",
  "age": 30,
  "email": "john@example.com",
  "graph_context": [...]
}
```

### Implementation Details

**Source file:** `src/python/tools/personalDataTool.py`

**Name normalization:**
- Strips whitespace
- Converts to lowercase
- Removes diacritics (é → e)
- Removes punctuation
- Collapses multiple spaces

**Cypher query:**
```cypher
MATCH (p:Person) WHERE toLower(p.name) = $lower RETURN p LIMIT 1
```

**Fallback strategy:**
If direct match fails, performs normalized comparison on all persons.

---

## update_person

Create a new person or update an existing person's information in the knowledge graph.

### Function Signature

```python
def update_person(
    name: str,
    age: int = None,
    email: str = None,
    phone: str = None,
    address: dict = None
) -> str
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Person's name (case-sensitive for storage) |
| `age` | integer | No | Person's age |
| `email` | string | No | Email address |
| `phone` | string | No | Phone number |
| `address` | object | No | Address object with street, city, state, zip |

### Return Value

Returns: `"Person data updated"`

If name is missing: `"Name is required"`

### Features

- **Upsert operation**: Creates if doesn't exist, updates if exists
- **Partial updates**: Only specified fields are updated
- **Nested objects**: Address stored as JSON string internally
- **Transaction safety**: Uses Neo4j MERGE for atomic operations

### Example Usage

**Create new person:**
```json
{
  "tool": "update_person",
  "arguments": {
    "name": "Alice Johnson",
    "age": 35,
    "email": "alice@example.com",
    "address": {
      "street": "456 Oak Ave",
      "city": "Cambridge",
      "state": "MA",
      "zip": "02139"
    }
  }
}
```

**Update existing person (partial):**
```json
{
  "tool": "update_person",
  "arguments": {
    "name": "Alice Johnson",
    "age": 36
  }
}
```

### Implementation Details

**Source file:** `src/python/tools/personalDataTool.py`

**Cypher query:**
```cypher
MERGE (p:Person {name: $name})
SET p.age = $age, p.email = $email, p.address = $address
RETURN p
```

**Address storage:**
- Stored as JSON string: `json.dumps(address)`
- Retrieved as object: `json.loads(address)`
- Handles nested structure gracefully

---

## link_entities

Create a relationship between two entities in the knowledge graph.

### Function Signature

```python
def link_entities(
    from_entity: str,
    to_entity: str,
    relationship_type: str
) -> str
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from_entity` | string | Yes | Source entity name |
| `to_entity` | string | Yes | Target entity name |
| `relationship_type` | string | Yes | Type of relationship (e.g., "FRIEND_OF", "WORKS_WITH") |

### Return Value

Returns: `"{from_entity} and {to_entity} linked with type {relationship_type}"`

### Features

- **Dynamic relationship types**: Any relationship type can be used
- **Directed relationships**: From source to target
- **Creates nodes if missing**: Entities created automatically if they don't exist
- **Multiple relationships**: Can create multiple relationships between same entities

### Example Usage

**Create friendship:**
```json
{
  "tool": "link_entities",
  "arguments": {
    "from_entity": "Alice",
    "to_entity": "Bob",
    "relationship_type": "FRIEND_OF"
  }
}
```

**Create work relationship:**
```json
{
  "tool": "link_entities",
  "arguments": {
    "from_entity": "Alice",
    "to_entity": "Charlie",
    "relationship_type": "WORKS_WITH"
  }
}
```

### Common Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| `FRIEND_OF` | Friendship | Alice → Bob |
| `FAMILY_OF` | Family member | John → Jane |
| `WORKS_WITH` | Colleague | Alice → Charlie |
| `MANAGES` | Manager | Bob → David |
| `KNOWS` | Acquaintance | Alice → Eve |

### Implementation Details

**Source file:** `src/python/tools/linkingTool.py`

**Graph operation:**
```python
graph.add_edge("Person", from_entity, "Person", to_entity, relationship_type)
```

**Cypher equivalent:**
```cypher
MERGE (a:Person {name: $from_entity})
MERGE (b:Person {name: $to_entity})
MERGE (a)-[r:RELATIONSHIP_TYPE]->(b)
RETURN r
```

---

## get_entity_context

Retrieve rich relationship context for an entity, including multi-hop connections.

### Function Signature

```python
def get_entity_context(
    entity_name: str,
    depth: int = 1
) -> str
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `entity_name` | string | Yes | - | Entity name to get context for |
| `depth` | integer | No | 1 | Maximum relationship depth (1-3 recommended) |

### Return Value

Returns a JSON string containing:

```json
{
  "entity": {
    "name": "Alice",
    "type": "Person"
  },
  "nodes": [
    {"name": "Alice", "type": "Person"},
    {"name": "Bob", "type": "Person"},
    {"name": "Charlie", "type": "Person"}
  ],
  "edges": [
    {
      "from": {"name": "Alice", "type": "Person"},
      "to": {"name": "Bob", "type": "Person"},
      "rel": "FRIEND_OF"
    },
    {
      "from": {"name": "Bob", "type": "Person"},
      "to": {"name": "Charlie", "type": "Person"},
      "rel": "WORKS_WITH"
    }
  ],
  "summary": "Alice (Person) -[FRIEND_OF]-> Bob (Person); Bob (Person) -[WORKS_WITH]-> Charlie (Person)"
}
```

### Features

- **Breadth-first traversal**: Explores graph systematically
- **Multi-hop relationships**: Configurable depth (1-3 hops)
- **Structured output**: Nodes, edges, and human-readable summary
- **LLM-friendly**: Summary format optimized for AI context

### Example Usage

**Single-hop context:**
```json
{
  "tool": "get_entity_context",
  "arguments": {
    "entity_name": "Alice"
  }
}
```

**Multi-hop context:**
```json
{
  "tool": "get_entity_context",
  "arguments": {
    "entity_name": "Alice",
    "depth": 2
  }
}
```

### Use Cases

1. **Profile enrichment**: Get all relationships for a person
2. **Network analysis**: Understand connections between people
3. **Recommendation**: Find mutual connections
4. **Context for LLM**: Provide relationship context to AI

### Implementation Details

**Source file:** `src/python/tools/linkingTool.py`

**Algorithm:**
- Breadth-first search (BFS) from entity
- Tracks visited nodes to avoid cycles
- Builds nodes and edges collections
- Generates human-readable summary

**Performance:**
- Depth 1: Direct connections only
- Depth 2: Friends of friends
- Depth 3+: May return large result sets

---

## Error Handling

All tools return descriptive error messages:

| Tool | Error Condition | Message |
|------|-----------------|---------|
| `fetch_person` | Name empty | `"Person not found"` |
| `fetch_person` | Person doesn't exist | `"Person not found"` |
| `update_person` | Name empty | `"Name is required"` |
| `link_entities` | Entity missing | Creates entity automatically |
| `get_entity_context` | Entity doesn't exist | Returns empty result |

## MCP Protocol Integration

### Tool Registration

Tools are registered in `src/python/mcp_server.py`:

```python
from fastmcp import FastMCP
from tools.personalDataTool import fetch_person_data, update_person_data
from tools.linkingTool import link_elements, fetch_entity_context

mcp = FastMCP("personamate")

@mcp.tool()
async def fetch_person(name: str) -> str:
    return fetch_person_data(name)

@mcp.tool()
async def update_person(name: str, **kwargs) -> str:
    return update_person_data(name, **kwargs)

@mcp.tool()
async def link_entities(from_entity: str, to_entity: str, relationship_type: str) -> str:
    return link_elements(from_entity, "Person", to_entity, "Person", relationship_type)

@mcp.tool()
async def get_entity_context(entity_name: str, depth: int = 1) -> str:
    return fetch_entity_context(entity_name, "Person", depth)
```

### Tool Discovery

List available tools via MCP protocol:

```python
# MCP client
result = await client.list_tools()
for tool in result.tools:
    print(f"{tool.name}: {tool.description}")
```

**Output:**
```
fetch_person: Fetch personal information about a person by name from Neo4j
update_person: Create or update a Person node in Neo4j with the provided properties
link_entities: Link two elements in the graph with a given link type
get_entity_context: Fetch structured context for an entity from Neo4j
```

## Testing

All tools have comprehensive test coverage in `test/python/test_tools.py`.

**Run tool tests:**
```bash
docker compose run --rm pytest pytest /app/test/python/test_tools.py -v
```

**Test coverage:**
- 14 tool implementation tests
- CRUD operations
- Edge cases
- Cross-tool workflows

See **[Testing Guide →](../testing.md)** for details.

## Next Steps

- **[MCP Resources →](resources.md)** Learn about MCP resources
- **[Testing →](../testing.md)** Run and write tests
- **[Contributing →](../contributing.md)** Add new tools
