"""
PersonaMate MCP Server using FastMCP.

This server exposes PersonaMate RAG tools through the Model Context Protocol,
allowing any MCP-compatible client to interact with the knowledge graph.
"""

import logging

from dotenv import load_dotenv
from fastmcp import FastMCP
from tools.personalDataTool import ingest_document as _ingest_document_tool
from tools.personalDataTool import rag_query as _rag_query_tool
from tools.personalDataTool import update_entity as _update_entity_tool
from utils.neo4j_graph import Neo4jGraph

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personamate.mcp")

# Create the FastMCP server
mcp = FastMCP("PersonaMate")


# ============================================================================
# TOOLS - Expose existing PersonaMate tools through MCP
# ============================================================================
# TOOLS - RAG Architecture Tools
# ============================================================================


@mcp.tool()
def rag_query(query: str, entity_type: str = None, limit: int = 5) -> str:
    """Retrieve information from the RAG system using semantic search.

    Args:
        query: Natural language query (e.g., "Python developers in Paris")
        entity_type: Optional filter by type (Person, Organization, etc.)
        limit: Maximum number of results (default: 5)

    Returns:
        JSON string with search results including entity data and relationships
    """
    logger.info(f"MCP tool invoked: rag_query(query={query}, type={entity_type})")
    result = _rag_query_tool.invoke({"query": query, "entity_type": entity_type, "limit": limit})
    return result


@mcp.tool()
def ingest_document(text: str, entity_type: str, entity_name: str, metadata: str = None) -> str:
    """Ingest a text document about people, organizations, or other entities.

    Args:
        text: Document text with entity information
        entity_type: Type of entity (Person, Organization, Project, etc.)
        entity_name: Name of the entity
        metadata: Optional JSON string with metadata (tags, source, etc.)

    Returns:
        JSON string with created entity_id and confirmation
    """
    logger.info(f"MCP tool invoked: ingest_document({entity_name}, type={entity_type})")
    result = _ingest_document_tool.invoke(
        {"text": text, "entity_type": entity_type, "entity_name": entity_name, "metadata": metadata}
    )
    return result


@mcp.tool()
def update_entity(entity_id: str, content: str = None, metadata: str = None, add_relationship: str = None) -> str:
    """Update an existing entity in the knowledge graph.

    Args:
        entity_id: Unique entity identifier (e.g., "person:abc123")
        content: Optional JSON string with content updates
        metadata: Optional JSON string with metadata updates
        add_relationship: Optional JSON with relationship info

    Returns:
        JSON string with updated entity data
    """
    logger.info(f"MCP tool invoked: update_entity({entity_id})")
    result = _update_entity_tool.invoke(
        {"entity_id": entity_id, "content": content, "metadata": metadata, "add_relationship": add_relationship}
    )
    return result


# Note: link_entities and get_entity_context removed - use RAG tools instead


# ============================================================================
# RESOURCES - Provide read-only access to graph data
# ============================================================================


@mcp.resource("graph://persons")
def list_all_persons() -> str:
    """List all persons in the knowledge graph.

    Returns a list of all person names currently stored.
    """
    logger.info("MCP resource accessed: graph://persons")
    graph = Neo4jGraph.load()
    try:
        query = "MATCH (p:Person) RETURN p.name as name ORDER BY name"
        with graph._driver.session(database=graph._database) as session:
            results = session.run(query)
            names = [record["name"] for record in results if record["name"]]
            return "\n".join(names) if names else "No persons found"
    except Exception as e:
        logger.error(f"Error listing persons: {e}")
        return f"Error: {str(e)}"
    finally:
        try:
            graph.close()
        except Exception:
            pass


@mcp.resource("graph://relationships")
def list_all_relationships() -> str:
    """List all relationships in the knowledge graph.

    Returns a summary of all edges/relationships.
    """
    logger.info("MCP resource accessed: graph://relationships")
    graph = Neo4jGraph.load()
    try:
        query = """
        MATCH (a)-[r]->(b)
        RETURN labels(a)[0] as type1, a.name as name1,
               type(r) as rel,
               labels(b)[0] as type2, b.name as name2
        LIMIT 100
        """
        with graph._driver.session(database=graph._database) as session:
            results = session.run(query)
            lines = []
            for record in results:
                lines.append(
                    f"{record['name1']} ({record['type1']}) "
                    f"-[{record['rel']}]-> "
                    f"{record['name2']} ({record['type2']})"
                )
            return "\n".join(lines) if lines else "No relationships found"
    except Exception as e:
        logger.error(f"Error listing relationships: {e}")
        return f"Error: {str(e)}"
    finally:
        try:
            graph.close()
        except Exception:
            pass


@mcp.resource("graph://stats")
def graph_statistics() -> str:
    """Get statistics about the knowledge graph.

    Returns counts of nodes and relationships by type.
    """
    logger.info("MCP resource accessed: graph://stats")
    graph = Neo4jGraph.load()
    try:
        stats = []
        with graph._driver.session(database=graph._database) as session:
            # Count nodes by label
            node_counts = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC")
            stats.append("=== Node Counts ===")
            for record in node_counts:
                stats.append(f"{record['label']}: {record['count']}")

            # Count relationships by type
            rel_counts = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC")
            stats.append("\n=== Relationship Counts ===")
            for record in rel_counts:
                stats.append(f"{record['type']}: {record['count']}")

        return "\n".join(stats) if len(stats) > 2 else "Graph is empty"
    except Exception as e:
        logger.error(f"Error getting graph stats: {e}")
        return f"Error: {str(e)}"
    finally:
        try:
            graph.close()
        except Exception:
            pass


# ============================================================================
# PROMPTS - Provide reusable prompt templates
# ============================================================================


@mcp.prompt()
def person_lookup_prompt(name: str) -> str:
    """Generate a prompt for looking up comprehensive information about a person.

    Args:
        name: Name of the person to look up
    """
    return f"""Please look up all available information about {name} and provide a comprehensive summary.

Use the fetch_person tool to get their basic information, then use get_entity_context to understand their relationships and connections.

Format the response as:
1. Basic Information (name, age, location, etc.)
2. Relationships (who they know, what they like, where they work, etc.)
3. Context (any additional relevant information from the graph)
"""


@mcp.prompt()
def relationship_analysis_prompt(person1: str, person2: str) -> str:
    """Generate a prompt for analyzing relationships between two people.

    Args:
        person1: First person's name
        person2: Second person's name
    """
    return f"""Analyze the relationship between {person1} and {person2}.

Steps:
1. Use get_entity_context for both {person1} and {person2} with depth=2
2. Look for direct connections between them
3. Look for mutual connections (people/things they both know)
4. Summarize how they might be connected

Provide:
- Direct relationships if any
- Mutual connections
- Degree of separation
- Suggested relationship context
"""


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server
    # For stdio transport (default for MCP): python mcp_server.py
    # For SSE transport: python mcp_server.py --transport sse --port 8080
    logger.info("Starting PersonaMate MCP Server...")
    mcp.run()
