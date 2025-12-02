# MCP Resources Reference

PersonaMate exposes read-only data through MCP resources. Resources provide structured access to graph data without modifying it, making them ideal for querying and exploration.

!!! info "MCP Protocol Interface"
    Resources are accessed via Model Context Protocol, not HTTP URLs. The `graph://` URI scheme is an MCP resource identifier, not a web URL. See [MCP Protocol](../mcp.md) for details.

## Resource Overview

| Resource URI | Description | Content Type | Format |
|-------------|-------------|--------------|--------|
| `graph://persons` | List all persons | text/plain | JSON array |
| `graph://relationships` | List all relationships | text/plain | JSON array |
| `graph://stats` | Graph statistics | text/plain | JSON object |

## graph://persons

Retrieve a list of all persons in the knowledge graph.

### URI

```
graph://persons
```

### Response Format

Returns a JSON array of person objects:

```json
[
  {
    "name": "Alice Johnson",
    "age": 35,
    "email": "alice@example.com",
    "phone": "555-0101",
    "address": {
      "street": "456 Oak Ave",
      "city": "Cambridge",
      "state": "MA",
      "zip": "02139"
    }
  },
  {
    "name": "Bob Smith",
    "age": 42,
    "email": "bob@example.com",
    "phone": "555-0102",
    "address": {
      "street": "789 Pine St",
      "city": "Boston",
      "state": "MA",
      "zip": "02101"
    }
  }
]
```

### MCP Client Usage

```python
# Read resource
result = await client.read_resource("graph://persons")
persons = json.loads(result.contents[0].text)

print(f"Found {len(persons)} persons")
for person in persons:
    print(f"- {person['name']} (age {person['age']})")
```

### Cypher Query

Internally executes:

```cypher
MATCH (p:Person)
RETURN p.name as name,
       p.age as age,
       p.email as email,
       p.phone as phone,
       p.address as address
ORDER BY p.name
```

### Use Cases

- **Directory listing**: Display all contacts
- **Search index**: Build searchable person list
- **Export data**: Backup or migrate persons
- **Analytics**: Analyze person demographics

### Implementation Details

**Source:** `src/python/mcp_server.py`

```python
@mcp.resource("graph://persons")
def get_all_persons() -> str:
    """List all persons in the graph"""
    g = Neo4jGraph.load()
    try:
        with g._driver.session(database=g._database) as session:
            result = session.run("MATCH (p:Person) RETURN p ORDER BY p.name")
            persons = []
            for record in result:
                node = record["p"]
                person_dict = dict(node)
                # Parse JSON address if stored as string
                if "address" in person_dict and isinstance(person_dict["address"], str):
                    person_dict["address"] = json.loads(person_dict["address"])
                persons.append(person_dict)
            return json.dumps(persons, indent=2)
    finally:
        g.close()
```

---

## graph://relationships

Retrieve all relationships between entities in the knowledge graph.

### URI

```
graph://relationships
```

### Response Format

Returns a JSON array of relationship objects:

```json
[
  {
    "from": "Alice Johnson",
    "to": "Bob Smith",
    "type": "FRIEND_OF",
    "properties": {}
  },
  {
    "from": "Bob Smith",
    "to": "Charlie Davis",
    "type": "WORKS_WITH",
    "properties": {
      "since": "2020-01-15",
      "department": "Engineering"
    }
  },
  {
    "from": "Alice Johnson",
    "to": "Charlie Davis",
    "type": "MANAGES",
    "properties": {}
  }
]
```

### MCP Client Usage

```python
# Read resource
result = await client.read_resource("graph://relationships")
relationships = json.loads(result.contents[0].text)

print(f"Found {len(relationships)} relationships")
for rel in relationships:
    print(f"- {rel['from']} -[{rel['type']}]-> {rel['to']}")
```

### Cypher Query

Internally executes:

```cypher
MATCH (a:Person)-[r]->(b:Person)
RETURN a.name as from,
       type(r) as type,
       b.name as to,
       properties(r) as properties
ORDER BY a.name, type(r), b.name
```

### Use Cases

- **Network visualization**: Build relationship graphs
- **Social network analysis**: Analyze connection patterns
- **Relationship discovery**: Find indirect connections
- **Data export**: Backup relationship data

### Common Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| `FRIEND_OF` | Personal friendship | Alice → Bob |
| `FAMILY_OF` | Family connection | John → Jane |
| `WORKS_WITH` | Professional colleague | Bob → Charlie |
| `MANAGES` | Manager-report | Alice → Charlie |
| `KNOWS` | General acquaintance | Any → Any |
| `COLLEAGUE_OF` | Work relationship | Team members |
| `PARTNER_OF` | Business partner | Business relations |

### Implementation Details

**Source:** `src/python/mcp_server.py`

```python
@mcp.resource("graph://relationships")
def get_all_relationships() -> str:
    """List all relationships in the graph"""
    g = Neo4jGraph.load()
    try:
        with g._driver.session(database=g._database) as session:
            result = session.run("""
                MATCH (a:Person)-[r]->(b:Person)
                RETURN a.name as from,
                       type(r) as type,
                       b.name as to,
                       properties(r) as properties
                ORDER BY a.name, type(r), b.name
            """)
            relationships = []
            for record in result:
                relationships.append({
                    "from": record["from"],
                    "to": record["to"],
                    "type": record["type"],
                    "properties": dict(record["properties"])
                })
            return json.dumps(relationships, indent=2)
    finally:
        g.close()
```

---

## graph://stats

Get statistical information about the knowledge graph.

### URI

```
graph://stats
```

### Response Format

Returns a JSON object with graph statistics:

```json
{
  "persons": {
    "total": 150,
    "with_email": 142,
    "with_phone": 138,
    "with_address": 145,
    "avg_age": 35.4
  },
  "relationships": {
    "total": 324,
    "by_type": {
      "FRIEND_OF": 180,
      "WORKS_WITH": 95,
      "FAMILY_OF": 32,
      "MANAGES": 17
    }
  },
  "network": {
    "avg_connections_per_person": 2.16,
    "most_connected": {
      "name": "Alice Johnson",
      "connections": 12
    },
    "isolated_persons": 5
  },
  "metadata": {
    "database": "neo4j",
    "last_updated": "2024-01-15T10:30:00Z"
  }
}
```

### MCP Client Usage

```python
# Read resource
result = await client.read_resource("graph://stats")
stats = json.loads(result.contents[0].text)

print(f"Total persons: {stats['persons']['total']}")
print(f"Total relationships: {stats['relationships']['total']}")
print(f"Most connected: {stats['network']['most_connected']['name']}")
```

### Cypher Queries

Multiple queries to gather statistics:

**Person count:**
```cypher
MATCH (p:Person) RETURN count(p) as total
```

**Relationship counts by type:**
```cypher
MATCH ()-[r]->()
RETURN type(r) as type, count(r) as count
ORDER BY count DESC
```

**Most connected person:**
```cypher
MATCH (p:Person)-[r]-()
RETURN p.name as name, count(r) as connections
ORDER BY connections DESC
LIMIT 1
```

### Use Cases

- **Dashboard metrics**: Display key statistics
- **Health monitoring**: Track graph growth
- **Data quality**: Identify incomplete records
- **Analytics**: Understand network structure

### Implementation Details

**Source:** `src/python/mcp_server.py`

```python
@mcp.resource("graph://stats")
def get_graph_stats() -> str:
    """Get statistical information about the graph"""
    g = Neo4jGraph.load()
    try:
        with g._driver.session(database=g._database) as session:
            # Count persons
            person_count = session.run("MATCH (p:Person) RETURN count(p) as total").single()["total"]

            # Count relationships by type
            rel_result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            rel_by_type = {rec["type"]: rec["count"] for rec in rel_result}

            # Most connected person
            most_connected = session.run("""
                MATCH (p:Person)-[r]-()
                RETURN p.name as name, count(r) as connections
                ORDER BY connections DESC
                LIMIT 1
            """).single()

            stats = {
                "persons": {"total": person_count},
                "relationships": {
                    "total": sum(rel_by_type.values()),
                    "by_type": rel_by_type
                },
                "network": {
                    "most_connected": dict(most_connected) if most_connected else None
                }
            }
            return json.dumps(stats, indent=2)
    finally:
        g.close()
```

---

## MCP Prompts

PersonaMate also exposes predefined prompts for common operations.

### person_lookup_prompt

Generate a comprehensive prompt for looking up person information.

**Prompt name:** `person_lookup_prompt`

**Arguments:**
- `name` (string, required): Person's name to look up

**Template:**
```
Please fetch comprehensive information about {name}, including:
- Basic details (age, email, phone, address)
- All relationships and connections
- Context about their network

Use the fetch_person and get_entity_context tools to gather complete information.
```

**Usage:**
```python
result = await client.get_prompt("person_lookup_prompt", arguments={"name": "Alice Johnson"})
prompt_text = result.messages[0].content.text
```

### relationship_analysis_prompt

Generate a prompt for analyzing relationships between people.

**Prompt name:** `relationship_analysis_prompt`

**Arguments:**
- `person1` (string, required): First person's name
- `person2` (string, required): Second person's name

**Template:**
```
Analyze the relationship between {person1} and {person2}:
- Direct relationships
- Mutual connections
- Shortest path between them
- Shared attributes or interests

Use get_entity_context for both persons and identify connections.
```

**Usage:**
```python
result = await client.get_prompt(
    "relationship_analysis_prompt",
    arguments={"person1": "Alice", "person2": "Bob"}
)
prompt_text = result.messages[0].content.text
```

---

## Resource Discovery

### List All Resources

```python
# MCP client
result = await client.list_resources()
for resource in result.resources:
    print(f"{resource.uri}: {resource.name}")
    print(f"  {resource.description}")
    print(f"  MIME: {resource.mimeType}")
```

**Output:**
```
graph://persons: All Persons
  List all persons in the knowledge graph
  MIME: text/plain

graph://relationships: All Relationships
  List all relationships between entities
  MIME: text/plain

graph://stats: Graph Statistics
  Statistical information about the graph
  MIME: text/plain
```

### Resource Templates

Resources can use URI templates for parameterized access (future enhancement):

```
graph://person/{name}        # Specific person
graph://person/{name}/friends # Person's friends
graph://search?q={query}     # Search persons
```

---

## Testing

Resources are tested in `test/python/test_mcp_integration.py`.

**Test resource reading:**
```python
@pytest.mark.asyncio
async def test_read_resource():
    """Test reading a resource via MCP"""
    result = await client.read_resource("graph://persons")
    assert len(result.contents) > 0
    assert result.contents[0].mimeType == "text/plain"

    # Parse and validate
    persons = json.loads(result.contents[0].text)
    assert isinstance(persons, list)
```

**Run resource tests:**
```bash
docker compose run --rm pytest pytest /app/test/python/test_mcp_integration.py::test_read_resource -v
```

---

## Performance Considerations

### graph://persons

- **Query complexity:** O(n) where n = number of persons
- **Memory usage:** Loads all persons into memory
- **Optimization:** Add pagination for large graphs (>1000 persons)

**Recommended limit:**
```cypher
MATCH (p:Person) RETURN p ORDER BY p.name LIMIT 100
```

### graph://relationships

- **Query complexity:** O(n) where n = number of relationships
- **Memory usage:** Loads all relationships into memory
- **Optimization:** Filter by relationship type or person

**Filtered query:**
```cypher
MATCH (a:Person)-[r:FRIEND_OF]->(b:Person)
RETURN a.name, type(r), b.name
```

### graph://stats

- **Query complexity:** Multiple O(n) queries
- **Memory usage:** Minimal (aggregates only)
- **Caching:** Consider caching stats for 5-10 minutes

---

## Error Handling

Resources return empty results or error messages:

| Condition | Behavior |
|-----------|----------|
| Empty graph | Returns empty array `[]` |
| Database error | Returns error message as text |
| Connection failure | MCP client raises exception |

---

## Next Steps

- **[MCP Tools →](tools.md)** Learn about MCP tools
- **[Testing →](../testing.md)** Test resources
- **[Contributing →](../contributing.md)** Add new resources
