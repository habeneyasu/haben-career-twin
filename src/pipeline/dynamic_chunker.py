import os
from typing import Tuple

from dotenv import load_dotenv

load_dotenv()

def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def _safe_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _safe_float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def choose_dynamic_chunk_params(
    content: str,
    source_path: str = "",
    min_chunk_size: int = 0,
    max_chunk_size: int = 0,
) -> Tuple[int, int]:
    """
    Decide dynamic chunk settings for a single document.

    Heuristics:
    - Larger documents get larger chunk sizes to reduce fragment count.
    - Live/API content gets slightly smaller chunks for precision.
    - Dense text (few newlines) uses more overlap for context continuity.
    """
    n = len(content or "")
    resolved_min = min_chunk_size or _safe_int_env("DYNAMIC_CHUNK_MIN_SIZE", 500)
    resolved_max = max_chunk_size or _safe_int_env("DYNAMIC_CHUNK_MAX_SIZE", 2000)
    live_size_delta = _safe_int_env("DYNAMIC_CHUNK_LIVE_SIZE_DELTA", 100)
    dense_overlap_ratio = _safe_float_env("DYNAMIC_CHUNK_DENSE_OVERLAP_RATIO", 0.20)
    normal_overlap_ratio = _safe_float_env("DYNAMIC_CHUNK_NORMAL_OVERLAP_RATIO", 0.15)
    dense_newline_threshold = _safe_float_env("DYNAMIC_CHUNK_DENSE_NEWLINE_THRESHOLD", 0.015)
    min_overlap = _safe_int_env("DYNAMIC_CHUNK_MIN_OVERLAP", 80)

    # Hard upper safety bounds to avoid accidental giant slices from bad env values.
    resolved_min = _clamp(resolved_min, 64, 4000)
    resolved_max = _clamp(resolved_max, resolved_min, 4000)

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
        chunk_size -= live_size_delta

    newline_ratio = content.count("\n") / max(1, n)
    overlap_ratio = dense_overlap_ratio if newline_ratio < dense_newline_threshold else normal_overlap_ratio

    chunk_size = _clamp(chunk_size, resolved_min, resolved_max)
    overlap = max(min_overlap, int(chunk_size * overlap_ratio))
    overlap = min(overlap, chunk_size - 1)
    return chunk_size, overlap


def choose_chunk_params(
    content: str,
    source_path: str = "",
    min_chunk_size: int = 0,
    max_chunk_size: int = 0,
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

