"""
Chunk Generator for Entity Embeddings

Generates chunks from entity documents for embedding:
1. Global chunk: entire entity summary
2. Attribute chunks: individual or grouped attributes

Each chunk includes metadata for tracking and retrieval.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class EmbeddingChunk:
    """Represents a chunk of content for embedding"""

    text: str
    chunk_type: str  # 'global' or 'attribute'
    entity_id: str
    doc_id: str
    attribute_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChunkGenerator:
    """Generates embedding chunks from entity documents"""

    # Attributes to group together for semantic coherence
    ATTRIBUTE_GROUPS = {
        "identity": ["name", "full_name", "first_name", "last_name", "title", "role"],
        "skills": ["skills", "expertise", "technologies", "tools", "languages"],
        "experience": ["experience", "years_experience", "positions", "roles"],
        "education": ["education", "degrees", "certifications", "qualifications"],
        "location": ["location", "city", "country", "region", "address"],
        "contact": ["email", "phone", "website", "linkedin", "github"],
        "organization": ["company", "organization", "employer", "team", "department"],
        "projects": ["projects", "portfolio", "achievements", "contributions"],
    }

    @staticmethod
    def create_global_chunk(
        entity_id: str, doc_id: str, document: Dict[str, Any], summary_text: Optional[str] = None
    ) -> EmbeddingChunk:
        """
        Create a global chunk representing the entire entity.

        Args:
            entity_id: Entity identifier
            doc_id: Document identifier
            document: Full document from MongoDB
            summary_text: Optional pre-generated summary text

        Returns:
            EmbeddingChunk for global entity representation
        """
        if summary_text:
            text = summary_text
        else:
            # Build comprehensive text from document
            parts = []

            # Entity name and type
            entity_name = document.get("entity_name", "Unknown")
            entity_type = document.get("entity_type", "Entity")
            parts.append(f"{entity_name} ({entity_type})")

            # Text content if available
            if "text" in document and document["text"]:
                parts.append(document["text"])

            # Structured content
            structured = document.get("structured", {})
            if structured:
                parts.append(ChunkGenerator._format_structured_data(structured))

            # Content field
            content = document.get("content", {})
            if content:
                for key, value in content.items():
                    if isinstance(value, str) and len(value) > 10:
                        parts.append(f"{key.title()}: {value}")

            text = "\n".join(parts)

        return EmbeddingChunk(
            text=text,
            chunk_type="global",
            entity_id=entity_id,
            doc_id=doc_id,
            attribute_name=None,
            metadata={
                "entity_name": document.get("entity_name"),
                "entity_type": document.get("entity_type"),
                "source": "global_summary",
            },
        )

    @staticmethod
    def create_attribute_chunks(
        entity_id: str,
        doc_id: str,
        structured_data: Dict[str, Any],
        entity_name: str = "Unknown",
        group_attributes: bool = True,
    ) -> List[EmbeddingChunk]:
        """
        Create attribute-specific chunks from structured data.

        Args:
            entity_id: Entity identifier
            doc_id: Document identifier
            structured_data: Dictionary of structured attributes
            entity_name: Name of entity for context
            group_attributes: If True, group related attributes together

        Returns:
            List of EmbeddingChunks, one per attribute or attribute group
        """
        chunks = []
        processed_attrs = set()

        if group_attributes:
            # Process attribute groups
            for group_name, group_attrs in ChunkGenerator.ATTRIBUTE_GROUPS.items():
                group_data = {}
                for attr in group_attrs:
                    if attr in structured_data:
                        group_data[attr] = structured_data[attr]
                        processed_attrs.add(attr)

                if group_data:
                    text = ChunkGenerator._format_attribute_group(group_name, group_data, entity_name)
                    chunks.append(
                        EmbeddingChunk(
                            text=text,
                            chunk_type="attribute",
                            entity_id=entity_id,
                            doc_id=doc_id,
                            attribute_name=group_name,
                            metadata={
                                "entity_name": entity_name,
                                "attribute_group": group_name,
                                "attributes": list(group_data.keys()),
                                "source": "structured_data",
                            },
                        )
                    )

        # Process remaining individual attributes
        for attr, value in structured_data.items():
            if attr not in processed_attrs and value:
                text = ChunkGenerator._format_single_attribute(attr, value, entity_name)
                chunks.append(
                    EmbeddingChunk(
                        text=text,
                        chunk_type="attribute",
                        entity_id=entity_id,
                        doc_id=doc_id,
                        attribute_name=attr,
                        metadata={"entity_name": entity_name, "attribute_name": attr, "source": "structured_data"},
                    )
                )

        return chunks

    @staticmethod
    def generate_all_chunks(
        entity_id: str,
        doc_id: str,
        document: Dict[str, Any],
        include_global: bool = True,
        include_attributes: bool = True,
        group_attributes: bool = True,
        global_summary: Optional[str] = None,
    ) -> List[EmbeddingChunk]:
        """
        Generate all chunks (global + attributes) for an entity.

        Args:
            entity_id: Entity identifier
            doc_id: Document identifier
            document: Full document from MongoDB
            include_global: Whether to generate global chunk
            include_attributes: Whether to generate attribute chunks
            group_attributes: Whether to group related attributes
            global_summary: Optional pre-generated summary for global chunk

        Returns:
            List of all generated chunks
        """
        chunks = []

        # Global chunk
        if include_global:
            global_chunk = ChunkGenerator.create_global_chunk(entity_id, doc_id, document, global_summary)
            chunks.append(global_chunk)

        # Attribute chunks
        if include_attributes:
            structured = document.get("structured", {})
            if structured:
                attr_chunks = ChunkGenerator.create_attribute_chunks(
                    entity_id=entity_id,
                    doc_id=doc_id,
                    structured_data=structured,
                    entity_name=document.get("entity_name", "Unknown"),
                    group_attributes=group_attributes,
                )
                chunks.extend(attr_chunks)

        return chunks

    @staticmethod
    def _format_structured_data(structured: Dict[str, Any]) -> str:
        """Format structured data as readable text"""
        parts = []
        for key, value in structured.items():
            if isinstance(value, list):
                if value:  # Only if list is not empty
                    parts.append(f"{key.replace('_', ' ').title()}: {', '.join(map(str, value))}")
            elif isinstance(value, dict):
                # Flatten nested dict
                for sub_key, sub_value in value.items():
                    parts.append(f"{key.replace('_', ' ').title()} - {sub_key}: {sub_value}")
            elif value is not None and str(value).strip():
                parts.append(f"{key.replace('_', ' ').title()}: {value}")
        return "\n".join(parts)

    @staticmethod
    def _format_attribute_group(group_name: str, group_data: Dict[str, Any], entity_name: str) -> str:
        """Format a group of related attributes"""
        parts = [f"{entity_name} - {group_name.title()}:"]

        for attr, value in group_data.items():
            if isinstance(value, list):
                parts.append(f"{attr.replace('_', ' ').title()}: {', '.join(map(str, value))}")
            elif isinstance(value, dict):
                parts.append(f"{attr.replace('_', ' ').title()}: {', '.join(f'{k}: {v}' for k, v in value.items())}")
            else:
                parts.append(f"{attr.replace('_', ' ').title()}: {value}")

        return "\n".join(parts)

    @staticmethod
    def _format_single_attribute(attr_name: str, attr_value: Any, entity_name: str) -> str:
        """Format a single attribute"""
        formatted_name = attr_name.replace("_", " ").title()

        if isinstance(attr_value, list):
            value_str = ", ".join(map(str, attr_value))
            return f"{entity_name} - {formatted_name}: {value_str}"
        elif isinstance(attr_value, dict):
            value_str = ", ".join(f"{k}: {v}" for k, v in attr_value.items())
            return f"{entity_name} - {formatted_name}: {value_str}"
        else:
            return f"{entity_name} - {formatted_name}: {attr_value}"

    @staticmethod
    def estimate_chunk_size(chunk: EmbeddingChunk) -> Dict[str, int]:
        """Estimate size of chunk for embedding"""
        return {
            "characters": len(chunk.text),
            "words": len(chunk.text.split()),
            "estimated_tokens": len(chunk.text.split()) * 1.3,  # Rough estimate
        }
