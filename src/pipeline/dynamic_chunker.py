from typing import Tuple


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def choose_dynamic_chunk_params(
    content: str,
    source_path: str = "",
    min_chunk_size: int = 500,
    max_chunk_size: int = 2000,
) -> Tuple[int, int]:
    """
    Decide dynamic chunk settings for a single document.

    Heuristics:
    - Larger documents get larger chunk sizes to reduce fragment count.
    - Live/API content gets slightly smaller chunks for precision.
    - Dense text (few newlines) uses more overlap for context continuity.
    """
    n = len(content or "")
    if n == 0:
        return 1000, 200

    if n < 2_000:
        chunk_size = 600
    elif n < 8_000:
        chunk_size = 900
    elif n < 20_000:
        chunk_size = 1200
    else:
        chunk_size = 1600

    if (source_path or "").startswith("live://"):
        chunk_size -= 100

    newline_ratio = content.count("\n") / max(1, n)
    overlap_ratio = 0.20 if newline_ratio < 0.015 else 0.15

    chunk_size = _clamp(chunk_size, min_chunk_size, max_chunk_size)
    overlap = max(80, int(chunk_size * overlap_ratio))
    overlap = min(overlap, chunk_size - 1)
    return chunk_size, overlap


def choose_chunk_params(
    content: str,
    source_path: str = "",
    min_chunk_size: int = 500,
    max_chunk_size: int = 2000,
) -> Tuple[int, int]:
    """
    Backward-compatible alias.
    Prefer `choose_dynamic_chunk_params` for clearer naming.
    """
    return choose_dynamic_chunk_params(
        content=content,
        source_path=source_path,
        min_chunk_size=min_chunk_size,
        max_chunk_size=max_chunk_size,
    )

