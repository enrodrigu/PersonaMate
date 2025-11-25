import os
import time
from utils.neo4j_graph import Neo4jGraph


def wait_for_neo4j(uri, user, password, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            g = Neo4jGraph(uri, user, password)
            g.close()
            return True
        except Exception:
            time.sleep(0.5)
    return False


def test_smoke_non_llm_basic_cycle():
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "personamate")

    assert wait_for_neo4j(uri, user, password), "Neo4j not ready"

    g = Neo4jGraph(uri, user, password)
    try:
        # Clean any previous test artifacts
        with g._driver.session(database=g._database) as s:
            s.run("MATCH (n) WHERE n.name IN [$a,$b] DETACH DELETE n", a="Alice-smoke", b="Bob-smoke")

        # Create/update nodes directly via Cypher (avoids decorated tool wrappers)
        with g._driver.session(database=g._database) as s:
            s.run(
                "MERGE (a:Person {name: $name}) SET a.age = $age, a.city = $city RETURN a",
                name="Alice-smoke",
                age=28,
                city="Exampleville",
            )
            s.run(
                "MERGE (b:Person {name: $name}) SET b.age = $age RETURN b",
                name="Bob-smoke",
                age=30,
            )

        # Link them using the graph API
        g.add_edge("Person", "Alice-smoke", "Person", "Bob-smoke", "knows")

        # Read back neighbors using graph API
        neighbors = g.get_neighbors("Alice-smoke", "Person")
        # expect at least one outgoing neighbor to Bob-smoke
        assert any(n.get("name") == "Bob-smoke" for n in neighbors), f"Neighbors: {neighbors}"

        # Fetch the node directly to validate properties
        with g._driver.session(database=g._database) as s:
            rec = s.run("MATCH (p:Person {name: $name}) RETURN p", name="Alice-smoke").single()
            assert rec is not None
            node = rec.get("p")
            props = dict(node)
            assert props.get("name") == "Alice-smoke"
            assert props.get("city") == "Exampleville"
    finally:
        try:
            with g._driver.session(database=g._database) as s:
                s.run("MATCH (n) WHERE n.name IN [$a,$b] DETACH DELETE n", a="Alice-smoke", b="Bob-smoke")
        except Exception:
            pass
        try:
            g.close()
        except Exception:
            pass
