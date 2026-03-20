from typing import Dict, Iterable, List, Optional

from src.pipeline.dynamic_chunker import choose_dynamic_chunk_params
from src.utils import safe_int_env


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


def _find_backward_natural_boundary(text: str, start: int, end: int) -> int:
    """
    Prefer splitting at natural boundaries near the target end:
    paragraph -> sentence -> whitespace.
    """
    if end <= start:
        return end

    # Avoid tiny chunks by only searching boundaries in the latter window.
    window_start = max(start, end - 220)
    segment = text[window_start:end]

    # 1) Paragraph boundary
    para_idx = segment.rfind("\n\n")
    if para_idx != -1:
        return window_start + para_idx + 2

    # 2) Sentence boundary
    sentence_markers = [". ", "! ", "? ", ".\n", "!\n", "?\n"]
    candidate = -1
    for marker in sentence_markers:
        pos = segment.rfind(marker)
        if pos > candidate:
            candidate = pos
    if candidate != -1:
        return window_start + candidate + 1

    # 3) Fallback: any whitespace
    return _find_backward_whitespace(text, start, end)


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
        end = _find_backward_natural_boundary(content, start, raw_end)
        if end <= start:  # fallback if no whitespace found
            end = raw_end
        chunks.append(content[start:end])
        if end >= n:
            break
        # Ensure forward progress even when overlap is large or split is tiny.
        next_start = max(0, end - overlap)
        if next_start <= start:
            next_start = end
        start = next_start
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
    max_doc_chars = safe_int_env("MAX_DOC_CHARS", 50000, minimum=0)
    short_doc_threshold = safe_int_env("SHORT_DOC_NO_CHUNK_THRESHOLD", 800)
    all_chunks: List[Dict[str, str]] = []
    for doc in documents:
        base_id = doc.get("document_id", "")
        raw_content = doc.get("content", "") or ""
        # Hard memory guard: cap per-document content before chunking.
        content = raw_content[:max_doc_chars] if max_doc_chars > 0 else raw_content
        source_path = doc.get("source_path", "") or ""

        # For short docs, force single chunk to reduce retrieval noise.
        if len(content) <= short_doc_threshold:
            selected_chunk_size = max(1, len(content))
            selected_overlap = 0
            parts = [content] if content else []
        elif dynamic:
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
            parts = chunk_text(
                content,
                chunk_size=selected_chunk_size,
                overlap=selected_overlap,
            )
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

