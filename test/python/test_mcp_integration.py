"""
Integration tests for PersonaMate MCP Server.

Tests the MCP server endpoints using the MCP SDK client to verify:
- Server initialization and connection
- Tool discovery and invocation
- Resource and prompt endpoints
- Neo4j integration through MCP
"""

import os

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure pytest to use asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def neo4j_uri():
    """Get Neo4j connection URI from environment."""
    return os.getenv("NEO4J_URI", "bolt://localhost:7687")


@pytest.fixture
def neo4j_user():
    """Get Neo4j username from environment."""
    return os.getenv("NEO4J_USER", "neo4j")


@pytest.fixture
def neo4j_password():
    """Get Neo4j password from environment."""
    return os.getenv("NEO4J_PASSWORD", "neo4j-pass")


@pytest.mark.asyncio
async def test_mcp_server_initialization():
    """Test that the MCP server starts and responds to initialization."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.python.mcp_server"],
        env={
            "PYTHONPATH": "/app",
            "NEO4J_URI": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
            "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "neo4j-pass"),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            result = await session.initialize()

            # Server should respond with initialization result
            assert result is not None
            assert result.protocolVersion is not None


@pytest.mark.asyncio
async def test_mcp_list_tools():
    """Test listing available tools from the MCP server."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.python.mcp_server"],
        env={
            "PYTHONPATH": "/app",
            "NEO4J_URI": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
            "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "neo4j-pass"),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools_result = await session.list_tools()
            tools = tools_result.tools

            # Verify expected tools are present
            tool_names = [tool.name for tool in tools]

            assert "fetch_person" in tool_names
            assert "update_person" in tool_names
            assert "link_entities" in tool_names
            assert "get_entity_context" in tool_names


@pytest.mark.asyncio
async def test_mcp_call_fetch_person_tool():
    """Test calling the fetch_person tool through MCP."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.python.mcp_server"],
        env={
            "PYTHONPATH": "/app",
            "NEO4J_URI": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
            "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "neo4j-pass"),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call fetch_person tool
            result = await session.call_tool("fetch_person", arguments={"name": "Test User"})

            # Should return result (even if person doesn't exist, should return valid response)
            assert result is not None
            assert len(result.content) > 0


@pytest.mark.asyncio
async def test_mcp_list_resources():
    """Test listing available resources from the MCP server."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.python.mcp_server"],
        env={
            "PYTHONPATH": "/app",
            "NEO4J_URI": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
            "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "neo4j-pass"),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List resources
            resources_result = await session.list_resources()
            resources = resources_result.resources

            # Verify expected resources are present
            resource_uris = [str(resource.uri) for resource in resources]

            assert "graph://persons" in resource_uris
            assert "graph://relationships" in resource_uris
            assert "graph://stats" in resource_uris


@pytest.mark.asyncio
async def test_mcp_list_prompts():
    """Test listing available prompts from the MCP server."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.python.mcp_server"],
        env={
            "PYTHONPATH": "/app",
            "NEO4J_URI": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
            "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "neo4j-pass"),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List prompts
            prompts_result = await session.list_prompts()
            prompts = prompts_result.prompts

            # Verify expected prompts are present
            prompt_names = [prompt.name for prompt in prompts]

            assert "person_lookup_prompt" in prompt_names
            assert "relationship_analysis_prompt" in prompt_names


@pytest.mark.asyncio
async def test_mcp_read_graph_stats_resource():
    """Test reading the graph statistics resource."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.python.mcp_server"],
        env={
            "PYTHONPATH": "/app",
            "NEO4J_URI": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
            "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "neo4j-pass"),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Read graph stats resource
            result = await session.read_resource("graph://stats")

            # Should return schema information
            assert result is not None
            assert len(result.contents) > 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
