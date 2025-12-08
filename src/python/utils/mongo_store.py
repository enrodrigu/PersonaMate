"""
MongoDB Document Store for PersonaMate RAG Architecture

Stores detailed, unstructured information about entities as JSON documents.
Each document is linked to a Neo4j node via a shared entity_id.

Document Structure:
{
    "entity_id": "uuid",           # Shared with Neo4j node
    "entity_type": "Person",       # Type of entity
    "entity_name": "John Doe",     # Name for reference
    "structured": {                # Structured attributes for chunking
        "name": "John Doe",
        "title": "Backend Engineer",
        "skills": ["Python", "Docker"],
        "location": "Montreal",
        "experience": "8 years"
    },
    "text": "...",                 # Optional full text for global embedding
    "content": {                   # Flexible document content
        "biography": "...",
        "description": "...",
        "details": {...},
        "history": [...],
        "notes": "..."
    },
    "metadata": {                  # Document metadata
        "created_at": "ISO datetime",
        "updated_at": "ISO datetime",
        "source": "user_input",
        "tags": ["tag1", "tag2"]
    },
    "version": 1                   # Document version
}
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


class MongoStore:
    """Document store for entity details using MongoDB."""

    def __init__(self, uri: str = None, database: str = None, collection: str = "entity_documents"):
        """Initialize MongoDB connection.

        Args:
            uri: MongoDB connection URI (default from NEO4J_URI env)
            database: Database name (default from MONGODB_DB env)
            collection: Collection name for entity documents
        """
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database or os.getenv("MONGODB_DB", "personamate")
        self.collection_name = collection

        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None
        self._collection: Optional[Collection] = None

    def _connect(self):
        """Lazy connection to MongoDB."""
        if self._client is None:
            self._client = MongoClient(self.uri)
            self._database = self._client[self.database_name]
            self._collection = self._database[self.collection_name]

            # Create indexes for efficient queries
            self._collection.create_index("entity_id", unique=True)
            self._collection.create_index([("entity_type", 1), ("entity_name", 1)])
            self._collection.create_index("metadata.tags")

    def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            self._collection = None

    @classmethod
    def load(cls) -> "MongoStore":
        """Factory method to create and connect store."""
        store = cls()
        store._connect()
        return store

    def create_document(
        self,
        entity_id: str,
        entity_type: str,
        entity_name: str,
        content: Dict[str, Any],
        structured: Optional[Dict[str, Any]] = None,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "user_input",
    ) -> str:
        """Create a new entity document.

        Args:
            entity_id: Unique ID shared with Neo4j node
            entity_type: Type of entity (Person, Organization, etc.)
            entity_name: Name of the entity
            content: Flexible document content
            structured: Structured attributes for attribute-based embedding
            text: Optional full text for global embedding
            metadata: Optional metadata dict
            source: Source of the information

        Returns:
            The entity_id of the created document
        """
        self._connect()

        now = datetime.utcnow().isoformat()
        doc = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "entity_name": entity_name,
            "content": content,
            "metadata": {
                "created_at": now,
                "updated_at": now,
                "source": source,
                "tags": metadata.get("tags", []) if metadata else [],
                **(metadata or {}),
            },
            "version": 1,
        }

        # Add structured data if provided
        if structured:
            doc["structured"] = structured

        # Add text if provided
        if text:
            doc["text"] = text

        self._collection.insert_one(doc)
        return entity_id

    def get_document(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by entity_id.

        Args:
            entity_id: The unique entity identifier

        Returns:
            Document dict or None if not found
        """
        self._connect()
        doc = self._collection.find_one({"entity_id": entity_id})
        if doc:
            # Remove MongoDB's _id from the result
            doc.pop("_id", None)
        return doc

    def update_document(
        self,
        entity_id: str,
        content: Optional[Dict[str, Any]] = None,
        structured: Optional[Dict[str, Any]] = None,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        merge: bool = True,
    ) -> bool:
        """Update an existing document.

        Args:
            entity_id: The unique entity identifier
            content: New content (merged or replaced based on merge flag)
            structured: New structured data (merged or replaced)
            text: New text field
            metadata: New metadata (merged with existing)
            merge: If True, merge with existing; if False, replace

        Returns:
            True if document was updated, False if not found
        """
        self._connect()

        existing = self.get_document(entity_id)
        if not existing:
            return False

        update_data = {"metadata.updated_at": datetime.utcnow().isoformat()}

        if content is not None:
            if merge:
                # Merge content with existing
                merged_content = {**existing.get("content", {}), **content}
                update_data["content"] = merged_content
            else:
                update_data["content"] = content

        if structured is not None:
            if merge:
                # Merge structured with existing
                merged_structured = {**existing.get("structured", {}), **structured}
                update_data["structured"] = merged_structured
            else:
                update_data["structured"] = structured

        if text is not None:
            update_data["text"] = text

        if metadata is not None:
            # Always merge metadata
            merged_metadata = {**existing.get("metadata", {}), **metadata}
            merged_metadata["updated_at"] = update_data["metadata.updated_at"]
            update_data["metadata"] = merged_metadata

        # Increment version
        update_data["version"] = existing.get("version", 1) + 1

        result = self._collection.update_one({"entity_id": entity_id}, {"$set": update_data})

        return result.modified_count > 0

    def delete_document(self, entity_id: str) -> bool:
        """Delete a document by entity_id.

        Args:
            entity_id: The unique entity identifier

        Returns:
            True if document was deleted, False if not found
        """
        self._connect()
        result = self._collection.delete_one({"entity_id": entity_id})
        return result.deleted_count > 0

    def search_documents(
        self,
        entity_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        text_search: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search documents with filters.

        Args:
            entity_type: Filter by entity type
            tags: Filter by tags (any match)
            text_search: Text search in entity_name (case-insensitive)
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        self._connect()

        query = {}
        if entity_type:
            query["entity_type"] = entity_type
        if tags:
            query["metadata.tags"] = {"$in": tags}
        if text_search:
            query["entity_name"] = {"$regex": text_search, "$options": "i"}

        docs = self._collection.find(query).limit(limit)
        results = []
        for doc in docs:
            doc.pop("_id", None)
            results.append(doc)

        return results

    def get_document_summary(self, entity_id: str, max_length: int = 150) -> Optional[str]:
        """Get a compact summary of document content for embedding.

        Optimized for the 3-part embedding approach:
        - Extracts 1-2 key paragraphs (biography, description, summary)
        - Truncates to max_length for compact representation
        - Focuses on descriptive content, not metadata

        Args:
            entity_id: The unique entity identifier
            max_length: Maximum length of summary in characters

        Returns:
            Compact text summary or None if not found
        """
        doc = self.get_document(entity_id)
        if not doc:
            return None

        content = doc.get("content", {})

        # Priority fields for summary
        summary_text = None
        for field in ["summary", "biography", "description", "about", "bio", "overview"]:
            if field in content and content[field]:
                text = str(content[field]).strip()
                if text:
                    summary_text = text
                    break

        if not summary_text:
            # Fallback: concatenate available text fields
            text_parts = []
            for key, value in content.items():
                if isinstance(value, str) and len(value) > 20:
                    text_parts.append(value)
                    if len(" ".join(text_parts)) > max_length:
                        break
            summary_text = " ".join(text_parts)

        # Truncate to max_length if needed
        if summary_text and len(summary_text) > max_length:
            summary_text = summary_text[:max_length].rsplit(" ", 1)[0] + "..."

        return summary_text or "No description available."

    def list_entity_ids(self, entity_type: Optional[str] = None) -> List[str]:
        """List all entity_ids, optionally filtered by type.

        Args:
            entity_type: Optional entity type filter

        Returns:
            List of entity_id strings
        """
        self._connect()

        query = {"entity_type": entity_type} if entity_type else {}
        docs = self._collection.find(query, {"entity_id": 1})

        return [doc["entity_id"] for doc in docs]
