import json
import os
from typing import Dict, List

from src.persistence import cache_doc, get_cached_doc
from src.tools import CareerTools

SUPPORTED_EXTENSIONS = (".txt", ".md", ".json")


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
    if not os.path.isdir(processed_dir):
        return []

    documents: List[Dict[str, str]] = []

    for filename in sorted(os.listdir(processed_dir)):
        file_path = os.path.join(processed_dir, filename)
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
    cache_ttl_seconds: int = 3600,
    cache_db_path: str = "database/cache.db",
) -> List[Dict[str, str]]:
    """
    Ingest live documents using tools as the source of truth.

    Produces normalized documents:
    - document_id
    - source_name
    - source_path (live:// identifier)
    - content
    """
    documents: List[Dict[str, str]] = []

    # GitHub (top repos JSON pretty-printed)
    try:
        doc_id = "github_repos_live"
        cached = get_cached_doc(
            doc_id=doc_id,
            max_age_seconds=cache_ttl_seconds,
            db_path=cache_db_path,
        )
        if cached:
            content = cached
        else:
            repos = CareerTools.get_github_live()
            content = json.dumps(repos, ensure_ascii=True, indent=2) if repos else ""
            if content:
                cache_doc(doc_id=doc_id, content=content, db_path=cache_db_path)

        if content:
            documents.append(
                {
                    "document_id": doc_id,
                    "source_name": "github_repos_live.json",
                    "source_path": "live://github/api",
                    "content": content,
                }
            )
    except Exception:
        # Swallow to keep pipeline robust, caller may log externally
        pass

    # Portfolio (plain text)
    try:
        doc_id = "portfolio_live"
        cached = get_cached_doc(
            doc_id=doc_id,
            max_age_seconds=cache_ttl_seconds,
            db_path=cache_db_path,
        )
        if cached:
            content = cached
        else:
            portfolio_text = CareerTools.get_portfolio_live()
            content = portfolio_text.strip() if portfolio_text else ""
            if content:
                cache_doc(doc_id=doc_id, content=content, db_path=cache_db_path)

        if content:
            documents.append(
                {
                    "document_id": doc_id,
                    "source_name": "portfolio_live.txt",
                    "source_path": "live://portfolio/html",
                    "content": content,
                }
            )
    except Exception:
        pass

    # LinkedIn meta (link string)
    try:
        doc_id = "linkedin_meta_live"
        cached = get_cached_doc(
            doc_id=doc_id,
            max_age_seconds=cache_ttl_seconds,
            db_path=cache_db_path,
        )
        if cached:
            content = cached
        else:
            linkedin_meta = CareerTools.get_linkedin_meta()
            content = linkedin_meta.strip() if linkedin_meta else ""
            if content:
                cache_doc(doc_id=doc_id, content=content, db_path=cache_db_path)

        if content:
            documents.append(
                {
                    "document_id": doc_id,
                    "source_name": "linkedin_meta_live.txt",
                    "source_path": "live://linkedin/meta",
                    "content": content,
                }
            )
    except Exception:
        pass

    return documents


def ingest_documents(
    use_live: bool = True,
    include_local_processed: bool = False,
    processed_dir: str = "data/processed",
    cache_ttl_seconds: int = 3600,
    cache_db_path: str = "database/cache.db",
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

