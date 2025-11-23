import time
import os
import pytest

from src.python.utils.neo4j_graph import Neo4jGraph


def wait_for_neo4j(uri, user, password, timeout=60):
    from neo4j import GraphDatabase
    start = time.time()
    while time.time() - start < timeout:
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            return True
        except Exception:
            time.sleep(1)
    return False


def test_neo4j_graph_basic_crud():
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j")

    assert wait_for_neo4j(uri, user, password, timeout=60), "Neo4j did not become ready in time"

    g = Neo4jGraph(uri=uri, user=user, password=password)

    a = "IntegrationTestAlice"
    b = "IntegrationTestBob"

    # ensure previous test runs cleaned up
    with g._driver.session(database=g._database) as s:
        s.run("MATCH (n) WHERE n.name IN $names DETACH DELETE n", names=[a, b])

    created = g.add_edge("Person", a, "Person", b, "KNOWS")
    assert created is not None

    node_a = g.get_node(a, "Person")
    node_b = g.get_node(b, "Person")
    assert node_a is not None
    assert node_b is not None

    neighbors = g.get_neighbors(a, "Person")
    # look for an outgoing KNOWS relationship to b
    found = any(n["direction"] == "out" and (n["rel"] == "KNOWS" or n["rel"] == "knows") and n["name"] == b for n in neighbors)
    assert found, f"Expected outgoing KNOWS relationship from {a} to {b}; neighbors: {neighbors}"

    # cleanup
    with g._driver.session(database=g._database) as s:
        s.run("MATCH (n) WHERE n.name IN $names DETACH DELETE n", names=[a, b])

    g.close()
