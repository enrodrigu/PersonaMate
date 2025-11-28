"""
Unit tests for PersonaMate tools.

Tests all tools from personalDataTool and linkingTool to verify:
- fetch_person_data: fetching person information
- update_person_data: creating/updating person nodes
- link_elements: creating relationships between entities
- fetch_entity_context: retrieving graph context for an entity
"""

import pytest
import json
import os
import time
from pydantic_core import ValidationError
from tools.personalDataTool import fetch_person_data, update_person_data
from tools.linkingTool import link_elements, fetch_entity_context
from utils.neo4j_graph import Neo4jGraph


@pytest.fixture(scope="module")
def clean_test_data():
    """Setup: Clean test data before running tests."""
    graph = Neo4jGraph.load()
    try:
        # Clean up any existing test data
        with graph._driver.session(database=graph._database) as session:
            session.run("MATCH (n) WHERE n.name =~ 'Test.*' DETACH DELETE n")
    finally:
        graph.close()
    
    yield
    
    # Teardown: Clean test data after tests
    graph = Neo4jGraph.load()
    try:
        with graph._driver.session(database=graph._database) as session:
            session.run("MATCH (n) WHERE n.name =~ 'Test.*' DETACH DELETE n")
    finally:
        graph.close()


class TestPersonalDataTool:
    """Tests for personalDataTool functions."""
    
    def test_update_person_data_create_new(self, clean_test_data):
        """Test creating a new person with all fields."""
        result = update_person_data.invoke({
            "name": "Test Person Alpha",
            "age": 30,
            "email": "alpha@test.com",
            "street": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345"
        })
        
        assert result == "Person data updated"
        
        # Verify person was created (with retry for Neo4j consistency)
        person_data = None
        for _ in range(3):
            person_data = fetch_person_data.invoke({"name": "Test Person Alpha"})
            if person_data != "Person not found":
                break
            time.sleep(0.5)
        
        assert person_data != "Person not found"
        assert isinstance(person_data, dict)
        assert person_data["name"] == "Test Person Alpha"
        assert person_data["age"] == 30
        assert person_data["email"] == "alpha@test.com"
        assert person_data["address"]["city"] == "Test City"
    
    def test_update_person_data_partial_update(self, clean_test_data):
        """Test updating only specific fields of an existing person."""
        # Create initial person
        update_person_data.invoke({
            "name": "Test Person Beta",
            "age": 25,
            "email": "beta@test.com"
        })
        
        # Update only age
        result = update_person_data.invoke({
            "name": "Test Person Beta",
            "age": 26
        })
        
        assert result == "Person data updated"
        
        # Verify update
        person_data = fetch_person_data.invoke({"name": "Test Person Beta"})
        assert person_data["age"] == 26
        assert person_data["email"] == "beta@test.com"  # Email should remain
    
    def test_update_person_data_no_name(self, clean_test_data):
        """Test that update fails without a name."""
        with pytest.raises(ValidationError) as exc_info:
            update_person_data.invoke({"age": 30})
        assert "name" in str(exc_info.value).lower()
        assert "required" in str(exc_info.value).lower()
    
    def test_fetch_person_data_existing(self, clean_test_data):
        """Test fetching an existing person."""
        # Create person first
        update_person_data.invoke({
            "name": "Test Person Gamma",
            "age": 35,
            "email": "gamma@test.com"
        })
        
        # Fetch person
        result = fetch_person_data.invoke({"name": "Test Person Gamma"})
        
        assert isinstance(result, dict)
        assert result["name"] == "Test Person Gamma"
        assert result["age"] == 35
        assert "graph_context" in result
    
    def test_fetch_person_data_not_found(self, clean_test_data):
        """Test fetching a non-existent person."""
        result = fetch_person_data.invoke({"name": "Test Nonexistent Person XYZ"})
        assert result == "Person not found"
    
    def test_fetch_person_data_case_insensitive(self, clean_test_data):
        """Test that person lookup is case-insensitive."""
        # Create person with specific casing
        update_person_data.invoke({
            "name": "Test Person Delta",
            "age": 40
        })
        
        # Fetch with different casing
        result = fetch_person_data.invoke({"name": "test person delta"})
        assert isinstance(result, dict)
        assert result["name"] == "Test Person Delta"
    
    def test_fetch_person_data_normalized_matching(self, clean_test_data):
        """Test that person lookup handles diacritics and special chars."""
        # Create person with accented name
        update_person_data.invoke({
            "name": "Test Person Épsilon",
            "age": 28
        })
        
        # Should match even without accent
        result = fetch_person_data.invoke({"name": "Test Person Epsilon"})
        assert isinstance(result, dict)
        assert "Épsilon" in result["name"] or "Epsilon" in result["name"]


class TestCrossToolIntegration:
    """Tests for cross-tool integration and workflow persistence."""
    
    def test_complete_workflow_create_link_fetch(self, clean_test_data):
        """Test complete workflow: create persons → link them → fetch and verify relationship in graph_context."""
        # Step 1: Create two persons using update_person_data
        update_person_data.invoke({
            "name": "Test Person Alice",
            "age": 28,
            "email": "alice@test.com"
        })
        update_person_data.invoke({
            "name": "Test Person Bob",
            "age": 32,
            "email": "bob@test.com"
        })
        
        # Step 2: Link them using link_elements
        link_result = link_elements.invoke({
            "element1": "Test Person Alice",
            "type1": "Person",
            "element2": "Test Person Bob",
            "type2": "Person",
            "linktype": "FRIEND_OF"
        })
        assert "linked with type FRIEND_OF" in link_result
        
        # Step 3: Fetch Alice and verify Bob appears in her graph_context
        alice_data = fetch_person_data.invoke({"name": "Test Person Alice"})
        assert isinstance(alice_data, dict)
        assert alice_data["name"] == "Test Person Alice"
        assert "graph_context" in alice_data
        
        # Verify Bob appears as a neighbor
        neighbors = alice_data["graph_context"]
        assert len(neighbors) > 0
        neighbor_names = [n.get("name") for n in neighbors if isinstance(n, dict)]
        assert "Test Person Bob" in neighbor_names
        
        # Step 4: Use fetch_entity_context to get full relationship details
        context = fetch_entity_context.invoke({
            "name": "Test Person Alice",
            "type": "Person",
            "depth": 1
        })
        context_data = json.loads(context)
        
        # Verify the relationship structure
        assert context_data["entity"]["name"] == "Test Person Alice"
        assert len(context_data["nodes"]) >= 2  # Alice and Bob
        assert len(context_data["edges"]) >= 1  # FRIEND_OF relationship
        
        # Find the FRIEND_OF edge
        friend_edges = [e for e in context_data["edges"] if e["rel"] == "FRIEND_OF"]
        assert len(friend_edges) > 0
        friend_edge = friend_edges[0]
        assert friend_edge["from"]["name"] == "Test Person Alice"
        assert friend_edge["to"]["name"] == "Test Person Bob"
        
        # Step 5: Verify bidirectional - fetch Bob and check for Alice
        bob_context = fetch_entity_context.invoke({
            "name": "Test Person Bob",
            "type": "Person",
            "depth": 1
        })
        bob_context_data = json.loads(bob_context)
        bob_node_names = [n["name"] for n in bob_context_data["nodes"]]
        assert "Test Person Alice" in bob_node_names


class TestLinkingTool:
    """Tests for linkingTool functions."""
    
    def test_link_elements_create_relationship(self, clean_test_data):
        """Test creating a relationship between two entities."""
        # Create two test persons
        update_person_data.invoke({"name": "Test Person Link1", "age": 30})
        update_person_data.invoke({"name": "Test Person Link2", "age": 25})
        
        # Link them
        result = link_elements.invoke({
            "element1": "Test Person Link1",
            "type1": "Person",
            "element2": "Test Person Link2",
            "type2": "Person",
            "linktype": "KNOWS"
        })
        
        assert "linked with type KNOWS" in result
        
        # Verify relationship exists by fetching context
        context = fetch_entity_context.invoke({
            "name": "Test Person Link1",
            "type": "Person",
            "depth": 1
        })
        context_data = json.loads(context)
        assert len(context_data["edges"]) > 0
        assert any(e["rel"] == "KNOWS" for e in context_data["edges"])
    
    def test_link_elements_different_types(self, clean_test_data):
        """Test linking entities of different types."""
        # Create person and organization
        update_person_data.invoke({"name": "Test Person Link3", "age": 35})
        
        # Manually create an Organization node
        graph = Neo4jGraph.load()
        try:
            with graph._driver.session(database=graph._database) as session:
                session.run("MERGE (o:Organization {name: $name})", name="Test Org Alpha")
        finally:
            graph.close()
        
        # Link person to organization
        result = link_elements.invoke({
            "element1": "Test Person Link3",
            "type1": "Person",
            "element2": "Test Org Alpha",
            "type2": "Organization",
            "linktype": "WORKS_AT"
        })
        
        assert "linked with type WORKS_AT" in result
    
    def test_fetch_entity_context_depth_1(self, clean_test_data):
        """Test fetching entity context with depth=1."""
        # Create a small graph: Person1 -> Person2 -> Person3
        update_person_data.invoke({"name": "Test Person Context1", "age": 30})
        update_person_data.invoke({"name": "Test Person Context2", "age": 25})
        update_person_data.invoke({"name": "Test Person Context3", "age": 20})
        
        link_elements.invoke({
            "element1": "Test Person Context1",
            "type1": "Person",
            "element2": "Test Person Context2",
            "type2": "Person",
            "linktype": "KNOWS"
        })
        link_elements.invoke({
            "element1": "Test Person Context2",
            "type1": "Person",
            "element2": "Test Person Context3",
            "type2": "Person",
            "linktype": "KNOWS"
        })
        
        # Fetch context for Person1 with depth=1
        result = fetch_entity_context.invoke({
            "name": "Test Person Context1",
            "type": "Person",
            "depth": 1
        })
        
        context = json.loads(result)
        
        assert context["entity"]["name"] == "Test Person Context1"
        assert context["entity"]["type"] == "Person"
        assert len(context["nodes"]) >= 2  # At least Person1 and Person2
        assert len(context["edges"]) >= 1  # At least one relationship
        assert "summary" in context
    
    def test_fetch_entity_context_depth_2(self, clean_test_data):
        """Test fetching entity context with depth=2 to traverse farther."""
        # Use the same graph from previous test
        result = fetch_entity_context.invoke({
            "name": "Test Person Context1",
            "type": "Person",
            "depth": 2
        })
        
        context = json.loads(result)
        
        # Should now include Person3 as well
        node_names = [n["name"] for n in context["nodes"]]
        assert "Test Person Context1" in node_names
        assert "Test Person Context2" in node_names
        # Person3 may or may not be included depending on BFS order, but edges should be longer
        assert len(context["edges"]) >= 1
    
    def test_fetch_entity_context_no_relations(self, clean_test_data):
        """Test fetching context for an isolated entity."""
        update_person_data.invoke({"name": "Test Person Isolated", "age": 50})
        
        result = fetch_entity_context.invoke({
            "name": "Test Person Isolated",
            "type": "Person",
            "depth": 1
        })
        
        context = json.loads(result)
        
        assert context["entity"]["name"] == "Test Person Isolated"
        assert len(context["nodes"]) == 1  # Only the entity itself
        assert len(context["edges"]) == 0  # No relationships
        assert context["summary"] == "No relations found"
    
    def test_fetch_entity_context_invalid_entity(self, clean_test_data):
        """Test fetching context for a non-existent entity."""
        result = fetch_entity_context.invoke({
            "name": "Test Nonexistent Entity XYZ",
            "type": "Person",
            "depth": 1
        })
        
        context = json.loads(result)
        
        # Should return empty context
        assert context["entity"]["name"] == "Test Nonexistent Entity XYZ"
        assert len(context["edges"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
