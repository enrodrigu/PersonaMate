# Embedding Pipeline Documentation

## Overview

Le pipeline d'embedding de PersonaMate génère deux types d'embeddings pour chaque entité:

1. **Global Embedding**: Représente l'entité entière (résumé complet)
2. **Attribute Embeddings**: Un embedding par attribut ou groupe d'attributs

Cette approche permet:
- ✅ Recherche sémantique globale (trouver des entités similaires)
- ✅ Recherche fine-grained (trouver des compétences, localisations spécifiques)
- ✅ Meilleure précision que les embeddings uniques
- ✅ Flexibilité dans les requêtes

## Architecture

```mermaid
graph TD
    A[EMBEDDING PIPELINE WORKFLOW] --> B[MongoDB Documents]
    A --> C[Neo4j Graph]
    A --> D[Qdrant Vectors]

    B --> E[Chunk Generator]
    C --> E
    E --> F[LLM Summary<br/>GPT-3.5: ~$0.00001/entity<br/>optional]
    F --> G[Sentence Transformer<br/>all-MiniLM-L6-v2<br/>384 dimensions]
    G --> D

    style A fill:#e1f5ff
    style E fill:#fff4e1
    style F fill:#ffe1e1
    style G fill:#e1ffe1
```

## Components

### 1. ChunkGenerator (`utils/chunk_generator.py`)

Génère les chunks de texte à partir des documents:

```python
from utils.chunk_generator import ChunkGenerator

# Générer tous les chunks pour une entité
chunks = ChunkGenerator.generate_all_chunks(
    entity_id="person:alice",
    doc_id="doc_123",
    document=mongo_document,
    include_global=True,
    include_attributes=True,
    group_attributes=True  # Grouper les attributs liés
)
```

**Groupes d'attributs par défaut:**
- `identity`: name, title, role
- `skills`: skills, expertise, technologies
- `experience`: experience, positions, years_experience
- `education`: education, degrees, certifications
- `location`: location, city, country
- `contact`: email, phone, website
- `organization`: company, employer, team
- `projects`: projects, achievements

### 2. VectorStore (`utils/vector_store.py`)

Gère les embeddings dans Qdrant avec support des chunks:

```python
from utils.vector_store import VectorStore

vector = VectorStore.load()

# Ajouter un chunk
vector.add_chunk_vector(
    chunk_id="chunk_uuid",
    entity_id="person:alice",
    doc_id="doc_123",
    chunk_type="attribute",  # or "global"
    text="Alice - Skills: Python, ML, TensorFlow",
    attribute_name="skills",
    metadata={"source": "structured_data"}
)

# Recherche par type de chunk
results = vector.search_chunks(
    query="machine learning expert",
    chunk_type="attribute",  # Chercher uniquement dans les attributs
    attribute_name="skills",  # Chercher uniquement dans les skills
    limit=5
)
```

### 3. MongoStore (`utils/mongo_store.py`)

Structure de document étendue avec support `structured`:

```python
from utils.mongo_store import MongoStore

mongo = MongoStore.load()

# Créer un document avec données structurées
mongo.create_document(
    entity_id="person:alice",
    entity_type="Person",
    entity_name="Alice Johnson",
    structured={  # NOUVEAU: Attributs structurés pour chunking
        "name": "Alice Johnson",
        "title": "Data Scientist",
        "skills": ["Python", "ML", "TensorFlow"],
        "location": "San Francisco",
        "experience": "10 years"
    },
    text="Full text description...",  # NOUVEAU: Texte global optionnel
    content={  # Contenu non structuré (legacy)
        "biography": "...",
        "notes": "..."
    }
)
```

### 4. EmbeddingPipeline (`utils/embedding_pipeline.py`)

Orchestrateur principal:

```python
from utils.embedding_pipeline import EmbeddingPipeline

pipeline = EmbeddingPipeline.load(use_llm_summaries=True)

# Ajouter une nouvelle entité avec embeddings automatiques
entity_id = pipeline.add_new_entity(
    entity_type="Person",
    entity_name="Alice Johnson",
    structured_data={
        "title": "Data Scientist",
        "skills": ["Python", "ML"],
        "location": "SF"
    },
    text="Alice is a data scientist...",
    relationships=[("company:acme", "WORKS_AT")]
)

# Recherche sémantique
results = pipeline.search_similar_entities(
    query="machine learning expert in San Francisco",
    limit=5
)
```

## Usage

### Installation

```bash
# Installer les dépendances
pip install langchain langchain-openai openai sentence-transformers

# Variables d'environnement pour LLM
export OPENAI_API_KEY="your-api-key"

# Démarrer les services
docker compose up -d mongodb neo4j qdrant
```

### Exemple 1: Ajouter une entité

```python
from utils.embedding_pipeline import EmbeddingPipeline

pipeline = EmbeddingPipeline.load(use_llm_summaries=True)

entity_id = pipeline.add_new_entity(
    entity_type="Person",
    entity_name="Bob Smith",
    structured_data={
        "name": "Bob Smith",
        "title": "Backend Engineer",
        "skills": ["Python", "Go", "Kubernetes"],
        "experience": "5 years",
        "location": "New York",
        "company": "Tech Corp"
    },
    content={
        "biography": "Backend engineer specializing in distributed systems..."
    },
    text="Bob is an experienced backend engineer..."
)

print(f"Created entity: {entity_id}")
```

### Exemple 2: Recherche sémantique

```python
# Recherche globale
results = pipeline.search_similar_entities(
    query="kubernetes expert",
    limit=5
)

for result in results:
    print(f"{result['entity_name']}: {result['score']:.3f}")
    print(f"  Matched: {result['matched_attribute']}")
```

### Exemple 3: Recherche par attribut

```python
# Recherche uniquement dans les compétences
from utils.vector_store import VectorStore

vector = VectorStore.load()

results = vector.search_chunks(
    query="machine learning deep learning",
    attribute_name="skills",  # Seulement dans skills
    limit=5
)

for result in results:
    print(f"Entity: {result['entity_id']}")
    print(f"Skills: {result['text']}")
    print(f"Score: {result['score']:.3f}")
```

### Exemple 4: Mettre à jour et régénérer

```python
# Mettre à jour une entité
result = pipeline.update_entity_embeddings(
    entity_id="person:bob",
    updated_attributes={
        "skills": ["Python", "Go", "Kubernetes", "Rust"],  # Ajout de Rust
        "certifications": ["AWS Certified"]
    },
    regenerate_all=True
)

print(f"Regenerated {result['chunk_count']} chunks")
```

### Exemple 5: Traitement batch

```python
# Régénérer tous les embeddings pour un type d'entité
results = pipeline.process_batch(
    entity_type="Person",
    force_regenerate=True
)

print(f"Processed {len(results)} entities")
```

## Résumés LLM (Optionnel)

Le pipeline peut utiliser LangChain + GPT-3.5/4 pour générer des résumés concis:

```python
pipeline = EmbeddingPipeline.load(use_llm_summaries=True)
```

**Prompt utilisé:**
```
Generate a concise summary (2-3 sentences, max 100 tokens) for this entity:

Entity: Alice Johnson (Person)
Attributes:
- title: Data Scientist
- skills: Python, ML, TensorFlow
- experience: 10 years
...

Summary:
```

**Coût estimé:**
- Input: ~100 tokens
- Output: ~50 tokens
- Total: ~150 tokens/entity
- GPT-3.5: ~$0.00001 par entité
- GPT-4: ~$0.0001 par entité

**Sans LLM:**
Le pipeline utilise un résumé basique concaténant les attributs structurés.

## Structure des Chunks

### Global Chunk

```json
{
  "chunk_id": "uuid",
  "entity_id": "person:alice",
  "doc_id": "doc_123",
  "chunk_type": "global",
  "text": "Alice Johnson (Person)\n\nAlice is a senior data scientist...",
  "metadata": {
    "entity_name": "Alice Johnson",
    "entity_type": "Person",
    "source": "global_summary"
  }
}
```

### Attribute Chunk

```json
{
  "chunk_id": "uuid",
  "entity_id": "person:alice",
  "doc_id": "doc_123",
  "chunk_type": "attribute",
  "attribute_name": "skills",
  "text": "Alice Johnson - Skills:\nSkills: Python, Machine Learning, TensorFlow\nExpertise: NLP, Deep Learning",
  "metadata": {
    "entity_name": "Alice Johnson",
    "attribute_group": "skills",
    "attributes": ["skills", "expertise"],
    "source": "structured_data"
  }
}
```

## Métadonnées Qdrant

Chaque point dans Qdrant inclut:

```python
{
    "chunk_id": "uuid",
    "entity_id": "person:alice",
    "doc_id": "doc_123",
    "chunk_type": "global" | "attribute",
    "attribute_name": "skills",  # Si attribute chunk
    "text": "Texte original",
    "created_at": "2025-12-08T...",
    # + metadata custom
}
```

## Filtres de Recherche

```python
# Chercher seulement les chunks globaux
results = vector.search_chunks(
    query="data scientist",
    chunk_type="global"
)

# Chercher dans une entité spécifique
results = vector.search_chunks(
    query="python",
    entity_id="person:alice"
)

# Chercher un attribut spécifique
results = vector.search_chunks(
    query="machine learning",
    attribute_name="skills"
)

# Combiner les filtres
results = vector.search_chunks(
    query="kubernetes",
    entity_id="person:bob",
    chunk_type="attribute",
    attribute_name="skills"
)
```

## Performance

### Taille des Embeddings

| Type | Texte moyen | Tokens | Embedding |
|------|-------------|--------|-----------|
| Global | 300-500 chars | 75-125 | 384-dim |
| Attribute group | 50-150 chars | 15-40 | 384-dim |
| Single attribute | 20-80 chars | 5-20 | 384-dim |

### Temps de Traitement

- **Génération chunk**: ~5ms
- **LLM summary**: ~500ms (si activé)
- **Embedding generation**: ~50ms par chunk
- **Batch insert Qdrant**: ~100ms pour 10 chunks
- **Total par entité**: ~1-2s avec LLM, ~0.5s sans

### Recommandations

1. **Batch processing**: Traiter les entités par lots de 50-100
2. **LLM summaries**: Activer uniquement pour entités complexes
3. **Attribute grouping**: Garder activé pour réduire le nombre de chunks
4. **Index Qdrant**: Utiliser HNSW avec m=16, ef_construct=100

## Scripts Utiles

### Régénérer tous les embeddings

```bash
python -c "
from utils.embedding_pipeline import EmbeddingPipeline
pipeline = EmbeddingPipeline.load(use_llm_summaries=True)
results = pipeline.process_batch(force_regenerate=True)
print(f'Processed {len(results)} entities')
pipeline.close()
"
```

### Vérifier les chunks d'une entité

```bash
python -c "
from utils.embedding_pipeline import EmbeddingPipeline
pipeline = EmbeddingPipeline.load()
info = pipeline.get_entity_embeddings_info('person:alice')
print(f'Total chunks: {info[\"total_chunks\"]}')
print(f'Global: {info[\"global_chunks\"]}')
print(f'Attributes: {info[\"attribute_chunks\"]}')
pipeline.close()
"
```

### Lancer la démo complète

```bash
# Tous les exemples interactifs
python examples/embedding_pipeline_demo.py

# Un exemple spécifique
python examples/embedding_pipeline_demo.py 1  # Example 1
python examples/embedding_pipeline_demo.py 3  # Example 3
```

## Troubleshooting

### LangChain non disponible

```
Warning: LangChain not installed. Summary generation will be basic.
```

**Solution**: `pip install langchain langchain-openai`

### OpenAI API Key manquant

```
Warning: Could not initialize LLM: ...
```

**Solution**: `export OPENAI_API_KEY="your-key"`

### Qdrant connection refusée

```
ERROR: Connection refused to Qdrant
```

**Solution**: `docker compose up -d qdrant`

### Pas de chunks générés

Vérifier que le document a le champ `structured`:

```python
doc = mongo.get_document(entity_id)
print(doc.get('structured'))  # Doit contenir des attributs
```

## API Reference

Voir les docstrings dans:
- `utils/chunk_generator.py`
- `utils/embedding_pipeline.py`
- `utils/vector_store.py`
- `utils/mongo_store.py`

## Examples

Voir `examples/embedding_pipeline_demo.py` pour 7 exemples complets.
