# H-CDT Overview

Haben’s Career Digital Twin (H‑CDT) is a production‑ready profile agent that turns static résumé data and live signals (LinkedIn, GitHub, Portfolio) into credible, on‑demand answers. Phase 1 focuses on reliable data intake, evidence‑grounded retrieval, and concise responses suitable for stakeholder reviews and hiring workflows.

## Delivery Status (Phase 1)

- Implemented: live data connectors, data intake and curation, adaptive content preparation, vector index, retrieval, lightweight supervisor and intent routing, and a minimal web interface for evaluation.
- In progress: evaluator pass (tone/accuracy guardrail) and OpenAI Agents SDK integration for deeper agent state and tool orchestration.

## Interaction Model

User query → Supervisor (intent routing) → Targeted data access (live + curated) → Retrieval with source evidence → Clear, business‑ready response.

## Functional Components

- Live Sources: LinkedIn, GitHub, and Portfolio connectors with configurable limits and timeouts.
- Intake & Curation: Ingestion with SQLite caching and normalized metadata across sources.
- Preparation: Adaptive chunking that optimizes context windows based on content density and source type.
- Embedding & Index: Embeddings via OpenRouter; persistent vector index backed by ChromaDB.
- Retrieval & Response: Query‑time search with grounded citations; identity summaries prioritize résumé, then live sources.
- Supervisor & Routing: Intent detection for links, live GitHub, identity, and general retrieval.
- Evaluation UI: Minimal Gradio chat interface to test the end‑to‑end path quickly.

Reference implementation lives in:
- `src/tools.py` (live sources), `src/persistence.py` (cache)
- `src/pipeline/ingestion.py`, `src/pipeline/metadata.py`
- `src/pipeline/chunking.py`, `src/pipeline/dynamic_chunker.py`
- `src/pipeline/embedding.py`, `src/pipeline/vector_store.py`, `src/pipeline/run_pipeline.py`
- `src/router.py`, `src/supervisor.py`, `src/gradio_app.py`

## Data Footprint

- `data/processed/`: normalized résumé and curated artifacts
- `database/chroma_db/`: vector index (persistent)
- `database/cache.db`: ingestion cache (TTL‑controlled)

## Configuration (Env‑Driven)

Key parameters are fully configurable through environment variables to align with security, performance, and cost objectives:
- Connectivity and models: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_EMBEDDING_MODEL`, `EMBEDDING_BATCH_SIZE`
- Profiles and limits: `GITHUB_PROFILE`, `PORTIFOLIO_PROFILE`, `LINKEDIN_PROFILE`, `GITHUB_REPO_LIMIT`, `HTTP_TIMEOUT_SECONDS`
- Curation and safety rails: `MAX_LIVE_DOC_CHARS`, `MAX_DOC_CHARS`, `SHORT_DOC_NO_CHUNK_THRESHOLD`
- Adaptive preparation: `DYNAMIC_CHUNK_*` family (min/max size, overlap ratios, thresholds)
- Vector index: `CHROMA_DB_PATH`, `CHROMA_COLLECTION`, `VECTOR_UPSERT_BATCH_SIZE`, `VECTOR_QUERY_TOP_K`
- Runtime stability (low‑resource mode): `RAYON_NUM_THREADS`, `TOKIO_WORKER_THREADS`
- Observability: `SHOW_CITATIONS_IN_LOG`