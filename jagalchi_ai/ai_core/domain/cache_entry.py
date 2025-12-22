from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class CacheEntry:
    """시맨틱 캐시 엔트리."""

    entry_id: str
    query: str
    answer: str
    metadata: Dict[str, Any]
