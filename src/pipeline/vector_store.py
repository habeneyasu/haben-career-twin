import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()


def _safe_int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, value)


# Must be set before importing chromadb/rust runtime.
os.environ.setdefault("RAYON_NUM_THREADS", str(_safe_int_env("RAYON_NUM_THREADS", 1)))
os.environ.setdefault("TOKIO_WORKER_THREADS", str(_safe_int_env("TOKIO_WORKER_THREADS", 1)))

import chromadb
from chromadb.config import Settings

_CHROMA_CLIENT = None
_CHROMA_COLLECTION = None


def _get_chroma_client():
    global _CHROMA_CLIENT
    if _CHROMA_CLIENT is not None:
        return _CHROMA_CLIENT

    db_path = os.getenv("CHROMA_DB_PATH", "database/chroma_db")
    os.makedirs(db_path, exist_ok=True)
    _CHROMA_CLIENT = chromadb.PersistentClient(
        path=db_path,
        settings=Settings(anonymized_telemetry=False),
    )
    return _CHROMA_CLIENT


def _get_collection():
    global _CHROMA_COLLECTION
    if _CHROMA_COLLECTION is not None:
        return _CHROMA_COLLECTION

    client = _get_chroma_client()
    collection_name = os.getenv("CHROMA_COLLECTION", "haben_career_knowledge")
    _CHROMA_COLLECTION = client.get_or_create_collection(name=collection_name)
    return _CHROMA_COLLECTION


def _upsert_batch(collection, records: List[Dict[str, object]]) -> int:
    ids: List[str] = []
    documents: List[str] = []
    embeddings: List[List[float]] = []
    metadatas: List[Dict[str, str]] = []

    for record in records:
        document_id = str(record.get("document_id", "unknown"))
        chunk_index = str(record.get("chunk_index", "0"))
        content = str(record.get("content", ""))
        vector = record.get("embedding")

        if not content or not isinstance(vector, list):
            continue

        ids.append(f"{document_id}_chunk_{chunk_index}")
        documents.append(content)
        embeddings.append(vector)

        metadata: Dict[str, str] = {}
        for k, v in record.items():
            if k in ("content", "embedding"):
                continue
            metadata[str(k)] = str(v)
        metadatas.append(metadata)

    if not ids:
        return 0

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return len(ids)


def upsert_embedding_records(records: List[Dict[str, object]]) -> int:
    """
    Upsert embedded chunk records into ChromaDB.

    Expected record keys:
    - document_id
    - chunk_index
    - content
    - embedding (List[float])
    Additional keys are stored as metadata.
    """
    if not records:
        return 0

    collection = _get_collection()
    upsert_batch_size = _safe_int_env("VECTOR_UPSERT_BATCH_SIZE", 50)

    total = 0
    for i in range(0, len(records), upsert_batch_size):
        batch = records[i : i + upsert_batch_size]
        total += _upsert_batch(collection, batch)
    return total


def query_similar_chunks(
    query_embedding: List[float],
    top_k: int = 0,
) -> List[Dict[str, object]]:
    """
    Query ChromaDB using a query embedding and return normalized results.
    """
    if not query_embedding:
        return []

    resolved_top_k = top_k or _safe_int_env("VECTOR_QUERY_TOP_K", 5)
    collection = _get_collection()
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=resolved_top_k,
    )

    docs = result.get("documents", [[]])[0] or []
    metas = result.get("metadatas", [[]])[0] or []
    distances = result.get("distances", [[]])[0] or []
    ids = result.get("ids", [[]])[0] or []

    formatted: List[Dict[str, object]] = []
    for i in range(len(docs)):
        formatted.append(
            {
                "id": ids[i] if i < len(ids) else "",
                "content": docs[i],
                "metadata": metas[i] if i < len(metas) else {},
                "distance": distances[i] if i < len(distances) else None,
            }
        )
    return formatted

