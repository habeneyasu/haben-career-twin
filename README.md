# H-CDT: Haben's Career Digital Twin

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Gradio](https://img.shields.io/badge/Gradio-5.9+-orange.svg)](https://gradio.app/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Latest-green.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Production-ready AI agent** that transforms static résumé data and live professional signals (LinkedIn, GitHub, Portfolio) into credible, on-demand answers. Built with RAG architecture, evidence-grounded validation, and enterprise-grade scalability.

## 🎯 Business Objective

H-CDT creates an **always-available, evidence-grounded AI agent** that represents professional expertise and recent work 24/7, enabling:

- **Automated Professional Presence**: Instant, accurate responses about skills, projects, and experience without manual intervention
- **Stakeholder Engagement**: Supports hiring workflows, client inquiries, and networking with credible, source-cited answers
- **Live Data Integration**: Continuously incorporates latest work from GitHub, LinkedIn, and portfolio to maintain currency
- **Lead Capture**: Automated capture of visitor interest and questions for network expansion
- **Scalable Knowledge Base**: Demonstrates production-grade RAG architecture suitable for enterprise deployment

## ✨ Key Features

- **Multi-Source RAG**: Combines static résumé with live GitHub, LinkedIn, and portfolio data
- **Intent-Aware Routing**: Intelligent query classification (identity, projects, links, general retrieval)
- **Evidence-Grounded Responses**: Anti-hallucination validation with source citations
- **Adaptive Chunking**: Dynamic text segmentation optimized for content density and source type
- **Memory-Optimized**: Streaming ingestion, batched processing, low-thread operations for resource-constrained environments
- **Real-Time Notifications**: Pushover and email alerts for lead capture and unanswered questions
- **Production-Ready**: Deployed on Hugging Face Spaces with Gradio interface

## 🛠️ Technical Stack

| Category | Technology |
|----------|-----------|
| **Language & Runtime** | Python 3.12+ with `uv` dependency management |
| **Vector Database** | ChromaDB for persistent embedding storage and semantic search |
| **Caching Layer** | SQLite for TTL-controlled ingestion cache and lead/question logging |
| **AI/ML Services** | OpenRouter API (embeddings: `text-embedding-3-small`, chat: `gpt-4o-mini`) |
| **Web Framework** | Gradio for interactive chat interface and Hugging Face Spaces deployment |
| **Data Processing** | BeautifulSoup4 (HTML parsing), requests (HTTP client) |
| **Configuration** | python-dotenv for environment-driven configuration |
| **Architecture** | Modular pipeline (ingestion → metadata → chunking → embedding → retrieval), supervisor-based routing, grounded response validation |

## 📊 Measured/Expected Impact

- **Availability**: 24/7 automated professional presence without manual maintenance
- **Response Quality**: Evidence-grounded answers with source citations, reducing hallucination risk through validation layers
- **Data Freshness**: Live integration ensures responses reflect current work and achievements
- **Scalability**: Memory-optimized processing supports resource-constrained deployments (tested on CPU-basic tier)
- **Lead Generation**: Automated capture of visitor contact details and unanswered questions
- **Demonstration Value**: Showcases production-grade RAG implementation for enterprise knowledge management and AI agent architectures

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- `uv` package manager (or `pip`)
- OpenRouter API key ([get one here](https://openrouter.ai/))
- GitHub, LinkedIn, and Portfolio profile URLs

### Installation

```bash
# Clone repository
git clone https://github.com/habeneyasu/haben-career-twin.git
cd haben-career-twin

# Install dependencies
uv pip install -r requirements.txt

# Or with pip
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
# Required: OpenRouter Configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-3-small
OPENROUTER_CHAT_MODEL=openai/gpt-4o-mini

# Required: Profile URLs
GITHUB_PROFILE=https://github.com/yourusername
PORTIFOLIO_PROFILE=https://yourportfolio.com
LINKEDIN_PROFILE=https://www.linkedin.com/in/yourprofile

# Optional: Notifications
PUSHOVER_API_TOKEN=your_token
PUSHOVER_USER_KEY=your_user_key
```

See full configuration options in [Configuration](#-configuration) section.

### Build Vector Index

```bash
python3 - <<'PY'
from src.pipeline.run_pipeline import build_vector_index
result = build_vector_index(
    use_live=True,
    include_local_processed=True,
    dynamic_chunking=True
)
print(f"Indexed {result['documents_ingested']} documents, {result['chunks_created']} chunks")
PY
```

### Run Locally

```bash
# Start Gradio interface
python app.py

# Or via module
python -m src.gradio_app
```

The interface will be available at `http://localhost:7860`

## 💬 Usage Examples

### Identity Query
```
User: "Tell me who is Haben?"
Agent: [Returns concise 2-4 sentence professional profile with role, specialization, and proof points]
```

### Project Query
```
User: "What are Haben's recent projects and technical work?"
Agent: [Returns structured response with Project, Business Objective, Core Capabilities, Technical Stack, Impact]
```

### Links Query
```
User: "Share your links"
Agent: [Returns LinkedIn, GitHub, and Portfolio URLs]
```

### General Retrieval
```
User: "What ML frameworks has Haben worked with?"
Agent: [Returns evidence-grounded answer with source citations]
```

## 🏗️ Architecture

### Interaction Flow

```
User Query
    ↓
Supervisor (Intent Routing)
    ↓
┌─────────────────────────────────────┐
│  Intent Detection                   │
│  - get_links                        │
│  - github_live                      │
│  - identity                          │
│  - retrieval (default)              │
└─────────────────────────────────────┘
    ↓
Targeted Data Access
    ↓
┌─────────────────────────────────────┐
│  Live Sources: GitHub, LinkedIn,    │
│  Portfolio (with SQLite cache)      │
│  + Local: resume.md                 │
└─────────────────────────────────────┘
    ↓
RAG Pipeline
    ↓
┌─────────────────────────────────────┐
│  1. Ingestion (with caching)        │
│  2. Metadata Enrichment             │
│  3. Adaptive Chunking               │
│  4. Embedding (OpenRouter)          │
│  5. Vector Storage (ChromaDB)       │
│  6. Semantic Search                 │
└─────────────────────────────────────┘
    ↓
Response Generation
    ↓
┌─────────────────────────────────────┐
│  Post-RAG LLM Synthesis             │
│  + Grounding Validation              │
│  + Fallback Formatting               │
└─────────────────────────────────────┘
    ↓
Business-Ready Response with Citations
```

### Component Overview

| Component | Purpose | Location |
|-----------|---------|----------|
| **Supervisor** | Intent routing, response orchestration | `src/supervisor.py` |
| **Router** | Query classification | `src/router.py` |
| **Tools** | Live data connectors (GitHub, LinkedIn, Portfolio) | `src/tools.py` |
| **Pipeline** | End-to-end RAG processing | `src/pipeline/` |
| **Vector Store** | ChromaDB persistence and querying | `src/pipeline/vector_store.py` |
| **Cache** | SQLite TTL caching | `src/persistence.py` |
| **UI** | Gradio chat interface | `src/gradio_app.py` |

## 📁 Project Structure

```
haben-career-twin/
├── app.py                 # Hugging Face Spaces entrypoint
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .env                  # Environment configuration (not in repo)
├── src/
│   ├── supervisor.py     # Main orchestration and response generation
│   ├── router.py          # Intent routing logic
│   ├── tools.py           # Live data connectors
│   ├── persistence.py     # SQLite caching layer
│   ├── gradio_app.py     # Gradio UI interface
│   └── pipeline/
│       ├── ingestion.py   # Document ingestion (live + local)
│       ├── metadata.py    # Metadata enrichment
│       ├── chunking.py    # Text chunking logic
│       ├── dynamic_chunker.py  # Adaptive chunking strategy
│       ├── embedding.py   # OpenRouter embedding generation
│       ├── vector_store.py     # ChromaDB operations
│       └── run_pipeline.py     # End-to-end pipeline orchestration
├── data/
│   ├── processed/        # Normalized résumé and curated artifacts
│   └── raw/              # Source documents (not in repo)
└── database/
    ├── chroma_db/        # Vector index (persistent)
    └── cache.db          # Ingestion cache (TTL-controlled)
```

## ⚙️ Configuration

All runtime parameters are environment-driven. Key variables:

### Required

- `OPENROUTER_API_KEY`: OpenRouter API key
- `OPENROUTER_BASE_URL`: OpenRouter API endpoint
- `GITHUB_PROFILE`, `PORTIFOLIO_PROFILE`, `LINKEDIN_PROFILE`: Profile URLs

### Optional (with defaults)

- `OPENROUTER_EMBEDDING_MODEL`: Embedding model (default: `openai/text-embedding-3-small`)
- `OPENROUTER_CHAT_MODEL`: Chat model (default: `openai/gpt-4o-mini`)
- `EMBEDDING_BATCH_SIZE`: Batch size for embeddings (default: `100`)
- `VECTOR_QUERY_TOP_K`: Number of results per query (default: `5`)
- `GITHUB_REPO_LIMIT`: Max repos to fetch (default: `5`)
- `MAX_LIVE_DOC_CHARS`: Max characters per live document (default: `50000`)
- `DYNAMIC_CHUNK_MIN_SIZE`, `DYNAMIC_CHUNK_MAX_SIZE`: Chunk size bounds
- `RAYON_NUM_THREADS`, `TOKIO_WORKER_THREADS`: Thread limits for ChromaDB (default: `1`)
- `SHOW_CITATIONS_IN_LOG`: Enable citation logging (default: `true`)
- `USE_OPENAI_AFTER_RAG`: Enable post-RAG LLM synthesis (default: `true`)

See `.env.example` for complete configuration reference.

## 🚢 Deployment

### Hugging Face Spaces

1. **Create Space:**
   - Go to [Hugging Face Spaces](https://huggingface.co/spaces)
   - Click "Create new Space"
   - Select SDK: `Gradio`, Hardware: `CPU basic`

2. **Push Code:**
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/haben-career-twin
   cd haben-career-twin
   # Copy project files
   git add .
   git commit -m "Initial deployment"
   git push
   ```

3. **Configure Secrets:**
   - Go to Space Settings → Variables and secrets
   - Add required secrets: `OPENROUTER_API_KEY`, profile URLs, etc.

4. **Access:** Your Space will be available at `https://huggingface.co/spaces/YOUR_USERNAME/haben-career-twin`

## 🧪 Testing

### Unit Tests
```bash
# Run pipeline components
python -m src.pipeline.run_pipeline

# Test supervisor
python -m src.supervisor "Tell me who is Haben?"
```

### Integration Test
```bash
# Build index and query
python3 - <<'PY'
from src.pipeline.run_pipeline import build_vector_index, search_similar_content

# Build
print(build_vector_index(use_live=True, include_local_processed=True))

# Query
results = search_similar_content("Haben's recent projects", top_k=3)
print(f"Found {len(results)} results")
PY
```

## 🐛 Troubleshooting

### Memory Issues
- Set `RAYON_NUM_THREADS=1` and `TOKIO_WORKER_THREADS=1`
- Reduce `EMBEDDING_BATCH_SIZE` and `VECTOR_UPSERT_BATCH_SIZE`
- Lower `MAX_LIVE_DOC_CHARS` and `MAX_DOC_CHARS`

### Empty Responses
- Verify `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL` are set
- Check that vector index is built: `ls database/chroma_db/`
- Rebuild index if needed

### Import Errors
- Ensure `src/` is in Python path
- Run from project root: `python -m src.gradio_app`

### ChromaDB Thread Errors
- Set `RAYON_NUM_THREADS=1` and `TOKIO_WORKER_THREADS=1` before importing ChromaDB

## 📈 Roadmap

### Phase 1 (Current) ✅
- [x] Live data connectors (GitHub, LinkedIn, Portfolio)
- [x] RAG pipeline (ingestion → embedding → retrieval)
- [x] Supervisor intent routing
- [x] Evidence-grounded response generation
- [x] Gradio UI and Hugging Face deployment

### Phase 2 (In Progress)
- [ ] Evaluator pass (tone/accuracy guardrail)
- [ ] OpenAI Agents SDK integration
- [ ] Enhanced conversational context
- [ ] Multi-turn dialogue support

### Phase 3 (Planned)
- [ ] Advanced analytics dashboard
- [ ] Custom knowledge base expansion
- [ ] API endpoints for external integration
- [ ] Multi-language support

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Gradio](https://gradio.app/) for the UI
- Powered by [OpenRouter](https://openrouter.ai/) for AI services
- Vector storage via [ChromaDB](https://www.trychroma.com/)
- Deployed on [Hugging Face Spaces](https://huggingface.co/spaces)

## 📧 Contact

- **GitHub**: [@habeneyasu](https://github.com/habeneyasu)
- **LinkedIn**: [habeneyasu](https://www.linkedin.com/in/habeneyasu)
- **Portfolio**: [habeneyasu.github.io](https://habeneyasu.github.io/)

---

**Built with ❤️ to demonstrate production-grade RAG architecture and AI agent capabilities.**
