from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RetrievalItem:
    """검색 결과 아이템."""

    source: str
    item_id: str
    score: float
    snippet: str
    metadata: Dict[str, str] = field(default_factory=dict)
