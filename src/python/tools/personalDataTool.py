"""
PersonaMate MCP Tools - Embedding Pipeline Architecture

Three main tools for knowledge management:
1. rag_query: Retrieve information using semantic chunk-based search
2. ingest_document: Add new entities with multi-level embeddings
3. update_entity: Update existing entities and regenerate embeddings
"""

import json
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from utils.embedding_pipeline import EmbeddingPipeline


@tool
def rag_query(query: str, entity_type: Optional[str] = None, limit: int = 5) -> str:
    """Retrieve information from the RAG system using chunk-based semantic search.

    Searches across chunks (global + attributes) to find relevant entities with
    complete context from Neo4j graph and MongoDB documents.

    Args:
        query: Natural language query (e.g., "Python developers in Paris", "companies in AI")
        entity_type: Optional filter by type (Person, Organization, etc.)
        limit: Maximum number of results (default: 5)

    Returns:
        JSON string with search results including:
        - entity_id, doc_id, entity_type
        - content (full document from MongoDB with structured attributes)
        - matched_chunks (which chunks matched the query)
        - similarity scores

    Example:
        rag_query("software engineers with machine learning experience", entity_type="Person", limit=3)
    """
    if not query:
        return json.dumps({"error": "Query is required"})

    pipeline = EmbeddingPipeline.load()
    try:
        # Semantic search using chunks
        results = pipeline.search_similar_entities(query=query, limit=limit, score_threshold=0.3, deduplicate=True)

        # Format results with full entity data
        formatted_results = []
        for result in results:
            entity_data = pipeline.mongo.get_document(result["doc_id"])

            formatted_results.append(
                {
                    "entity_id": result["entity_id"],
                    "doc_id": result["doc_id"],
                    "score": result["score"],
                    "matched_chunk": result.get("chunk_type"),
                    "matched_attribute": result.get("attribute_name"),
                    "text_preview": result.get("text", "")[:200],
                    "content": entity_data,
                }
            )

        return json.dumps(
            {"query": query, "results_count": len(formatted_results), "results": formatted_results},
            indent=2,
            default=str,
        )

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def ingest_document(
    text: str,
    entity_type: str,
    entity_id: str,
    structured_data: Optional[str] = None,
    metadata: Optional[str] = None,
    generate_summary: bool = False,
) -> str:
    """Ingest a document with multi-level embeddings (global + attribute chunks).

    Creates entity across all three stores:
    - Neo4j: Entity node with type and ID
    - MongoDB: Document with structured attributes
    - Qdrant: Multiple embedding chunks (1 global + N attributes)

    Args:
        text: Global summary text for the entity
        entity_type: Type of entity (Person, Organization, Project, etc.)
        entity_id: Unique identifier for the entity
        structured_data: Optional JSON with attribute groups (skills, experience, etc.)
        metadata: Optional JSON string with additional metadata (tags, source, date)
        generate_summary: Whether to use LLM to generate summaries (costs ~$0.00001)

    Returns:
        JSON string with created entity_id, doc_id, and chunk count

    Example:
        ingest_document(
            text="John Doe is a senior AI researcher",
            entity_type="Person",
            entity_id="person:john_doe",
            structured_data='{"skills": ["Python", "NLP"], "experience": ["Google", "OpenAI"]}',
            generate_summary=True
        )
    """
    if not text or not entity_type or not entity_id:
        return json.dumps({"error": "text, entity_type, and entity_id are required"})

    pipeline = EmbeddingPipeline.load(use_langchain=generate_summary)
    try:
        # Parse structured data
        structured_dict = {}
        if structured_data:
            try:
                structured_dict = json.loads(structured_data)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON in structured_data parameter"})

        # Parse metadata
        meta_dict = {}
        if metadata:
            try:
                meta_dict = json.loads(metadata)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON in metadata parameter"})

        meta_dict["ingested_at"] = datetime.utcnow().isoformat()

        # Create entity with multi-level embeddings
        doc_id = pipeline.add_new_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            text_content=text,
            structured_data=structured_dict,
            metadata=meta_dict,
        )

        # Get chunk count
        chunks = pipeline.vector_store.get_entity_chunks(entity_id)

        return json.dumps(
            {
                "success": True,
                "entity_id": entity_id,
                "doc_id": doc_id,
                "entity_type": entity_type,
                "chunks_created": len(chunks),
                "chunk_breakdown": {"global": 1, "attributes": len(chunks) - 1},
                "ingested_at": meta_dict["ingested_at"],
                "message": f"Successfully ingested {entity_type} with {len(chunks)} embedding chunks",
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps({"error": f"Ingestion failed: {str(e)}"})


@tool
def update_entity(
    entity_id: str,
    doc_id: str,
    text: Optional[str] = None,
    structured_data: Optional[str] = None,
    metadata: Optional[str] = None,
    force_regenerate: bool = False,
) -> str:
    """Update an existing entity and regenerate its embeddings.

    Updates entity information across all three stores:
    - Neo4j: Entity properties
    - MongoDB: Document content and structured data
    - Qdrant: Regenerates all embedding chunks

    Args:
        entity_id: Unique entity identifier (e.g., "person:alice")
        doc_id: MongoDB document ID
        text: Optional new global summary text
        structured_data: Optional JSON with updated attribute groups
        metadata: Optional JSON string with metadata updates
        force_regenerate: Force regeneration even if content unchanged

    Returns:
        JSON string with updated entity data and chunk count

    Example:
        update_entity(
            entity_id="person:alice",
            doc_id="507f1f77bcf86cd799439011",
            structured_data='{"skills": ["Python", "Rust", "ML"]}',
            force_regenerate=True
        )
    """
    if not entity_id or not doc_id:
        return json.dumps({"error": "entity_id and doc_id are required"})

    pipeline = EmbeddingPipeline.load()
    try:
        # Parse structured data
        structured_dict = None
        if structured_data:
            try:
                structured_dict = json.loads(structured_data)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON in structured_data parameter"})

        # Parse metadata
        meta_dict = None
        if metadata:
            try:
                meta_dict = json.loads(metadata)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON in metadata parameter"})

        if meta_dict:
            meta_dict["last_updated"] = datetime.utcnow().isoformat()

        # Update MongoDB document
        if text or structured_dict or meta_dict:
            update_fields = {}
            if text:
                update_fields["text"] = text
            if structured_dict:
                update_fields["structured"] = structured_dict
            if meta_dict:
                update_fields.update(meta_dict)

            pipeline.mongo.update_document(doc_id, update_fields)

        # Regenerate embeddings
        chunks_created = pipeline.update_entity_embeddings(
            entity_id=entity_id, doc_id=doc_id, force_regenerate=force_regenerate
        )

        # Get updated document
        updated_doc = pipeline.mongo.get_document(doc_id)

        return json.dumps(
            {
                "success": True,
                "entity_id": entity_id,
                "doc_id": doc_id,
                "chunks_regenerated": chunks_created,
                "updated_fields": {
                    "text": text is not None,
                    "structured_data": structured_dict is not None,
                    "metadata": meta_dict is not None,
                },
                "current_content": updated_doc,
                "message": f"Successfully updated entity {entity_id} with {chunks_created} chunks",
            },
            indent=2,
            default=str,
        )

    except Exception as e:
        return json.dumps({"error": f"Update failed: {str(e)}"})
