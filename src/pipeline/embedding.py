import os
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_EMBEDDING_MODEL = os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")
_EMBEDDING_CLIENT = None


def _get_embedding_client() -> OpenAI:
    global _EMBEDDING_CLIENT
    if _EMBEDDING_CLIENT is not None:
        return _EMBEDDING_CLIENT

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    base_url = os.getenv("OPENROUTER_BASE_URL", "").strip()
    if not api_key:
        raise ValueError("Missing OPENROUTER_API_KEY in environment")
    if not base_url:
        raise ValueError("Missing OPENROUTER_BASE_URL in environment")
    _EMBEDDING_CLIENT = OpenAI(api_key=api_key, base_url=base_url)
    return _EMBEDDING_CLIENT


def embed_texts(
    texts: List[str],
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    Returns vectors in the same order as input texts.
    """
    if not texts:
        return []

    client = _get_embedding_client()
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def embed_chunk_records(
    chunk_records: List[Dict[str, str]],
    model: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = 0,
) -> List[Dict[str, object]]:
    """
    Add embeddings to chunk records.

    Expected input fields per record:
    - content
    - document_id
    - chunk_index
    ... (any additional metadata is preserved)

    Returns a new list where each record has:
    - embedding: List[float]
    """
    if not chunk_records:
        return []
    resolved_batch_size = batch_size or int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
    if resolved_batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    enriched: List[Dict[str, object]] = []
    for i in range(0, len(chunk_records), resolved_batch_size):
        batch = chunk_records[i : i + resolved_batch_size]
        texts = [str(item.get("content", "")) for item in batch]
        vectors = embed_texts(texts, model=model)

        for item, vector in zip(batch, vectors):
            copied = dict(item)
            copied["embedding"] = vector
            copied["embedding_model"] = model
            enriched.append(copied)

    return enriched

