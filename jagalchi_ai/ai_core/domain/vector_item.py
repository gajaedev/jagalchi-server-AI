from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class VectorItem:
    """벡터 스토어 아이템."""

    item_id: str
    vector: List[float]
    metadata: Dict[str, Any]
