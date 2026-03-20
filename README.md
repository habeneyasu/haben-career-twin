# H-CDT Architecture

Minimal Phase-1 architecture for a career digital twin.

## Implementation Status

- Implemented: `tools`, `ingestion`, `metadata`, `chunking`, `dynamic_chunker`, `persistence/cache`
- Placeholder: `embedding`, `vector_store`, `supervisor`, `router`, `evaluator`

## Flow

`User -> supervisor -> router -> tools + pipeline -> evaluator`

## Modules

- `src/tools.py`: live sources (GitHub, Portfolio, LinkedIn)
- `src/pipeline/ingestion.py`: implemented live/local ingestion with SQLite cache (`src/persistence.py`)
- `src/pipeline/metadata.py`: implemented metadata enrichment (source, hash, timestamps)
- `src/pipeline/chunking.py`: chunk execution
- `src/pipeline/dynamic_chunker.py`: dynamic chunk-size/overlap strategy
- `src/pipeline/embedding.py`: embeddings layer
- `src/pipeline/vector_store.py`: ChromaDB boundary
- `src/supervisor.py`, `src/router.py`, `src/evaluator/evaluator.py`: orchestration placeholders

## Data

- `data/raw/`: source assets
- `data/processed/`: normalized artifacts
- `database/chroma_db/`: vector store
- `database/cache.db`: ingestion cache
