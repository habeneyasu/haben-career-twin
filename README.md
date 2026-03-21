# 🤖 H-CDT: Haben-Career Digital Twin

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Supervisor_Orchestration](https://img.shields.io/badge/Orchestration-Supervisor_Pattern-8A2BE2.svg)](#architecture-of-responsibility)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Persistent-green.svg)](https://www.trychroma.com/)
[![Deployed_on_HuggingFace](https://img.shields.io/badge/Deployed-HuggingFace_Spaces-yellow.svg)](https://huggingface.co/spaces)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

**Build and deploy your own Agent to represent you to potential future employers.**

**A Production-Grade Supervisor-Driven Autonomous AI Agent for Technical Recruiting.**

Combined example (two queries in one screenshot):

- Who is Haben, and what is his core engineering focus based only on available evidence?
- What are Haben’s recent projects, and for each one list business objective, technical stack, and measurable impact from available evidence?

![Combined Identity and Projects Responses](assets/screenshots/Screenshot%20from%202026-03-21%2014-05-02.png)

Replacing static resumes with a self-auditing, agentic proxy that provides real-time, grounded answers about my 8+ years of engineering experience.

H-CDT is designed as a reliability-first recruiting system, not a demo chatbot: it ingests trusted career evidence, retrieves relevant context in milliseconds, and responds with grounded, production-safe answers.

## Architecture of Responsibility

H-CDT uses a supervisor-first control plane so each component has a single operational responsibility:

- **Supervisor orchestration pattern:** The supervisor orchestrates intent routing, response assembly, and grounding checks across retrieval and action pathways.
- **Knowledge path (agent memory):** Retrieves and ranks evidence from resume, GitHub, LinkedIn, and portfolio data in ChromaDB.
- **Action path (tools):** Executes operational tools such as Pushover and SMTP notifications for recruiter lead capture and follow-up.
- **Guardrail before output:** Responses are validated against retrieved evidence to reduce hallucination risk before a final answer is returned.

```text
User Question
  -> Supervisor (orchestration + policy)
      -> Knowledge Path (retrieve + synthesize)
      -> Action Path (notify/log/follow-up)
  -> Grounding Validation
  -> Final Answer with Evidence Context
```

## Reliability and Evaluation (Production Differentiator)

Most agent demos stop at response generation. H-CDT adds an explicit reliability layer:

- **Single-LLM synthesis + grounding gate:** Primary LLM generates the response, then a deterministic grounding validator checks overlap with retrieved evidence before answer release.
- **Grounding-first responses:** The system answers from confirmed evidence (resume + GitHub + LinkedIn + portfolio corpus) and falls back to transparent uncertainty when context is missing.
- **Self-correction behavior (implemented):** A grounding gate validates LLM output against retrieved evidence; when validation fails, the supervisor falls back to deterministic evidence-formatted answers instead of speculative generation.
- **Latency-aware retrieval:** ChromaDB persistent indexing supports fast semantic lookup for recruiter-style questions.

## Streaming Ingestion Pipeline (O(1) Memory Footprint)

The ingestion/indexing pipeline is optimized for low-resource environments (including 8GB RAM machines):

- **Step 1 - Hash:** Deterministic IDs and dedup-ready document signatures.
- **Step 2 - Metadata:** Source-aware metadata normalization for reliable filtering/citation.
- **Step 3 - Chunk:** Dynamic chunking and overlap tuned for retrieval precision and context continuity.
- **Batch-safe upserts:** Embedding and vector writes run in bounded batches to keep memory usage stable as corpus size grows.

## Infrastructure as Code and MLOps Maturity

- **Dynamic chunking strategy:** Uses adaptive chunk sizes with overlap (default range controlled by env vars, typically 500-2000 chars) to balance retrieval precision and context continuity.
- **Secret management (zero-trust):** Runtime keys are injected via environment variables and deployment secrets (`.env` locally, Hugging Face Secrets in cloud).
- **Real-time observability:** Pushover + email notifications act as production monitoring hooks when high-value recruiter leads are captured.
  - Instant push notifications via Pushover allow for real-time engagement when technical recruiters interact with the system.
- **Deployment discipline:** Single-entry app for Hugging Face Spaces (`app.py`) with modular pipeline components under `src/pipeline/`.

## Core Stack

| Layer | Technology |
|---|---|
| Runtime | Python, `uv` |
| LLM + Embeddings | OpenRouter-compatible models |
| Agent Memory & Retrieval | ChromaDB (persistent vector knowledge store) |
| Orchestration | Supervisor/sub-agent control flow |
| Interface | Gradio (Hugging Face Spaces) |
| Persistence | SQLite + JSONL logs |

## Quick Start

```bash
git clone https://github.com/habeneyasu/haben-career-twin.git
cd haben-career-twin
uv sync

# Configure runtime secrets and profile URLs in .env

python3 - <<'PY'
from src.pipeline.run_pipeline import build_vector_index
print(build_vector_index(use_live=True, include_local_processed=True, dynamic_chunking=True))
PY

python -m src.gradio_app
```

## Repository Map

- `src/supervisor.py` - orchestration, grounding checks, lead-capture notifications
- `src/router.py` - intent classifier called by the supervisor (routing policy)
- `src/tools.py` - external data/tool adapters
- `src/pipeline/` - ingestion, metadata, chunking, embedding, indexing
- `src/pipeline/vector_store.py` - ChromaDB upsert/query abstraction
- `src/gradio_app.py` - UI runtime
- `app.py` - Hugging Face Spaces entrypoint

## License and Contact

- MIT License (`LICENSE`)
- [GitHub](https://github.com/habeneyasu)
- [LinkedIn](https://www.linkedin.com/in/habeneyasu)
- [Portfolio](https://habeneyasu.github.io/)
