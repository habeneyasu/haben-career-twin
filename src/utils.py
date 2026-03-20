"""
Shared utility functions for environment variable parsing.
"""
import os
from typing import Optional


def safe_int_env(name: str, default: int, minimum: Optional[int] = None) -> int:
    """
    Safely parse integer environment variable with optional minimum.
    """
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    return value


def safe_float_env(name: str, default: float) -> float:
    """
    Safely parse float environment variable.
    """
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default
