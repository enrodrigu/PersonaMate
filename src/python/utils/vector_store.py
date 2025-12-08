"""
Qdrant Vector Store for PersonaMate RAG Architecture

Stores embeddings of entity documents for semantic search.
Each vector is linked to a Neo4j node and MongoDB document via entity_id.

Vector Structure:
- id: entity_id (UUID)
- vector: embedding (384-dimensional for all-MiniLM-L6-v2)
- payload: {
    "entity_id": "uuid",
    "entity_type": "Person",
    "entity_name": "John Doe",
    "text": "original text that was embedded",
    "created_at": "ISO datetime"
  }
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer


class VectorStore:
    """Vector store for semantic search using Qdrant."""

    # Default embedding model - lightweight and fast
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    VECTOR_SIZE = 384  # Dimension for all-MiniLM-L6-v2

    def __init__(self, uri: str = None, collection_name: str = "entity_embeddings", embedding_model: str = None):
        """Initialize Qdrant connection.

        Args:
            uri: Qdrant connection URI (default from QDRANT_URI env)
            collection_name: Collection name for vectors
            embedding_model: SentenceTransformer model name
        """
        self.uri = uri or os.getenv("QDRANT_URI", "http://localhost:6333")
        self.collection_name = collection_name
        self.model_name = embedding_model or self.DEFAULT_MODEL

        self._client: Optional[QdrantClient] = None
        self._model: Optional[SentenceTransformer] = None

    def _connect(self):
        """Lazy connection to Qdrant and load embedding model."""
        if self._client is None:
            self._client = QdrantClient(url=self.uri)

            # Create collection if it doesn't exist
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.VECTOR_SIZE, distance=Distance.COSINE),
                )

        if self._model is None:
            self._model = SentenceTransformer(self.model_name)

    def close(self):
        """Close Qdrant connection."""
        if self._client:
            self._client.close()
            self._client = None
        # Model stays in memory (can be reused)

    @classmethod
    def load(cls) -> "VectorStore":
        """Factory method to create and connect store."""
        store = cls()
        store._connect()
        return store

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding
        """
        self._connect()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def add_chunk_vector(
        self,
        chunk_id: str,
        entity_id: str,
        doc_id: str,
        chunk_type: str,
        text: str,
        attribute_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a chunk-specific vector (global or attribute).

        Args:
            chunk_id: Unique identifier for this chunk
            entity_id: Entity identifier
            doc_id: Document identifier in MongoDB
            chunk_type: Type of chunk ('global' or 'attribute')
            text: Text to embed
            attribute_name: Name of attribute if chunk_type is 'attribute'
            metadata: Additional metadata

        Returns:
            The chunk_id
        """
        self._connect()

        # Generate embedding
        vector = self._generate_embedding(text)

        # Prepare payload with chunk-specific metadata
        payload = {
            "chunk_id": chunk_id,
            "entity_id": entity_id,
            "doc_id": doc_id,
            "chunk_type": chunk_type,
            "text": text,
            "created_at": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }

        if attribute_name:
            payload["attribute_name"] = attribute_name

        # Create point
        point = PointStruct(id=chunk_id, vector=vector, payload=payload)

        self._client.upsert(collection_name=self.collection_name, points=[point])

        return chunk_id

    def add_chunks_batch(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Add multiple chunks in batch for efficiency.

        Args:
            chunks: List of chunk dicts with keys:
                - chunk_id, entity_id, doc_id, chunk_type, text
                - optional: attribute_name, metadata

        Returns:
            List of chunk_ids
        """
        self._connect()

        points = []
        chunk_ids = []

        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", str(uuid4()))
            text = chunk["text"]

            # Generate embedding
            vector = self._generate_embedding(text)

            # Prepare payload
            payload = {
                "chunk_id": chunk_id,
                "entity_id": chunk["entity_id"],
                "doc_id": chunk["doc_id"],
                "chunk_type": chunk["chunk_type"],
                "text": text,
                "created_at": datetime.utcnow().isoformat(),
            }

            if "attribute_name" in chunk:
                payload["attribute_name"] = chunk["attribute_name"]

            if "metadata" in chunk:
                payload.update(chunk["metadata"])

            points.append(PointStruct(id=chunk_id, vector=vector, payload=payload))

            chunk_ids.append(chunk_id)

        # Batch upsert
        if points:
            self._client.upsert(collection_name=self.collection_name, points=points)

        return chunk_ids

    def search_chunks(
        self,
        query: str,
        entity_id: Optional[str] = None,
        chunk_type: Optional[str] = None,
        attribute_name: Optional[str] = None,
        limit: int = 5,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Search for chunks with optional filters.

        Args:
            query: Search query text
            entity_id: Filter by specific entity
            chunk_type: Filter by chunk type ('global' or 'attribute')
            attribute_name: Filter by specific attribute name
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of matching chunks with scores
        """
        self._connect()

        # Generate query embedding
        query_vector = self._generate_embedding(query)

        # Build filters
        filter_conditions = []

        if entity_id:
            filter_conditions.append(FieldCondition(key="entity_id", match=MatchValue(value=entity_id)))

        if chunk_type:
            filter_conditions.append(FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type)))

        if attribute_name:
            filter_conditions.append(FieldCondition(key="attribute_name", match=MatchValue(value=attribute_name)))

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Search
        results = self._client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
        )

        # Format results
        return [
            {
                "chunk_id": hit.payload.get("chunk_id"),
                "entity_id": hit.payload.get("entity_id"),
                "doc_id": hit.payload.get("doc_id"),
                "chunk_type": hit.payload.get("chunk_type"),
                "attribute_name": hit.payload.get("attribute_name"),
                "score": hit.score,
                "text": hit.payload.get("text"),
                "payload": hit.payload,
            }
            for hit in results
        ]

    def get_entity_chunks(self, entity_id: str, chunk_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all chunks for a specific entity.

        Args:
            entity_id: Entity identifier
            chunk_type: Optional filter by chunk type

        Returns:
            List of all chunks for the entity
        """
        self._connect()

        filter_conditions = [FieldCondition(key="entity_id", match=MatchValue(value=entity_id))]

        if chunk_type:
            filter_conditions.append(FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type)))

        results = self._client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(must=filter_conditions),
            limit=100,  # Reasonable limit for one entity
            with_vectors=False,
        )

        return [
            {
                "chunk_id": point.payload.get("chunk_id"),
                "chunk_type": point.payload.get("chunk_type"),
                "attribute_name": point.payload.get("attribute_name"),
                "text": point.payload.get("text"),
                "payload": point.payload,
            }
            for point in results[0]
        ]

    def delete_entity_chunks(self, entity_id: str, chunk_type: Optional[str] = None) -> int:
        """Delete all chunks for an entity.

        Args:
            entity_id: Entity identifier
            chunk_type: Optional filter to delete only specific type

        Returns:
            Number of chunks deleted
        """
        self._connect()

        filter_conditions = [FieldCondition(key="entity_id", match=MatchValue(value=entity_id))]

        if chunk_type:
            filter_conditions.append(FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type)))

        # Get all matching points
        results = self._client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(must=filter_conditions),
            limit=100,
            with_vectors=False,
        )

        point_ids = [point.id for point in results[0]]

        if point_ids:
            self._client.delete(collection_name=self.collection_name, points_selector=point_ids)

        return len(point_ids)

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection.

        Returns:
            Dict with collection stats
        """
        self._connect()

        info = self._client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
            "vector_size": self.VECTOR_SIZE,
            "model": self.model_name,
        }
