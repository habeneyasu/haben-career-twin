# Haben's Career Digital Twin (H-CDT) - Project Architecture

## Architecture Goal

H-CDT is structured as a modular digital twin for career representation, with clear boundaries between orchestration, live data tools, evaluator, and data pipeline stages.

## High-Level Architecture

```text
User
  -> Supervisor (routing/orchestration)
      -> Router (intent direction)
          -> Tools (live profile data access)
          -> Pipeline (knowledge-base preparation)
          -> Evaluator (secondary quality check)
```

## Core Modules

### `src/supervisor.py`
- Architecture entry point for orchestration flow
- Coordinates interaction between routing, tools, and evaluation layers

### `src/router.py`
- Intent routing boundary
- Decides which internal component should handle a given query

### `src/tools.py`
- Live-source integration layer
- Contains:
  - `get_github_live()`
  - `get_portfolio_live()`
  - `get_linkedin_meta()`

### `src/pipeline/`
- Pipeline stages are separated by responsibility:
  - `ingestion.py` - document ingestion
  - `metadata.py` - metadata shaping
  - `chunking.py` - text chunk strategy
  - `embedding.py` - embedding generation
  - `vector_store.py` - vector database write/read boundary

### `src/evaluator/evaluator.py`
- Secondary LLM evaluation boundary (tone/accuracy review layer)

## Data Architecture

```text
data/raw/        -> source assets
data/processed/  -> processed artifacts
database/chroma_db/ -> vector storage
```

## Current Repository Structure

```text
src/
├── supervisor.py
├── router.py
├── tools.py
├── evaluator/
│   └── evaluator.py
└── pipeline/
    ├── ingestion.py
    ├── metadata.py
    ├── chunking.py
    ├── embedding.py
    └── vector_store.py
```
