"""
Unit tests for Embedding Pipeline
"""

from unittest.mock import Mock, patch

import pytest
from utils.chunk_generator import ChunkGenerator
from utils.embedding_pipeline import EmbeddingPipeline


class TestChunkGenerator:
    """Tests for ChunkGenerator"""

    def test_create_global_chunk(self):
        """Test global chunk creation"""
        document = {
            "entity_name": "Alice Johnson",
            "entity_type": "Person",
            "text": "Alice is a data scientist.",
            "structured": {"title": "Data Scientist", "skills": ["Python", "ML"]},
        }

        chunk = ChunkGenerator.create_global_chunk(entity_id="test:1", doc_id="doc_1", document=document)

        assert chunk.chunk_type == "global"
        assert chunk.entity_id == "test:1"
        assert chunk.doc_id == "doc_1"
        assert "Alice Johnson" in chunk.text
        assert "Person" in chunk.text
        assert chunk.attribute_name is None

    def test_create_attribute_chunks_grouped(self):
        """Test attribute chunk creation with grouping"""
        structured_data = {
            "name": "Alice",
            "title": "Data Scientist",
            "skills": ["Python", "ML", "TensorFlow"],
            "location": "San Francisco",
        }

        chunks = ChunkGenerator.create_attribute_chunks(
            entity_id="test:1",
            doc_id="doc_1",
            structured_data=structured_data,
            entity_name="Alice Johnson",
            group_attributes=True,
        )

        assert len(chunks) > 0
        assert all(c.chunk_type == "attribute" for c in chunks)

        # Check for identity group (name, title)
        identity_chunks = [c for c in chunks if c.attribute_name == "identity"]
        assert len(identity_chunks) == 1
        assert "Alice" in identity_chunks[0].text

        # Check for skills group
        skills_chunks = [c for c in chunks if c.attribute_name == "skills"]
        assert len(skills_chunks) == 1
        assert "Python" in skills_chunks[0].text

    def test_create_attribute_chunks_ungrouped(self):
        """Test attribute chunk creation without grouping"""
        structured_data = {"title": "Engineer", "location": "NYC"}

        chunks = ChunkGenerator.create_attribute_chunks(
            entity_id="test:1",
            doc_id="doc_1",
            structured_data=structured_data,
            entity_name="Bob",
            group_attributes=False,
        )

        assert len(chunks) == 2
        attr_names = [c.attribute_name for c in chunks]
        assert "title" in attr_names
        assert "location" in attr_names

    def test_generate_all_chunks(self):
        """Test complete chunk generation"""
        document = {
            "entity_name": "Test User",
            "entity_type": "Person",
            "structured": {"skills": ["Python", "Docker"], "location": "Paris"},
            "text": "Test description",
        }

        chunks = ChunkGenerator.generate_all_chunks(
            entity_id="test:1", doc_id="doc_1", document=document, include_global=True, include_attributes=True
        )

        global_chunks = [c for c in chunks if c.chunk_type == "global"]
        attr_chunks = [c for c in chunks if c.chunk_type == "attribute"]

        assert len(global_chunks) == 1
        assert len(attr_chunks) > 0


class TestEmbeddingPipeline:
    """Tests for EmbeddingPipeline"""

    @pytest.fixture
    def mock_pipeline(self):
        """Create pipeline with mocked stores"""
        with patch("utils.embedding_pipeline.MongoStore") as mock_mongo, patch(
            "utils.embedding_pipeline.Neo4jGraph"
        ) as mock_neo4j, patch("utils.embedding_pipeline.VectorStore") as mock_vector:

            # Setup mocks
            mongo_instance = Mock()
            neo4j_instance = Mock()
            vector_instance = Mock()

            mock_mongo.load.return_value = mongo_instance
            mock_neo4j.load.return_value = neo4j_instance
            mock_vector.load.return_value = vector_instance

            pipeline = EmbeddingPipeline.load(use_llm_summaries=False)

            return pipeline, mongo_instance, neo4j_instance, vector_instance

    def test_process_entity(self, mock_pipeline):
        """Test entity processing"""
        pipeline, mongo, neo4j, vector = mock_pipeline

        # Mock document
        mongo.get_document.return_value = {
            "_id": "doc_1",
            "entity_name": "Alice",
            "entity_type": "Person",
            "structured": {"skills": ["Python"], "title": "Engineer"},
        }

        vector.add_chunks_batch.return_value = ["chunk_1", "chunk_2"]

        result = pipeline.process_entity(entity_id="test:1", generate_global=True, generate_attributes=True)

        assert result["entity_id"] == "test:1"
        assert result["chunk_count"] == 2
        assert "chunk_ids" in result

        # Verify vector store was called
        vector.add_chunks_batch.assert_called_once()

    def test_add_new_entity(self, mock_pipeline):
        """Test adding new entity"""
        pipeline, mongo, neo4j, vector = mock_pipeline

        # Setup mocks for add flow
        mongo.get_document.return_value = {
            "_id": "doc_1",
            "entity_name": "Bob",
            "entity_type": "Person",
            "structured": {"title": "Engineer"},
        }

        vector.add_chunks_batch.return_value = ["chunk_1"]

        entity_id = pipeline.add_new_entity(
            entity_type="Person",
            entity_name="Bob Smith",
            structured_data={"title": "Engineer"},
            content={"bio": "Test"},
            relationships=[("company:1", "WORKS_AT")],
        )

        assert entity_id.startswith("person:")

        # Verify all stores were called
        neo4j.add_entity.assert_called()
        mongo.create_document.assert_called()
        neo4j.add_relationship.assert_called()

    def test_update_entity_embeddings(self, mock_pipeline):
        """Test updating entity embeddings"""
        pipeline, mongo, neo4j, vector = mock_pipeline

        # Setup mocks
        mongo.get_document.return_value = {
            "_id": "doc_1",
            "entity_name": "Alice",
            "entity_type": "Person",
            "structured": {"skills": ["Python", "Rust"]},  # Updated
        }

        mongo.update_document.return_value = True

        neo4j.get_entity.return_value = {"id": "test:1", "type": "Person", "name": "Alice"}

        vector.add_chunks_batch.return_value = ["chunk_1", "chunk_2"]

        result = pipeline.update_entity_embeddings(
            entity_id="test:1", updated_attributes={"skills": ["Python", "Rust"]}, regenerate_all=True
        )

        assert result["chunk_count"] == 2

        # Verify update was called
        mongo.update_document.assert_called_once()
        vector.add_chunks_batch.assert_called()

    def test_search_similar_entities(self, mock_pipeline):
        """Test entity search"""
        pipeline, mongo, neo4j, vector = mock_pipeline

        # Mock search results
        vector.search_chunks.return_value = [
            {"entity_id": "test:1", "chunk_type": "global", "score": 0.85, "text": "Alice is a data scientist..."},
            {
                "entity_id": "test:2",
                "chunk_type": "attribute",
                "attribute_name": "skills",
                "score": 0.78,
                "text": "Skills: Python, ML",
            },
        ]

        # Mock entity documents
        mongo.get_document.side_effect = [
            {"entity_name": "Alice", "entity_type": "Person"},
            {"entity_name": "Bob", "entity_type": "Person"},
        ]

        results = pipeline.search_similar_entities(query="machine learning expert", limit=5)

        assert len(results) == 2
        assert results[0]["entity_name"] == "Alice"
        assert results[0]["score"] == 0.85

    def test_get_entity_embeddings_info(self, mock_pipeline):
        """Test getting embedding info"""
        pipeline, mongo, neo4j, vector = mock_pipeline

        # Mock chunks
        vector.get_entity_chunks.return_value = [
            {"chunk_type": "global", "attribute_name": None},
            {"chunk_type": "attribute", "attribute_name": "skills"},
            {"chunk_type": "attribute", "attribute_name": "location"},
        ]

        info = pipeline.get_entity_embeddings_info("test:1")

        assert info["total_chunks"] == 3
        assert info["global_chunks"] == 1
        assert info["attribute_chunks"] == 2
        assert set(info["attributes"]) == {"skills", "location"}


class TestChunkFormatting:
    """Tests for chunk text formatting"""

    def test_format_single_attribute_list(self):
        """Test formatting list attribute"""
        text = ChunkGenerator._format_single_attribute("skills", ["Python", "Docker", "Kubernetes"], "Alice")

        assert "Alice" in text
        assert "Skills" in text
        assert "Python" in text
        assert "Docker" in text

    def test_format_single_attribute_dict(self):
        """Test formatting dict attribute"""
        text = ChunkGenerator._format_single_attribute(
            "contact", {"email": "alice@example.com", "phone": "123-456"}, "Alice"
        )

        assert "Alice" in text
        assert "Contact" in text
        assert "alice@example.com" in text

    def test_format_attribute_group(self):
        """Test formatting attribute group"""
        text = ChunkGenerator._format_attribute_group(
            "skills", {"skills": ["Python", "ML"], "expertise": ["Deep Learning"]}, "Alice"
        )

        assert "Alice" in text
        assert "Skills" in text
        assert "Python" in text
        assert "Deep Learning" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
