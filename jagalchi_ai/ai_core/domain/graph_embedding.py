from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class GraphEmbedding:
    """그래프 임베딩 벡터."""

    node_id: str
    vector: List[float]
