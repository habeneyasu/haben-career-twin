import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _is_live_source(source_path: str) -> bool:
    return isinstance(source_path, str) and source_path.startswith("live://")


def _sha256(text: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()


def build_document_metadata(
    document: Dict[str, str],
    default_ttl_seconds: int = 3600,
    source_kind: Optional[str] = None,
) -> Dict[str, str]:
    """
    Build normalized document-level metadata.
    - Adds identifiers, timing, origin, size, and a content hash for change tracking.
    """
    content = document.get("content", "") or ""
    source_path = document.get("source_path", "") or ""
    live = _is_live_source(source_path)

    resolved_source_kind = source_kind or ("live" if live else "local")

    return {
        "document_id": document.get("document_id", "") or "",
        "source_name": document.get("source_name", "") or "",
        "source_path": source_path,
        "source_kind": resolved_source_kind,  # live | local
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "content_length": str(len(content)),
        "content_sha256": _sha256(content),
        "default_ttl_seconds": str(int(default_ttl_seconds)),
    }


def build_all_metadata(
    documents: List[Dict[str, str]],
    default_ttl_seconds: int = 3600,
) -> List[Dict[str, str]]:
    """
    Convenience helper to create metadata objects for a list of documents.
    """
    return [
        build_document_metadata(d, default_ttl_seconds=default_ttl_seconds)
        for d in documents
    ]

