from typing import Dict, Iterable, List, Optional

from src.pipeline.dynamic_chunker import choose_dynamic_chunk_params


def _find_backward_whitespace(text: str, start: int, end: int) -> int:
    """
    Try to avoid cutting words: search backward from `end` to the nearest whitespace.
    Returns the split index; if none found, return `end`.
    """
    i = end
    # Clamp within bounds
    if i > len(text):
        i = len(text)
    if i <= start:
        return end
    while i > start:
        if text[i - 1].isspace():
            return i
        i -= 1
    return end


def chunk_text(content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Character-based chunking with overlap and soft word boundaries.
    - chunk_size: maximum characters per chunk
    - overlap: number of characters to overlap between adjacent chunks
    """
    if not content:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    chunks: List[str] = []
    start = 0
    n = len(content)
    while start < n:
        raw_end = min(start + chunk_size, n)
        end = _find_backward_whitespace(content, start, raw_end)
        if end <= start:  # fallback if no whitespace found
            end = raw_end
        chunks.append(content[start:end])
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


def chunk_documents(
    documents: Iterable[Dict[str, str]],
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
    dynamic: bool = True,
) -> List[Dict[str, str]]:
    """
    Chunk multiple normalized documents.
    Input document expected keys:
      - document_id
      - source_name
      - source_path
      - content
    Returns list of chunk dicts:
      - document_id
      - chunk_index
      - content
      - source_name
      - source_path
      - chunk_size
      - total_chunks
    """
    all_chunks: List[Dict[str, str]] = []
    for doc in documents:
        base_id = doc.get("document_id", "")
        content = doc.get("content", "") or ""
        source_path = doc.get("source_path", "") or ""

        if dynamic:
            # Dynamic behavior is delegated to `dynamic_chunker.py`.
            selected_chunk_size, selected_overlap = choose_dynamic_chunk_params(
                content=content,
                source_path=source_path,
            )
            # Optional caller overrides
            if chunk_size is not None:
                selected_chunk_size = chunk_size
            if overlap is not None:
                selected_overlap = overlap
        else:
            selected_chunk_size = chunk_size if chunk_size is not None else 1000
            selected_overlap = overlap if overlap is not None else 200

        parts = chunk_text(
            content,
            chunk_size=selected_chunk_size,
            overlap=selected_overlap,
        )
        total = len(parts)
        for idx, part in enumerate(parts):
            all_chunks.append(
                {
                    "document_id": base_id,
                    "chunk_index": str(idx),
                    "content": part,
                    "source_name": doc.get("source_name", "") or "",
                    "source_path": doc.get("source_path", "") or "",
                    "chunk_size": str(len(part)),
                    "total_chunks": str(total),
                    "selected_chunk_size": str(selected_chunk_size),
                    "selected_overlap": str(selected_overlap),
                }
            )
    return all_chunks

