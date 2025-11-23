from neo4j import GraphDatabase
import os


class Neo4jGraph:
    """Simple wrapper around a Neo4j database providing a compact API
    used by the application.

    Methods implemented:
    - add_node(type, name)
    - add_edge(type1, name1, type2, name2, edgetype)
    - get_node(name, type=None)
    - get_neighbors(name, type=None) -> list of neighbor dicts

    This wrapper uses `MERGE` so nodes are created if they don't exist.
    Connection is configured via constructor or environment variables:
    `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DB`.
    """

    def __init__(self, uri: str = None, user: str = None, password: str = None, database: str = None):
        uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = user or os.getenv("NEO4J_USER", "neo4j")
        password = password or os.getenv("NEO4J_PASSWORD", "neo4j")
        database = database or os.getenv("NEO4J_DB", "neo4j")

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    def close(self):
        self._driver.close()

    def add_node(self, type: str, name: str):
        query = (
            f"MERGE (n:`{type}` {{name: $name}}) RETURN id(n) as id, labels(n) as labels, n.name as name"
        )
        with self._driver.session(database=self._database) as session:
            result = session.run(query, name=name)
            return result.single()

    def add_edge(self, type1: str, name1: str, type2: str, name2: str, edgetype: str):
        # Ensure both nodes exist and create relationship
        query = (
            f"MERGE (a:`{type1}` {{name: $name1}})\n"
            f"MERGE (b:`{type2}` {{name: $name2}})\n"
            f"MERGE (a)-[r:`{edgetype}`]->(b)\n"
            "RETURN id(r) as id"
        )
        with self._driver.session(database=self._database) as session:
            result = session.run(query, name1=name1, name2=name2)
            return result.single()

    def get_node(self, name: str, type: str = None):
        if type:
            query = f"MATCH (n:`{type}` {{name: $name}}) RETURN n LIMIT 1"
            with self._driver.session(database=self._database) as session:
                rec = session.run(query, name=name).single()
                return rec["n"] if rec else None
        else:
            query = "MATCH (n {name: $name}) RETURN n LIMIT 1"
            with self._driver.session(database=self._database) as session:
                rec = session.run(query, name=name).single()
                return rec["n"] if rec else None

    def get_neighbors(self, name: str, type: str = None):
        """Return direct neighbors of a node in a structured format.

        Args:
            name: node name to look up
            type: optional label to narrow the starting node

        Returns:
            List[dict]: each dict contains: `direction` ("out"|"in"),
                `rel` (relationship type), `name` (neighbor node name),
                `labels` (neighbor node labels list)
        """
        params = {"name": name}
        if type:
            out_q = f"MATCH (n:`{type}` {{name: $name}})-[r]->(m) RETURN type(r) as rel, m.name as name, labels(m) as labels"
            in_q = f"MATCH (n:`{type}` {{name: $name}})<-[r]-(m) RETURN type(r) as rel, m.name as name, labels(m) as labels"
        else:
            out_q = "MATCH (n {name: $name})-[r]->(m) RETURN type(r) as rel, m.name as name, labels(m) as labels"
            in_q = "MATCH (n {name: $name})<-[r]-(m) RETURN type(r) as rel, m.name as name, labels(m) as labels"

        neighbors = []
        with self._driver.session(database=self._database) as session:
            for rec in session.run(out_q, **params):
                neighbors.append({
                    "direction": "out",
                    "rel": rec.get("rel"),
                    "name": rec.get("name"),
                    "labels": rec.get("labels") or [],
                })
            for rec in session.run(in_q, **params):
                neighbors.append({
                    "direction": "in",
                    "rel": rec.get("rel"),
                    "name": rec.get("name"),
                    "labels": rec.get("labels") or [],
                })
        return neighbors
    # Compatibility helpers used in code that expects save/load on mpg
    def save(self, filename: str = None):
        # No-op: Neo4j persists data for us
        return True

    @classmethod
    def load(cls, filepath: str = None):
        # Create an instance using env vars (or defaults)
        return cls()
