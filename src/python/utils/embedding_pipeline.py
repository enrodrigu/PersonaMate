"""
Embedding Pipeline for PersonaMate Knowledge Graph

Orchestrates the generation of embeddings for entities:
1. Global embedding: represents the entire entity
2. Attribute embeddings: one per attribute or attribute group

Uses LangChain with GPT-3.5/4 for summary generation (optional, low cost).
Integrates with MongoDB (documents), Neo4j (graph), and Qdrant (vectors).
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4

try:
    from langchain.schema import HumanMessage
    from langchain_openai import ChatOpenAI

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain not installed. Summary generation will be basic.")

from utils.chunk_generator import ChunkGenerator
from utils.mongo_store import MongoStore
from utils.neo4j_graph import Neo4jGraph
from utils.vector_store import VectorStore


class EmbeddingPipeline:
    """Pipeline for generating and managing entity embeddings"""

    def __init__(
        self,
        mongo: Optional[MongoStore] = None,
        neo4j: Optional[Neo4jGraph] = None,
        vector: Optional[VectorStore] = None,
        use_llm_summaries: bool = True,
        llm_model: str = "gpt-3.5-turbo",
    ):
        """Initialize the embedding pipeline.

        Args:
            mongo: MongoDB store instance
            neo4j: Neo4j graph instance
            vector: Qdrant vector store instance
            use_llm_summaries: Use LLM for generating summaries
            llm_model: LLM model name for summaries
        """
        self.mongo = mongo or MongoStore.load()
        self.neo4j = neo4j or Neo4jGraph.load()
        self.vector = vector or VectorStore.load()

        self.use_llm_summaries = use_llm_summaries and LANGCHAIN_AVAILABLE
        self.llm = None

        if self.use_llm_summaries:
            try:
                self.llm = ChatOpenAI(
                    model=llm_model, temperature=0.3, max_tokens=150  # Keep summaries short and cost-effective
                )
            except Exception as e:
                print(f"Warning: Could not initialize LLM: {e}")
                self.use_llm_summaries = False

    @classmethod
    def load(cls, use_llm_summaries: bool = True) -> "EmbeddingPipeline":
        """Factory method to create pipeline with all stores"""
        return cls(use_llm_summaries=use_llm_summaries)

    def process_entity(
        self,
        entity_id: str,
        generate_global: bool = True,
        generate_attributes: bool = True,
        force_regenerate: bool = False,
    ) -> Dict[str, Any]:
        """Process an entity and generate all embeddings.

        Args:
            entity_id: Entity identifier
            generate_global: Generate global embedding
            generate_attributes: Generate attribute embeddings
            force_regenerate: Regenerate even if embeddings exist

        Returns:
            Dict with results: chunk_ids, statistics, etc.
        """
        # Get document from MongoDB
        document = self.mongo.get_document(entity_id)
        if not document:
            raise ValueError(f"Entity {entity_id} not found in MongoDB")

        doc_id = document.get("_id", entity_id)

        # Delete existing embeddings if regenerating
        if force_regenerate:
            self.vector.delete_entity_chunks(entity_id)

        # Generate global summary if using LLM
        global_summary = None
        if generate_global and self.use_llm_summaries:
            global_summary = self._generate_global_summary(document)

        # Generate chunks
        chunks = ChunkGenerator.generate_all_chunks(
            entity_id=entity_id,
            doc_id=str(doc_id),
            document=document,
            include_global=generate_global,
            include_attributes=generate_attributes,
            group_attributes=True,
            global_summary=global_summary,
        )

        # Prepare chunks for vector store
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                "chunk_id": str(uuid4()),
                "entity_id": chunk.entity_id,
                "doc_id": chunk.doc_id,
                "chunk_type": chunk.chunk_type,
                "text": chunk.text,
                "metadata": chunk.metadata or {},
            }

            if chunk.attribute_name:
                chunk_dict["attribute_name"] = chunk.attribute_name

            chunk_dicts.append(chunk_dict)

        # Batch insert to vector store
        chunk_ids = self.vector.add_chunks_batch(chunk_dicts)

        # Update Neo4j metadata (optional: track embedding status)
        self._update_neo4j_metadata(entity_id, embeddings_generated=True, chunk_count=len(chunk_ids))

        return {
            "entity_id": entity_id,
            "chunk_ids": chunk_ids,
            "chunk_count": len(chunk_ids),
            "global_chunks": sum(1 for c in chunks if c.chunk_type == "global"),
            "attribute_chunks": sum(1 for c in chunks if c.chunk_type == "attribute"),
            "used_llm": self.use_llm_summaries,
        }

    def process_batch(
        self, entity_ids: Optional[List[str]] = None, entity_type: Optional[str] = None, force_regenerate: bool = False
    ) -> List[Dict[str, Any]]:
        """Process multiple entities in batch.

        Args:
            entity_ids: Specific entity IDs to process
            entity_type: Process all entities of this type
            force_regenerate: Regenerate existing embeddings

        Returns:
            List of results for each entity
        """
        if entity_ids is None:
            # Get all entities of specified type
            entity_ids = self.mongo.list_entity_ids(entity_type)

        results = []
        for entity_id in entity_ids:
            try:
                result = self.process_entity(entity_id=entity_id, force_regenerate=force_regenerate)
                results.append(result)
                print(f"✓ Processed {entity_id}: {result['chunk_count']} chunks")
            except Exception as e:
                print(f"✗ Error processing {entity_id}: {e}")
                results.append({"entity_id": entity_id, "error": str(e)})

        return results

    def add_new_entity(
        self,
        entity_type: str,
        entity_name: str,
        structured_data: Dict[str, Any],
        content: Optional[Dict[str, Any]] = None,
        text: Optional[str] = None,
        relationships: Optional[List[tuple]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a new entity with full pipeline processing.

        Args:
            entity_type: Type of entity (Person, Company, etc.)
            entity_name: Name of the entity
            structured_data: Structured attributes for chunking
            content: Additional unstructured content
            text: Full text description
            relationships: List of (target_id, rel_type) tuples
            metadata: Additional metadata

        Returns:
            Entity ID of created entity
        """
        entity_id = f"{entity_type.lower()}:{uuid4()}"

        # 1. Create entity in Neo4j
        self.neo4j.add_entity(entity_id=entity_id, entity_type=entity_type, name=entity_name, **structured_data)

        # 2. Create document in MongoDB
        self.mongo.create_document(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            structured=structured_data,
            content=content or {},
            text=text,
            metadata=metadata,
        )

        # 3. Create relationships in Neo4j
        if relationships:
            for rel_tuple in relationships:
                if len(rel_tuple) >= 2:
                    target_id, rel_type = rel_tuple[0], rel_tuple[1]
                    rel_metadata = rel_tuple[2] if len(rel_tuple) > 2 else {}
                    self.neo4j.add_relationship(
                        source_id=entity_id, target_id=target_id, rel_type=rel_type, **rel_metadata
                    )

        # 4. Generate embeddings
        self.process_entity(entity_id)

        return entity_id

    def update_entity_embeddings(
        self, entity_id: str, updated_attributes: Optional[Dict[str, Any]] = None, regenerate_all: bool = True
    ) -> Dict[str, Any]:
        """Update entity and regenerate embeddings.

        Args:
            entity_id: Entity to update
            updated_attributes: New/updated attributes
            regenerate_all: Regenerate all chunks or only affected ones

        Returns:
            Update results
        """
        if updated_attributes:
            # Update MongoDB document
            self.mongo.update_document(entity_id=entity_id, structured=updated_attributes, merge=True)

            # Update Neo4j properties
            entity = self.neo4j.get_entity(entity_id)
            if entity:
                self.neo4j.add_entity(
                    entity_id=entity_id,
                    entity_type=entity.get("type", "Entity"),
                    name=entity.get("name", "Unknown"),
                    **updated_attributes,
                )

        # Regenerate embeddings
        return self.process_entity(entity_id=entity_id, force_regenerate=regenerate_all)

    def _generate_global_summary(self, document: Dict[str, Any]) -> str:
        """Generate a concise summary using LLM.

        Args:
            document: MongoDB document

        Returns:
            Generated summary text (max ~100-150 tokens)
        """
        if not self.llm:
            return None

        # Build context for LLM
        entity_name = document.get("entity_name", "Unknown")
        entity_type = document.get("entity_type", "Entity")

        structured = document.get("structured", {})
        content = document.get("content", {})
        text = document.get("text", "")

        # Prepare prompt
        context_parts = [f"Entity: {entity_name} ({entity_type})"]

        if text:
            context_parts.append(f"Description: {text[:500]}")

        if structured:
            context_parts.append("Attributes:")
            for key, value in list(structured.items())[:10]:  # Limit to avoid token overflow
                context_parts.append(f"- {key}: {value}")

        if content:
            for key, value in list(content.items())[:5]:
                if isinstance(value, str):
                    context_parts.append(f"{key}: {value[:200]}")

        context = "\n".join(context_parts)

        # Generate summary
        prompt = f"""Generate a concise summary (2-3 sentences, max 100 tokens) for this entity:

{context}

Summary:"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            summary = response.content.strip()
            return summary
        except Exception as e:
            print(f"Warning: LLM summary generation failed: {e}")
            return None

    def _update_neo4j_metadata(self, entity_id: str, embeddings_generated: bool, chunk_count: int):
        """Update Neo4j entity with embedding metadata"""
        try:
            entity = self.neo4j.get_entity(entity_id)
            if entity:
                self.neo4j.add_entity(
                    entity_id=entity_id,
                    entity_type=entity.get("type", "Entity"),
                    name=entity.get("name", "Unknown"),
                    embeddings_generated=embeddings_generated,
                    embedding_chunk_count=chunk_count,
                )
        except Exception as e:
            print(f"Warning: Could not update Neo4j metadata: {e}")

    def get_entity_embeddings_info(self, entity_id: str) -> Dict[str, Any]:
        """Get information about entity's embeddings.

        Args:
            entity_id: Entity identifier

        Returns:
            Dict with embedding information
        """
        chunks = self.vector.get_entity_chunks(entity_id)

        return {
            "entity_id": entity_id,
            "total_chunks": len(chunks),
            "global_chunks": sum(1 for c in chunks if c.get("chunk_type") == "global"),
            "attribute_chunks": sum(1 for c in chunks if c.get("chunk_type") == "attribute"),
            "attributes": list(set(c.get("attribute_name") for c in chunks if c.get("attribute_name"))),
            "chunks": chunks,
        }

    def search_similar_entities(
        self, query: str, entity_type: Optional[str] = None, search_global_only: bool = False, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar entities using embeddings.

        Args:
            query: Search query
            entity_type: Filter by entity type
            search_global_only: Only search global chunks
            limit: Max results

        Returns:
            List of similar entities with scores
        """
        chunk_type = "global" if search_global_only else None

        results = self.vector.search_chunks(query=query, chunk_type=chunk_type, limit=limit)

        # Group by entity and get best score
        entity_results = {}
        for result in results:
            entity_id = result["entity_id"]
            if entity_id not in entity_results or result["score"] > entity_results[entity_id]["score"]:
                entity_results[entity_id] = result

        # Enrich with full entity data
        enriched_results = []
        for entity_id, result in entity_results.items():
            doc = self.mongo.get_document(entity_id)
            if doc:
                enriched_results.append(
                    {
                        "entity_id": entity_id,
                        "entity_name": doc.get("entity_name"),
                        "entity_type": doc.get("entity_type"),
                        "score": result["score"],
                        "matched_chunk": result["chunk_type"],
                        "matched_attribute": result.get("attribute_name"),
                        "matched_text": result["text"][:200] + "...",
                    }
                )

        return enriched_results

    def close(self):
        """Close all connections"""
        self.mongo.close()
        self.neo4j.close()
        self.vector.close()
