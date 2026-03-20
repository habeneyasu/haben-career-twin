# H‑CDT: Haben's Career Digital Twin

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Gradio](https://img.shields.io/badge/Gradio-5.9+-orange.svg)](https://gradio.app/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Latest-green.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An executive‑ready, production‑grade AI agent that turns static résumé data and live professional signals (LinkedIn, GitHub, Portfolio) into credible, on‑demand answers.

## Problem

Profiles and portfolios get outdated fast. Recruiters and clients want instant, accurate answers about recent work, skills, and impact—without scheduling a call or hunting across links.

## Approach

Treat the professional profile like a product. Build a resilient Retrieval‑Augmented Generation (RAG) system that fuses the résumé with live GitHub, LinkedIn, and portfolio signals; add a supervisor that routes intent and synthesizes grounded answers.

## Solution

H‑CDT unifies multi‑source data into a vector index and serves business‑ready responses with citations. It’s memory‑efficient, cloud‑deployable, and avoids hallucinations via validation and fallbacks.

## Outcomes

- 24/7 professional presence with consistent, high‑quality answers
- Faster stakeholder decisions from credible, source‑cited responses
- Freshness from live GitHub/LinkedIn/portfolio integration
- Lead capture with push/email alerts for instant follow‑ups

## What It Does (In Plain Terms)

- Answers “Who is Haben?” in 2‑4 executive sentences, grounded in evidence
- Summarizes recent projects and technical work from live GitHub + portfolio
- Shares links on request and surfaces the most relevant citations
- Logs unknown questions and captures contact details for follow‑ups

## Key Capabilities

- Multi‑Source RAG over résumé + GitHub + LinkedIn + portfolio
- Intent‑aware routing (identity, projects, links, retrieval)
- Evidence‑grounded answers with citation logging (no hallucinations)
- Adaptive chunking and memory‑safe, batched processing
- Real‑time notifications (Pushover/email) for leads and gaps
- Deployed to Hugging Face Spaces with a clean Gradio UI

## Technical Stack (at a Glance)

| Category | Technology |
|----------|-----------|
| Language & Runtime | Python 3.12+ with `uv` |
| Vector Database | ChromaDB |
| Caching Layer | SQLite (TTL cache + logs) |
| AI/ML Services | OpenRouter (embeddings + chat) |
| Web Framework | Gradio (Hugging Face Spaces) |
| Data Processing | BeautifulSoup4, requests |
| Config | python‑dotenv |
| Architecture | Modular pipeline + supervisor + grounding validation |

## Architecture (How It Works)

```
Problem/Question
   ↓
Supervisor (Intent Router)
   ↓
Live + Local Data (GitHub, LinkedIn, Portfolio, résumé)
   ↓
RAG Pipeline: Ingest → Metadata → Adaptive Chunking → Embeddings → ChromaDB
   ↓
LLM Synthesis (OpenRouter) → Grounding Validation → Clean, cited answer
```

### Components

| Component | Purpose | Location |
|-----------|---------|----------|
| Supervisor | Orchestrates routing + response | `src/supervisor.py` |
| Router | Classifies intent | `src/router.py` |
| Tools | Live data connectors | `src/tools.py` |
| Pipeline | RAG processing | `src/pipeline/` |
| Vector Store | ChromaDB ops | `src/pipeline/vector_store.py` |
| Cache | SQLite TTL cache | `src/persistence.py` |
| UI | Gradio chat | `src/gradio_app.py` |

## Quick Start

```bash
# Clone and install
git clone https://github.com/habeneyasu/haben-career-twin.git
cd haben-career-twin
uv pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in OPENROUTER_* and profile URLs

# Build index
python3 - <<'PY'
from src.pipeline.run_pipeline import build_vector_index
print(build_vector_index(use_live=True, include_local_processed=True, dynamic_chunking=True))
PY

# Run app
python -m src.gradio_app
```

## Configuration (Essentials)

- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_EMBEDDING_MODEL`, `OPENROUTER_CHAT_MODEL`
- `GITHUB_PROFILE`, `PORTIFOLIO_PROFILE`, `LINKEDIN_PROFILE`
- `CHROMA_DB_PATH`, `CACHE_DB_PATH`, `RAYON_NUM_THREADS`, `TOKIO_WORKER_THREADS`

See `.env.example` for a complete list.

## Troubleshooting

- Empty answers? Rebuild the index and verify OpenRouter keys.
- Memory issues? Lower batch sizes and set thread limits to 1.
- Import errors? Run from project root and use `python -m src.gradio_app`.

## License & Contact

- License: MIT (see `LICENSE`)
- GitHub: [@habeneyasu](https://github.com/habeneyasu)
- LinkedIn: [habeneyasu](https://www.linkedin.com/in/habeneyasu)
- Portfolio: [habeneyasu.github.io](https://habeneyasu.github.io/)
