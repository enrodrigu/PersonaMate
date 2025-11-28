"""
PersonaMate MCP Server using FastMCP.

This server exposes PersonaMate tools and Neo4j graph context through the Model Context Protocol,
allowing any MCP-compatible client (Claude Desktop, IDEs, etc.) to interact with the knowledge graph.
"""

import logging

from dotenv import load_dotenv
from fastmcp import FastMCP

from tools.personalDataTool import fetch_person_data as _fetch_person_data_tool
from tools.personalDataTool import update_person_data as _update_person_data_tool
from tools.linkingTool import link_elements as _link_elements_tool
from tools.linkingTool import fetch_entity_context as _fetch_entity_context_tool
from utils.neo4j_graph import Neo4jGraph

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personamate.mcp")

# Create the FastMCP server
mcp = FastMCP("PersonaMate")


# ============================================================================
# TOOLS - Expose existing PersonaMate tools through MCP
# ============================================================================

@mcp.tool()
def fetch_person(name: str) -> str:
    """Fetch personal information about a person by name from the knowledge graph.
    
    Args:
        name: The name of the person to look up
        
    Returns:
        A JSON string containing the person's data and related graph context
    """
    logger.info(f"MCP tool invoked: fetch_person(name={name})")
    # The underlying tool is decorated with @tool from langchain, so we invoke it
    result = _fetch_person_data_tool.invoke({"name": name})
    return result


@mcp.tool()
def update_person(name: str, field: str, value: str) -> str:
    """Update a person's information in the knowledge graph.
    
    Args:
        name: The name of the person to update
        field: The field/property to update (e.g., 'age', 'email', 'location')
        value: The new value for the field
        
    Returns:
        Success message
    """
    logger.info(f"MCP tool invoked: update_person(name={name}, field={field}, value={value})")
    result = _update_person_data_tool.invoke({"name": name, "field": field, "value": value})
    return result


@mcp.tool()
def link_entities(element1: str, type1: str, element2: str, type2: str, linktype: str) -> str:
    """Create a relationship between two entities in the knowledge graph.
    
    Args:
        element1: Name of the first entity
        type1: Type of the first entity (e.g., 'Person', 'Organization')
        element2: Name of the second entity
        type2: Type of the second entity
        linktype: Type of relationship (e.g., 'knows', 'likes', 'works_at')
        
    Returns:
        Success message
    """
    logger.info(f"MCP tool invoked: link_entities({element1} -{linktype}-> {element2})")
    result = _link_elements_tool.invoke({
        "element1": element1,
        "type1": type1,
        "element2": element2,
        "type2": type2,
        "linktype": linktype
    })
    return result


@mcp.tool()
def get_entity_context(name: str, entity_type: str = "Person", depth: int = 1) -> str:
    """Get rich context about an entity including its relationships in the graph.
    
    Args:
        name: Name of the entity
        entity_type: Type of entity (default: 'Person')
        depth: How many hops to traverse (default: 1)
        
    Returns:
        JSON string with nodes, edges, and a human-readable summary
    """
    logger.info(f"MCP tool invoked: get_entity_context(name={name}, type={entity_type}, depth={depth})")
    result = _fetch_entity_context_tool.invoke({
        "name": name,
        "type": entity_type,
        "depth": depth
    })
    return result


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
            node_counts = session.run(
                "MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC"
            )
            stats.append("=== Node Counts ===")
            for record in node_counts:
                stats.append(f"{record['label']}: {record['count']}")
            
            # Count relationships by type
            rel_counts = session.run(
                "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC"
            )
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
