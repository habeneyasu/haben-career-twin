import json
import os
import asyncio
import re
from typing import Dict, List

from dotenv import load_dotenv

from src.persistence import cache_doc, get_cached_doc
from src.tools import CareerTools

load_dotenv()

SUPPORTED_EXTENSIONS = tuple(
    ext.strip().lower()
    for ext in os.getenv("INGEST_SUPPORTED_EXTENSIONS", ".txt,.md,.json").split(",")
    if ext.strip()
)
MAX_LIVE_DOC_CHARS = int(os.getenv("MAX_LIVE_DOC_CHARS", "50000"))
INGEST_DEBUG = os.getenv("INGEST_DEBUG", "false").lower() == "true"


def _cap_text(text: str) -> str:
    if not text:
        return ""
    if MAX_LIVE_DOC_CHARS <= 0:
        return text
    return text[:MAX_LIVE_DOC_CHARS]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "section"


def _read_file_content(file_path: str) -> str:
    """Read file content and normalize to plain text."""
    _, ext = os.path.splitext(file_path.lower())

    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        # Keep JSON deterministic and human-readable for later chunking.
        return json.dumps(payload, ensure_ascii=True, indent=2)

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def ingest_processed_documents(processed_dir: str = "data/processed") -> List[Dict[str, str]]:
    """
    Ingest processed documents from disk.

    Returns a normalized list of document dictionaries:
    - document_id
    - source_path
    - source_name
    - content
    """
    resolved_dir = processed_dir or os.getenv("PROCESSED_DATA_DIR", "data/processed")
    if not os.path.isdir(resolved_dir):
        return []

    documents: List[Dict[str, str]] = []

    for filename in sorted(os.listdir(resolved_dir)):
        file_path = os.path.join(resolved_dir, filename)
        if not os.path.isfile(file_path):
            continue
        if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
            continue

        content = _read_file_content(file_path).strip()
        if not content:
            continue

        document_id, _ = os.path.splitext(filename)
        documents.append(
            {
                "document_id": document_id,
                "source_name": filename,
                "source_path": file_path,
                "content": content,
            }
        )

    return documents


def ingest_live_documents(
    cache_ttl_seconds: int = 0,
    cache_db_path: str = "",
) -> List[Dict[str, str]]:
    """
    Ingest live documents using tools as the source of truth.

    Produces normalized documents:
    - document_id
    - source_name
    - source_path (live:// identifier)
    - content
    """
    resolved_ttl = cache_ttl_seconds or int(os.getenv("INGEST_CACHE_TTL_SECONDS", "3600"))
    resolved_cache_db_path = cache_db_path or os.getenv("CACHE_DB_PATH", "database/cache.db")

    documents: List[Dict[str, str]] = []

    # GitHub (top repos JSON pretty-printed)
    try:
        doc_id = "github_repos_live"
        cached = get_cached_doc(
            doc_id=doc_id,
            max_age_seconds=resolved_ttl,
            db_path=resolved_cache_db_path,
        )
        if cached:
            content = _cap_text(cached)
        else:
            repos = CareerTools.get_github_live()
            content = _cap_text(json.dumps(repos, ensure_ascii=True, indent=2) if repos else "")
            if content:
                cache_doc(doc_id=doc_id, content=content, db_path=resolved_cache_db_path)

        if content:
            documents.append(
                {
                    "document_id": doc_id,
                    "source_name": "github_repos_live.json",
                    "source_path": "live://github/api",
                    "content": content,
                }
            )
    except Exception as exc:
        if INGEST_DEBUG:
            print(f"[ingest_live_documents] github failed: {exc}")

    # Portfolio (heading-aware sections)
    try:
        doc_id = "portfolio_sections_live"
        cached = get_cached_doc(
            doc_id=doc_id,
            max_age_seconds=resolved_ttl,
            db_path=resolved_cache_db_path,
        )
        if cached:
            section_payload = json.loads(cached)
        else:
            sections = CareerTools.get_portfolio_live_sections()
            section_payload = [
                {
                    "section_title": s.get("section_title", ""),
                    "section_slug": s.get("section_slug", ""),
                    "content": _cap_text(s.get("content", "")),
                }
                for s in sections
            ]
            if section_payload:
                cache_doc(
                    doc_id=doc_id,
                    content=json.dumps(section_payload, ensure_ascii=True),
                    db_path=resolved_cache_db_path,
                )

        for idx, section in enumerate(section_payload):
            content = _cap_text(section.get("content", ""))
            if not content:
                continue
            slug = _slugify(section.get("section_slug") or section.get("section_title") or f"section-{idx}")
            documents.append(
                {
                    "document_id": f"portfolio_live_{slug}_{idx}",
                    "source_name": f"portfolio_{slug}.txt",
                    "source_path": "live://portfolio/html",
                    "content": content,
                    "section_title": section.get("section_title", ""),
                }
            )
    except Exception as exc:
        if INGEST_DEBUG:
            print(f"[ingest_live_documents] portfolio failed: {exc}")

    # LinkedIn live profile metadata
    try:
        doc_id = "linkedin_meta_live"
        cached = get_cached_doc(
            doc_id=doc_id,
            max_age_seconds=resolved_ttl,
            db_path=resolved_cache_db_path,
        )
        if cached:
            content = _cap_text(cached)
        else:
            linkedin_live = CareerTools.get_linkedin_live()
            content = _cap_text(linkedin_live.strip() if linkedin_live else "")
            if content:
                cache_doc(doc_id=doc_id, content=content, db_path=resolved_cache_db_path)

        if content:
            documents.append(
                {
                    "document_id": doc_id,
                    "source_name": "linkedin_meta_live.txt",
                    "source_path": "live://linkedin/meta",
                    "content": content,
                }
            )
    except Exception as exc:
        if INGEST_DEBUG:
            print(f"[ingest_live_documents] linkedin failed: {exc}")

    return documents


async def ingest_live_documents_async(
    cache_ttl_seconds: int = 0,
    cache_db_path: str = "",
) -> List[Dict[str, str]]:
    """
    Async variant of live ingestion.
    It runs each source fetch in a thread to reduce wall-clock waiting time.
    """
    resolved_ttl = cache_ttl_seconds or int(os.getenv("INGEST_CACHE_TTL_SECONDS", "3600"))
    resolved_cache_db_path = cache_db_path or os.getenv("CACHE_DB_PATH", "database/cache.db")

    async def _github_doc():
        doc_id = "github_repos_live"
        cached = get_cached_doc(doc_id=doc_id, max_age_seconds=resolved_ttl, db_path=resolved_cache_db_path)
        if cached:
            content = _cap_text(cached)
        else:
            repos = await asyncio.to_thread(CareerTools.get_github_live)
            content = _cap_text(json.dumps(repos, ensure_ascii=True, indent=2) if repos else "")
            if content:
                cache_doc(doc_id=doc_id, content=content, db_path=resolved_cache_db_path)
        if not content:
            return None
        return {
            "document_id": doc_id,
            "source_name": "github_repos_live.json",
            "source_path": "live://github/api",
            "content": content,
        }

    async def _portfolio_doc():
        doc_id = "portfolio_sections_live"
        cached = get_cached_doc(doc_id=doc_id, max_age_seconds=resolved_ttl, db_path=resolved_cache_db_path)
        if cached:
            section_payload = json.loads(cached)
        else:
            sections = await asyncio.to_thread(CareerTools.get_portfolio_live_sections)
            section_payload = [
                {
                    "section_title": s.get("section_title", ""),
                    "section_slug": s.get("section_slug", ""),
                    "content": _cap_text(s.get("content", "")),
                }
                for s in sections
            ]
            if section_payload:
                cache_doc(
                    doc_id=doc_id,
                    content=json.dumps(section_payload, ensure_ascii=True),
                    db_path=resolved_cache_db_path,
                )
        if not section_payload:
            return None
        docs = []
        for idx, section in enumerate(section_payload):
            content = _cap_text(section.get("content", ""))
            if not content:
                continue
            slug = _slugify(section.get("section_slug") or section.get("section_title") or f"section-{idx}")
            docs.append(
                {
                    "document_id": f"portfolio_live_{slug}_{idx}",
                    "source_name": f"portfolio_{slug}.txt",
                    "source_path": "live://portfolio/html",
                    "content": content,
                    "section_title": section.get("section_title", ""),
                }
            )
        return docs

    async def _linkedin_doc():
        doc_id = "linkedin_meta_live"
        cached = get_cached_doc(doc_id=doc_id, max_age_seconds=resolved_ttl, db_path=resolved_cache_db_path)
        if cached:
            content = _cap_text(cached)
        else:
            linkedin_live = await asyncio.to_thread(CareerTools.get_linkedin_live)
            content = _cap_text(linkedin_live.strip() if linkedin_live else "")
            if content:
                cache_doc(doc_id=doc_id, content=content, db_path=resolved_cache_db_path)
        if not content:
            return None
        return {
            "document_id": doc_id,
            "source_name": "linkedin_meta_live.txt",
            "source_path": "live://linkedin/meta",
            "content": content,
        }

    tasks = [_github_doc(), _portfolio_doc(), _linkedin_doc()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    docs: List[Dict[str, str]] = []
    for result in results:
        if isinstance(result, Exception):
            if INGEST_DEBUG:
                print(f"[ingest_live_documents_async] source failed: {result}")
            continue
        if result:
            if isinstance(result, list):
                docs.extend(result)
            else:
                docs.append(result)
    return docs


def ingest_documents(
    use_live: bool = True,
    include_local_processed: bool = False,
    processed_dir: str = "",
    cache_ttl_seconds: int = 0,
    cache_db_path: str = "",
) -> List[Dict[str, str]]:
    """
    Primary ingestion entrypoint.
    - If use_live: pull from tools (GitHub/Portfolio/LinkedIn)
    - If include_local_processed: merge with files from data/processed
    """
    docs: List[Dict[str, str]] = []
    if use_live:
        docs.extend(
            ingest_live_documents(
                cache_ttl_seconds=cache_ttl_seconds,
                cache_db_path=cache_db_path,
            )
        )
    if include_local_processed:
        docs.extend(ingest_processed_documents(processed_dir=processed_dir))
    return docs

