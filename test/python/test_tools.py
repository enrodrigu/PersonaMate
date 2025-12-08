"""
Unit tests for PersonaMate tools.

Basic tests for RAG tools with mocked dependencies
"""

import json
from unittest.mock import Mock, patch

import pytest


class TestRAGQueryTool:
    """Tests for rag_query tool"""

    @patch("tools.personalDataTool.EmbeddingPipeline")
    def test_rag_query_basic(self, mock_pipeline_class):
        """Test basic rag_query functionality"""
        from tools.personalDataTool import rag_query

        # Mock pipeline and search results
        mock_pipeline = Mock()
        mock_pipeline_class.load.return_value = mock_pipeline

        mock_pipeline.search_similar_entities.return_value = [
            {"entity_id": "test:1", "doc_id": "doc_1", "score": 0.85, "chunk_type": "global", "text": "Test result"}
        ]

        mock_pipeline.mongo.get_document.return_value = {"entity_name": "Test Entity", "entity_type": "Person"}

        # Execute
        result = rag_query.invoke({"query": "test query", "limit": 5})
        result_data = json.loads(result)

        # Verify
        assert "results" in result_data
        assert result_data["results_count"] >= 0


class TestIngestDocumentTool:
    """Tests for ingest_document tool"""

    @patch("tools.personalDataTool.EmbeddingPipeline")
    def test_ingest_document_basic(self, mock_pipeline_class):
        """Test basic document ingestion"""
        from tools.personalDataTool import ingest_document

        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline_class.load.return_value = mock_pipeline

        mock_pipeline.add_new_entity.return_value = "doc_123"
        mock_pipeline.vector_store.get_entity_chunks.return_value = [
            {"chunk_type": "global"},
            {"chunk_type": "attribute"},
        ]

        # Execute
        result = ingest_document.invoke(
            {"text": "Test document", "entity_type": "Person", "entity_id": "test:person_1"}
        )
        result_data = json.loads(result)

        # Verify
        assert result_data["success"] is True
        assert result_data["entity_id"] == "test:person_1"
        assert result_data["chunks_created"] == 2


class TestUpdateEntityTool:
    """Tests for update_entity tool"""

    @patch("tools.personalDataTool.EmbeddingPipeline")
    def test_update_entity_basic(self, mock_pipeline_class):
        """Test basic entity update"""
        from tools.personalDataTool import update_entity

        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline_class.load.return_value = mock_pipeline

        mock_pipeline.update_entity_embeddings.return_value = 3
        mock_pipeline.mongo.get_document.return_value = {"entity_id": "test:1", "entity_name": "Updated Entity"}

        # Execute
        result = update_entity.invoke({"entity_id": "test:1", "doc_id": "doc_1", "text": "Updated text"})
        result_data = json.loads(result)

        # Verify
        assert result_data["success"] is True
        assert result_data["chunks_regenerated"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
