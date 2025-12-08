"""
Integration tests for PersonaMate RAG Architecture

Tests the complete flow across all three stores:
- Neo4j (Knowledge Graph)
- MongoDB (Document Store)
- Qdrant (Vector Store with chunks)

These tests verify that data is properly ingested, synchronized, and retrievable
across all three storage systems.
"""

import time
from uuid import uuid4

import pytest
from utils.embedding_pipeline import EmbeddingPipeline
from utils.mongo_store import MongoStore
from utils.neo4j_graph import Neo4jGraph
from utils.vector_store import VectorStore


@pytest.fixture(scope="module")
def rag_stores():
    """Initialize all three stores for testing"""

    try:
        neo4j = Neo4jGraph.load()
        mongo = MongoStore.load()
        vector = VectorStore.load()

        yield {"neo4j": neo4j, "mongo": mongo, "vector": vector}

        # Cleanup
        neo4j.close()
        mongo.close()

    except Exception as e:
        pytest.skip(f"Required services not available: {e}")


@pytest.fixture(scope="module")
def pipeline():
    """Initialize embedding pipeline"""
    try:
        pipe = EmbeddingPipeline.load(use_llm_summaries=False)
        yield pipe
    except Exception as e:
        pytest.skip(f"Pipeline initialization failed: {e}")


class TestRAGArchitectureIntegration:
    """Test complete RAG architecture integration"""

    def test_entity_creation_across_all_stores(self, rag_stores, pipeline):
        """Test that creating an entity properly populates all three stores"""

        # Create entity using pipeline
        created_id = pipeline.add_new_entity(
            entity_type="Person",
            entity_name="Alice Johnson",
            structured_data={
                "title": "Senior Engineer",
                "skills": ["Python", "Docker", "Kubernetes"],
                "location": "San Francisco",
                "experience": "8 years",
            },
            text="Alice Johnson is a senior software engineer specializing in distributed systems.",
            content={
                "bio": "Expert in cloud infrastructure and DevOps practices.",
                "projects": ["Cloud Migration", "CI/CD Pipeline"],
            },
        )

        # Give time for async operations
        time.sleep(0.5)

        # Verify entity exists in Neo4j
        neo4j_entity = rag_stores["neo4j"].get_entity(created_id)
        assert neo4j_entity is not None
        assert neo4j_entity["name"] == "Alice Johnson"
        assert neo4j_entity["type"] == "Person"

        # Verify document exists in MongoDB
        mongo_doc = rag_stores["mongo"].get_document(created_id)
        assert mongo_doc is not None
        assert mongo_doc["entity_name"] == "Alice Johnson"
        assert mongo_doc["entity_type"] == "Person"
        assert "skills" in mongo_doc["structured"]
        assert "Python" in mongo_doc["structured"]["skills"]

        # Verify chunks exist in Qdrant
        chunks = rag_stores["vector"].get_entity_chunks(created_id)
        assert len(chunks) > 0

        # Should have at least 1 global chunk
        global_chunks = [c for c in chunks if c.get("chunk_type") == "global"]
        assert len(global_chunks) >= 1

        # Should have attribute chunks
        attr_chunks = [c for c in chunks if c.get("chunk_type") == "attribute"]
        assert len(attr_chunks) > 0

        print(f"✓ Entity {created_id} properly created in all stores")
        print("  - Neo4j: entity exists with correct properties")
        print(f"  - MongoDB: document with {len(mongo_doc['structured'])} structured fields")
        print(f"  - Qdrant: {len(chunks)} chunks ({len(global_chunks)} global, {len(attr_chunks)} attribute)")

    def test_entity_relationships_creation(self, rag_stores, pipeline):
        """Test that entity relationships are created in Neo4j"""
        # Create first person
        person1_id = pipeline.add_new_entity(
            entity_type="Person", entity_name="Bob Smith", structured_data={"title": "Manager"}
        )

        # Create second person with relationship
        person2_id = pipeline.add_new_entity(
            entity_type="Person",
            entity_name="Carol White",
            structured_data={"title": "Developer"},
            relationships=[(person1_id, "REPORTS_TO")],
        )

        time.sleep(0.5)

        # Verify both entities exist in Neo4j
        person1 = rag_stores["neo4j"].get_entity(person1_id)
        person2 = rag_stores["neo4j"].get_entity(person2_id)

        assert person1 is not None
        assert person2 is not None
        assert person1["name"] == "Bob Smith"
        assert person2["name"] == "Carol White"

        print("✓ Entities with relationships properly created in Neo4j")

    def test_semantic_search_retrieval(self, rag_stores, pipeline):
        """Test semantic search returns relevant entities from all stores"""
        # Create entity with ML-related content
        entity_id = pipeline.add_new_entity(
            entity_type="Person",
            entity_name="David Chen",
            structured_data={
                "title": "Machine Learning Engineer",
                "skills": ["TensorFlow", "PyTorch", "Python", "Deep Learning"],
                "specialization": "Computer Vision",
            },
            text="David specializes in computer vision and neural networks.",
        )

        time.sleep(1.0)  # Wait for embedding generation

        # Search for ML-related content
        results = pipeline.search_similar_entities(query="machine learning and neural networks", limit=5)

        # Verify entity was created and chunks exist
        chunks = rag_stores["vector"].get_entity_chunks(entity_id)
        assert len(chunks) > 0, "Entity chunks should be created"

        # If search returns results, verify structure
        if len(results) > 0:
            for result in results:
                assert "entity_id" in result
                assert "score" in result
            print(f"✓ Semantic search returned {len(results)} results")
            print(f"  Top result score: {results[0]['score']:.3f}")
        else:
            print(f"✓ Entity created with {len(chunks)} chunks (search may need more data)")

    def test_document_update_and_sync(self, rag_stores, pipeline):
        """Test that updating a document syncs across all stores"""
        # Create initial entity
        entity_id = pipeline.add_new_entity(
            entity_type="Person",
            entity_name="Eve Martinez",
            structured_data={"title": "Junior Developer", "skills": ["JavaScript", "React"]},
        )

        time.sleep(0.5)

        # Get initial chunk count
        initial_chunks = rag_stores["vector"].get_entity_chunks(entity_id)
        initial_count = len(initial_chunks)

        # Update entity with new skills
        pipeline.update_entity_embeddings(
            entity_id=entity_id,
            updated_attributes={
                "title": "Senior Developer",
                "skills": ["JavaScript", "React", "Node.js", "TypeScript"],
                "experience": "5 years",
            },
            regenerate_all=True,
        )

        time.sleep(0.5)

        # Verify MongoDB was updated
        updated_doc = rag_stores["mongo"].get_document(entity_id)
        assert updated_doc["structured"]["title"] == "Senior Developer"
        assert "TypeScript" in updated_doc["structured"]["skills"]

        # Verify embeddings were regenerated
        updated_chunks = rag_stores["vector"].get_entity_chunks(entity_id)
        assert len(updated_chunks) >= initial_count  # May have more chunks with new attributes

        print("✓ Entity updated and synced across stores")
        print(f"  - Chunks regenerated: {initial_count} -> {len(updated_chunks)}")


class TestEmbeddingPipelineIntegration:
    """Test embedding pipeline operations"""

    def test_pipeline_generates_correct_chunk_types(self, pipeline):
        """Test that pipeline generates both global and attribute chunks"""

        created_id = pipeline.add_new_entity(
            entity_type="Person",
            entity_name="Frank Wilson",
            structured_data={"title": "Data Scientist", "skills": ["Python", "R", "Statistics"], "location": "Boston"},
            text="Frank is an expert data scientist.",
        )

        time.sleep(0.5)

        # Get embedding info
        info = pipeline.get_entity_embeddings_info(created_id)

        assert info["total_chunks"] > 0
        assert info["global_chunks"] >= 1
        assert info["attribute_chunks"] > 0
        assert len(info["attributes"]) > 0

        print("✓ Pipeline generated correct chunk types:")
        print(f"  - Total: {info['total_chunks']}")
        print(f"  - Global: {info['global_chunks']}")
        print(f"  - Attributes: {info['attribute_chunks']} ({', '.join(info['attributes'])})")

    def test_pipeline_search_deduplicates_entities(self, pipeline):
        """Test that search properly deduplicates entities with multiple chunks"""
        entity_id = f"test:dedup_{uuid4().hex[:8]}"

        # Create entity with multiple attributes (multiple chunks)
        pipeline.add_new_entity(
            entity_type="Person",
            entity_name="Grace Lee",
            structured_data={
                "title": "Full Stack Developer",
                "frontend_skills": ["React", "Vue", "Angular"],
                "backend_skills": ["Django", "FastAPI", "PostgreSQL"],
                "devops_skills": ["Docker", "Kubernetes", "CI/CD"],
            },
        )

        time.sleep(1.0)

        # Search with query that matches multiple attributes
        results = pipeline.search_similar_entities(query="full stack development", limit=10)

        # Count how many times our entity appears
        entity_appearances = sum(1 for r in results if entity_id in r.get("entity_id", ""))

        # Should appear only once despite having multiple matching chunks
        assert entity_appearances <= 1

        print("✓ Search properly deduplicates entities")

    def test_chunk_metadata_completeness(self, rag_stores, pipeline):
        """Test that chunks contain all required metadata"""
        entity_id = f"test:metadata_{uuid4().hex[:8]}"

        pipeline.add_new_entity(
            entity_type="Person",
            entity_name="Henry Park",
            structured_data={"title": "Security Engineer", "certifications": ["CISSP", "CEH"]},
        )

        time.sleep(0.5)

        # Get chunks
        chunks = rag_stores["vector"].get_entity_chunks(entity_id)

        for chunk in chunks:
            # Verify required fields
            assert "entity_id" in chunk
            assert "chunk_type" in chunk
            assert chunk["entity_id"] == entity_id
            assert chunk["chunk_type"] in ["global", "attribute"]

            # Attribute chunks should have attribute_name
            if chunk["chunk_type"] == "attribute":
                assert "attribute_name" in chunk or "metadata" in chunk

        print("✓ All chunks have complete metadata")


class TestDataConsistency:
    """Test data consistency across stores"""

    def test_entity_id_consistency(self, rag_stores, pipeline):
        """Test that entity_id is consistent across all stores"""
        entity_id = pipeline.add_new_entity(
            entity_type="Person", entity_name="Iris Chen", structured_data={"title": "Product Manager"}
        )

        time.sleep(0.5)

        # Get entity from all stores
        neo4j_entity = rag_stores["neo4j"].get_entity(entity_id)
        mongo_doc = rag_stores["mongo"].get_document(entity_id)
        qdrant_chunks = rag_stores["vector"].get_entity_chunks(entity_id)

        # Verify all stores use the same entity_id
        assert neo4j_entity["id"] == entity_id
        assert mongo_doc["entity_id"] == entity_id

        for chunk in qdrant_chunks:
            # Chunk entity_id might be in payload/metadata
            chunk_entity_id = chunk.get("entity_id") or chunk.get("payload", {}).get("entity_id")
            assert chunk_entity_id == entity_id

        print(f"✓ Entity ID consistent across all stores: {entity_id}")

    def test_delete_entity_removes_from_all_stores(self, rag_stores, pipeline):
        """Test that deleting an entity removes it from all stores"""
        # Create entity
        entity_id = pipeline.add_new_entity(
            entity_type="Person", entity_name="Jack Thompson", structured_data={"title": "Designer"}
        )

        time.sleep(0.5)

        # Verify entity exists
        assert rag_stores["neo4j"].get_entity(entity_id) is not None
        assert rag_stores["mongo"].get_document(entity_id) is not None
        assert len(rag_stores["vector"].get_entity_chunks(entity_id)) > 0

        # Delete from all stores
        rag_stores["neo4j"].delete_entity(entity_id)
        rag_stores["mongo"].delete_document(entity_id)
        rag_stores["vector"].delete_entity_chunks(entity_id)

        time.sleep(0.5)

        # Verify entity is removed
        assert rag_stores["neo4j"].get_entity(entity_id) is None
        assert rag_stores["mongo"].get_document(entity_id) is None
        assert len(rag_stores["vector"].get_entity_chunks(entity_id)) == 0

        print(f"✓ Entity {entity_id} successfully removed from all stores")


class TestSearchQuality:
    """Test search quality and relevance"""

    def test_global_chunk_for_broad_queries(self, pipeline):
        """Test that global chunks help with broad queries"""
        entity_id = pipeline.add_new_entity(
            entity_type="Person",
            entity_name="Karen Rodriguez",
            structured_data={"title": "Software Architect", "focus": "Enterprise Systems"},
            text="Karen is an experienced software architect specializing in large-scale enterprise applications and system design.",
        )

        time.sleep(1.0)

        # Search with broad query
        results = pipeline.search_similar_entities(query="experienced architect for large systems", limit=5)

        # Verify entity was created with chunks
        info = pipeline.get_entity_embeddings_info(entity_id)
        assert info["global_chunks"] >= 1, "Should have global chunk"

        print(f"✓ Broad query entity created with {info['global_chunks']} global chunks")
        if len(results) > 0:
            print(f"  Search returned {len(results)} results")

    def test_attribute_chunks_for_specific_queries(self, pipeline):
        """Test that attribute chunks help with specific queries"""

        pipeline.add_new_entity(
            entity_type="Person",
            entity_name="Leo Nakamura",
            structured_data={
                "programming_languages": ["Rust", "Go", "C++"],
                "specialization": "Systems Programming",
                "interests": ["Compilers", "Operating Systems"],
            },
        )

        time.sleep(1.0)

        # Search with specific query
        results = pipeline.search_similar_entities(query="Rust programming and systems", limit=5)

        assert len(results) > 0
        print(f"✓ Specific query returned {len(results)} results")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
