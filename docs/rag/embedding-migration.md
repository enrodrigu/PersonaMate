# Migration Guide: Old vs New Embedding System

## Overview

PersonaMate a migré d'un système d'embedding **simple** (1 embedding par entité) vers un système **multi-niveaux** (embeddings global + par attribut).

## Ancien Système (Simple Embedding)

### Architecture

```
Entity → MongoDB Document → Summary Text → 1 Embedding → Qdrant
```

### Code (Ancien)

```python
from utils.rag_manager import RAGManager

rag = RAGManager.load()

# Ajout d'une entité
entity_id = rag.add_entity(
    entity_type="Person",
    name="Alice Johnson",
    content={
        "biography": "Alice is a data scientist...",
        "skills": ["Python", "ML"]
    }
)
# Génère 1 seul embedding global
```

### Problèmes

❌ **Un seul embedding** par entité
❌ **Perte de granularité** : impossible de cibler des attributs spécifiques
❌ **Recherche imprécise** : mélange tous les attributs dans un texte
❌ **Dilution d'information** : attributs importants noyés dans le texte global
❌ **Pas de filtrage par attribut**

### Exemple de recherche (Ancien)

```python
# Recherche "kubernetes expert"
results = rag.search("kubernetes expert")

# Problème: retourne des personnes avec "kubernetes" mentionné
# n'importe où dans leur profil, même si c'est un projet passé
# et pas une compétence principale
```

## Nouveau Système (Multi-Level Embeddings)

### Architecture

```
Entity → MongoDB Document → Chunks:
                             ├─ Global Chunk → Embedding (global)
                             ├─ Skills Chunk → Embedding (skills)
                             ├─ Location Chunk → Embedding (location)
                             └─ Experience Chunk → Embedding (experience)
                                      ↓
                              All embeddings → Qdrant (with metadata)
```

### Code (Nouveau)

```python
from utils.embedding_pipeline import EmbeddingPipeline

pipeline = EmbeddingPipeline.load(use_llm_summaries=True)

# Ajout d'une entité
entity_id = pipeline.add_new_entity(
    entity_type="Person",
    entity_name="Alice Johnson",
    structured_data={  # NOUVEAU: Attributs structurés
        "name": "Alice Johnson",
        "title": "Data Scientist",
        "skills": ["Python", "ML", "TensorFlow"],
        "location": "San Francisco",
        "experience": "10 years"
    },
    text="Alice is a data scientist...",
    content={
        "biography": "...",
        "achievements": [...]
    }
)
# Génère N embeddings: 1 global + 1 par attribut/groupe
```

### Avantages

✅ **Embeddings multi-niveaux** : global + attributs
✅ **Granularité fine** : recherche ciblée par attribut
✅ **Meilleure précision** : moins de dilution
✅ **Filtrage avancé** : par type de chunk, attribut spécifique
✅ **Résumés LLM** : summaries optimisés (optionnel)

### Exemple de recherche (Nouveau)

```python
# Recherche globale (comme avant)
results = pipeline.search_similar_entities(
    query="kubernetes expert",
    limit=5
)

# NOUVEAU: Recherche ciblée sur les compétences uniquement
from utils.vector_store import VectorStore

vector = VectorStore.load()
results = vector.search_chunks(
    query="kubernetes docker",
    chunk_type="attribute",
    attribute_name="skills",  # Chercher UNIQUEMENT dans skills
    limit=5
)

# Résultat: Retourne uniquement les personnes ayant
# kubernetes/docker dans leurs compétences principales
```

## Comparison Table

| Feature | Ancien Système | Nouveau Système |
|---------|----------------|-----------------|
| **Embeddings par entité** | 1 (global) | N (global + attributs) |
| **Granularité** | Grossière | Fine |
| **Recherche ciblée** | ❌ Non | ✅ Oui |
| **Filtrage par attribut** | ❌ Non | ✅ Oui |
| **Résumés LLM** | ❌ Non | ✅ Optionnel |
| **Précision recherche** | Moyenne | Élevée |
| **Flexibilité** | Faible | Élevée |
| **Coût stockage** | 1× | N× |
| **Performance recherche** | ~50ms | ~50-100ms |

## Migration Path

### Option 1: Migration Complète (Recommandé)

Régénérer tous les embeddings avec le nouveau système:

```python
from utils.embedding_pipeline import EmbeddingPipeline

pipeline = EmbeddingPipeline.load(use_llm_summaries=True)

# Migrer toutes les entités existantes
results = pipeline.process_batch(
    force_regenerate=True  # Régénère tout
)

print(f"Migrated {len(results)} entities")
```

**Avantages:**
- ✅ Bénéficie immédiatement des nouveaux features
- ✅ Meilleure qualité de recherche
- ✅ Cohérence complète

**Inconvénients:**
- ⏱️ Temps de traitement pour migrer toutes les entités
- 💰 Coût LLM si activé (~$0.00001 par entité)

### Option 2: Migration Progressive

Migrer uniquement les nouvelles entités et laisser les anciennes:

```python
# Nouveau code utilise EmbeddingPipeline
from utils.embedding_pipeline import EmbeddingPipeline

pipeline = EmbeddingPipeline.load()

# Nouvelles entités
entity_id = pipeline.add_new_entity(...)

# Anciennes entités restent inchangées
# Elles fonctionnent toujours avec l'ancien système
```

**Avantages:**
- ✅ Pas de migration bulk nécessaire
- ✅ Coexistence des deux systèmes
- ✅ Progressif et sans interruption

**Inconvénients:**
- ❌ Incohérence entre anciennes et nouvelles entités
- ❌ Deux APIs à maintenir

### Option 3: Hybride (Recommandé pour production)

Migrer progressivement les entités les plus utilisées:

```python
from utils.embedding_pipeline import EmbeddingPipeline

pipeline = EmbeddingPipeline.load()

# Identifier les entités critiques
critical_entities = [...]  # Top 100 entités

# Migrer uniquement celles-ci
for entity_id in critical_entities:
    pipeline.process_entity(
        entity_id=entity_id,
        force_regenerate=True
    )

# Migrer le reste en batch async
pipeline.process_batch(
    entity_type="Person",
    force_regenerate=True
)
```

## Code Changes Required

### 1. Mise à jour MongoDB Documents

**Ancien format:**
```json
{
  "entity_id": "person:alice",
  "entity_type": "Person",
  "entity_name": "Alice",
  "content": {
    "biography": "...",
    "skills": ["Python", "ML"]
  }
}
```

**Nouveau format:**
```json
{
  "entity_id": "person:alice",
  "entity_type": "Person",
  "entity_name": "Alice",
  "structured": {
    "name": "Alice",
    "title": "Data Scientist",
    "skills": ["Python", "ML"],
    "location": "SF"
  },
  "text": "Global description...",
  "content": {
    "biography": "...",
    "notes": "..."
  }
}
```

**Migration script:**
```python
from utils.mongo_store import MongoStore

mongo = MongoStore.load()

# Pour chaque document existant
for doc in mongo._collection.find():
    # Extraire attributs structurés du content
    structured = {
        "name": doc.get("entity_name"),
        "skills": doc.get("content", {}).get("skills", []),
        # ... autres attributs
    }

    # Mettre à jour
    mongo.update_document(
        entity_id=doc["entity_id"],
        structured=structured,
        merge=True
    )
```

### 2. Mise à jour Code Application

**Ancien code:**
```python
from utils.rag_manager import RAGManager

rag = RAGManager.load()

# Recherche
results = rag.search("data scientist", limit=5)
```

**Nouveau code:**
```python
from utils.embedding_pipeline import EmbeddingPipeline

pipeline = EmbeddingPipeline.load()

# Recherche globale (compatible)
results = pipeline.search_similar_entities(
    query="data scientist",
    limit=5
)

# OU recherche ciblée (nouveau feature)
from utils.vector_store import VectorStore

vector = VectorStore.load()
results = vector.search_chunks(
    query="data scientist",
    attribute_name="title",
    limit=5
)
```

## Performance Impact

### Stockage

| Système | Embeddings/Entité | Espace/Entité | Total (1000 entités) |
|---------|-------------------|---------------|----------------------|
| Ancien | 1 | ~1.5 KB | 1.5 MB |
| Nouveau | ~5-10 | ~7.5-15 KB | 7.5-15 MB |

**Impact:** ~5-10× plus d'espace nécessaire

### Recherche

| Opération | Ancien | Nouveau |
|-----------|--------|---------|
| Recherche simple | 50ms | 50-100ms |
| Recherche filtrée | N/A | 60-120ms |
| Recherche attribut | N/A | 40-80ms |

**Impact:** Légèrement plus lent mais avec bien plus de précision

### Génération

| Opération | Ancien | Nouveau (sans LLM) | Nouveau (avec LLM) |
|-----------|--------|--------------------|--------------------|
| Temps/entité | 300ms | 500ms | 1-2s |
| Coût/entité | $0 | $0 | ~$0.00001 |

## Backwards Compatibility

Le nouveau système est **compatible** avec l'ancien:

```python
# Ancien code fonctionne toujours
from utils.rag_manager import RAGManager

rag = RAGManager.load()
results = rag.search("query")  # ✅ Fonctionne

# Nouveau code disponible en parallèle
from utils.embedding_pipeline import EmbeddingPipeline

pipeline = EmbeddingPipeline.load()
results = pipeline.search_similar_entities("query")  # ✅ Fonctionne
```

## Recommendations

### Pour Production

1. ✅ **Migrer progressivement** : Option 3 (Hybride)
2. ✅ **Activer LLM summaries** pour entités importantes
3. ✅ **Monitorer performance** et ajuster
4. ✅ **Tester en staging** avant production

### Pour Développement

1. ✅ **Utiliser nouveau système** immédiatement
2. ✅ **Régénérer tout** avec `process_batch(force_regenerate=True)`
3. ✅ **Expérimenter** avec recherches ciblées

### Pour Tests

1. ✅ **Comparer qualité** ancien vs nouveau
2. ✅ **Mesurer précision** avec métriques (Recall@k, MRR)
3. ✅ **Valider coûts** si LLM activé

## FAQ

### Q: Dois-je migrer immédiatement?

**R**: Non, les deux systèmes coexistent. Migrez progressivement.

### Q: Dois-je activer les résumés LLM?

**R**: Optionnel. Testez d'abord sans, puis activez pour voir la différence. Coût minimal (~$0.00001/entité).

### Q: Comment minimiser le coût?

**R**:
- Désactiver LLM: `use_llm_summaries=False`
- Ou utiliser GPT-3.5 au lieu de GPT-4
- Ou traiter uniquement les entités importantes

### Q: Puis-je revenir en arrière?

**R**: Oui, conservez les anciens embeddings et désactivez le nouveau système.

### Q: Comment tester la qualité?

**R**: Exécutez des recherches test et comparez les résultats:

```python
# Comparer
old_results = rag.search("kubernetes expert", limit=10)
new_results = pipeline.search_similar_entities("kubernetes expert", limit=10)

# Analyser différences
```

## Support

- **Documentation**: [docs/embedding-pipeline.md](embedding-pipeline.md)
- **Examples**: [examples/embedding_pipeline_demo.py](../examples/embedding_pipeline_demo.py)
- **Issues**: GitHub issues
