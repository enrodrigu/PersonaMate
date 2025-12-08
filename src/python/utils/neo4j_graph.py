import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase


class Neo4jGraph:
    """Neo4j wrapper for PersonaMate RAG architecture.

    Node Model:
    - Entity: Canonical nodes with unique id (e.g. 'person:john'), type, name
    - DocumentRef: Pointers to MongoDB documents with doc_id, storage URI

    Relationship Model:
    - Typed edges (WORKS_AT, KNOWS, HAS_SKILL, etc.)
    - Metadata: source, confidence, created_at, updated_at
    - HAS_DOCUMENT: Links Entity to DocumentRef

    Constraints/Indexes (auto-created):
    - UNIQUE constraint on Entity.id
    - UNIQUE constraint on DocumentRef.doc_id
    - INDEX on Entity.type
    - INDEX on Entity.name
    """

    def __init__(self, uri: str = None, user: str = None, password: str = None, database: str = None):
        uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = user or os.getenv("NEO4J_USER", "neo4j")
        password = password or os.getenv("NEO4J_PASSWORD", "neo4j")
        database = database or os.getenv("NEO4J_DB", "neo4j")

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self._ensure_constraints()

    def _ensure_constraints(self):
        """Create constraints and indexes if they don't exist."""
        with self._driver.session(database=self._database) as session:
            # Entity ID uniqueness constraint
            session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
            # DocumentRef ID uniqueness constraint
            session.run("CREATE CONSTRAINT docref_id IF NOT EXISTS FOR (d:DocumentRef) REQUIRE d.doc_id IS UNIQUE")
            # Entity type index
            session.run("CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            # Entity name index
            session.run("CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name)")

    def close(self):
        self._driver.close()

    @classmethod
    def load(cls) -> "Neo4jGraph":
        """Factory method to create instance using environment variables."""
        return cls()

    def add_entity(self, entity_id: str, entity_type: str, name: str, **properties):
        """Create or merge an Entity node.

        Args:
            entity_id: Unique namespaced ID (e.g. 'person:john', 'company:acme')
            entity_type: Type of entity (Person, Organization, Product, etc.)
            name: Display name
            **properties: Additional properties to set

        Returns:
            Entity node record
        """
        props = {
            "id": entity_id,
            "type": entity_type,
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
            **properties,
        }

        # Build SET clause for properties
        set_clauses = ", ".join([f"e.{k} = ${k}" for k in props.keys()])
        query = f"MERGE (e:Entity {{id: $id}}) SET {set_clauses} RETURN e"

        with self._driver.session(database=self._database) as session:
            result = session.run(query, **props)
            return result.single()

    def add_document_ref(self, doc_id: str, storage_uri: str, **metadata):
        """Create or update a DocumentRef node pointing to MongoDB.

        Args:
            doc_id: Document identifier (matches MongoDB entity_id)
            storage_uri: Storage URI (e.g. 'mongo://personamate.documents/uuid')
            **metadata: Additional metadata (source, etc.)

        Returns:
            DocumentRef node record
        """
        props = {"doc_id": doc_id, "storage": storage_uri, "updated_at": datetime.utcnow().isoformat(), **metadata}

        set_clauses = ", ".join([f"d.{k} = ${k}" for k in props.keys()])
        query = f"MERGE (d:DocumentRef {{doc_id: $doc_id}}) SET {set_clauses} RETURN d"

        with self._driver.session(database=self._database) as session:
            result = session.run(query, **props)
            return result.single()

    def link_entity_to_document(self, entity_id: str, doc_id: str, **metadata):
        """Create HAS_DOCUMENT relationship from Entity to DocumentRef.

        Args:
            entity_id: Entity node ID
            doc_id: DocumentRef node ID
            **metadata: Relationship metadata

        Returns:
            Relationship record
        """
        props = {"entity_id": entity_id, "doc_id": doc_id, "added_at": datetime.utcnow().isoformat(), **metadata}

        query = """
        MATCH (e:Entity {id: $entity_id})
        MATCH (d:DocumentRef {doc_id: $doc_id})
        MERGE (e)-[r:HAS_DOCUMENT]->(d)
        SET r.added_at = $added_at
        RETURN r
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, **props)
            return result.single()

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        source: str = "user_input",
        confidence: float = 1.0,
        **properties,
    ):
        """Create a typed relationship between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            rel_type: Relationship type (WORKS_AT, KNOWS, LIKES, HAS_SKILL, etc.)
            source: Data source
            confidence: Confidence score (0-1)
            **properties: Additional relationship properties (since, role, etc.)

        Returns:
            Relationship record
        """
        props = {
            "source_id": source_id,
            "target_id": target_id,
            "source": source,
            "confidence": confidence,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            **properties,
        }

        # Build SET clause for relationship properties
        rel_props = {k: v for k, v in props.items() if k not in ["source_id", "target_id"]}
        set_clauses = ", ".join([f"r.{k} = ${k}" for k in rel_props.keys()])

        query = f"""
        MATCH (a:Entity {{id: $source_id}})
        MATCH (b:Entity {{id: $target_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET {set_clauses}
        RETURN r
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, **props)
            return result.single()

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get an Entity node by ID.

        Args:
            entity_id: Entity ID to retrieve

        Returns:
            Entity node dict or None
        """
        query = "MATCH (e:Entity {id: $entity_id}) RETURN e"
        with self._driver.session(database=self._database) as session:
            result = session.run(query, entity_id=entity_id)
            record = result.single()
            return dict(record["e"]) if record else None

    def get_entity_by_name(self, name: str, entity_type: str = None) -> Optional[Dict[str, Any]]:
        """Find entity by name, optionally filtered by type.

        Args:
            name: Entity name to search
            entity_type: Optional type filter

        Returns:
            Entity node dict or None
        """
        if entity_type:
            query = "MATCH (e:Entity {name: $name, type: $entity_type}) RETURN e LIMIT 1"
            params = {"name": name, "entity_type": entity_type}
        else:
            query = "MATCH (e:Entity {name: $name}) RETURN e LIMIT 1"
            params = {"name": name}

        with self._driver.session(database=self._database) as session:
            result = session.run(query, **params)
            record = result.single()
            return dict(record["e"]) if record else None

    def get_neighbors(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all neighboring entities and their relationships.

        Args:
            entity_id: Entity ID to get neighbors for

        Returns:
            List of dicts with neighbor info and relationship details
        """
        query = """
        MATCH (e:Entity {id: $entity_id})-[r]->(n:Entity)
        RETURN type(r) as rel_type, 'out' as direction, n, r
        UNION
        MATCH (e:Entity {id: $entity_id})<-[r]-(n:Entity)
        RETURN type(r) as rel_type, 'in' as direction, n, r
        """

        neighbors = []
        with self._driver.session(database=self._database) as session:
            results = session.run(query, entity_id=entity_id)
            for record in results:
                neighbor = dict(record["n"])
                rel = dict(record["r"])
                neighbors.append(
                    {
                        "entity_id": neighbor.get("id"),
                        "name": neighbor.get("name"),
                        "type": neighbor.get("type"),
                        "rel_type": record["rel_type"],
                        "direction": record["direction"],
                        "relationship": rel,
                    }
                )

        return neighbors

    def get_document_refs(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all DocumentRef nodes linked to an entity.

        Args:
            entity_id: Entity ID

        Returns:
            List of DocumentRef node dicts
        """
        query = """
        MATCH (e:Entity {id: $entity_id})-[:HAS_DOCUMENT]->(d:DocumentRef)
        RETURN d
        """

        refs = []
        with self._driver.session(database=self._database) as session:
            results = session.run(query, entity_id=entity_id)
            for record in results:
                refs.append(dict(record["d"]))

        return refs

    def delete_entity(self, entity_id: str):
        """Delete an Entity node and all its relationships.

        Args:
            entity_id: Entity ID to delete

        Returns:
            True if deleted
        """
        query = "MATCH (e:Entity {id: $entity_id}) DETACH DELETE e"
        with self._driver.session(database=self._database) as session:
            session.run(query, entity_id=entity_id)
            return True

    def delete_document_ref(self, doc_id: str):
        """Delete a DocumentRef node and its relationships.

        Args:
            doc_id: DocumentRef ID to delete

        Returns:
            True if deleted
        """
        query = "MATCH (d:DocumentRef {doc_id: $doc_id}) DETACH DELETE d"
        with self._driver.session(database=self._database) as session:
            session.run(query, doc_id=doc_id)
            return True
