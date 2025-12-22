from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class GraphNode:
    """그래프 RAG 노드."""

    node_id: str
    text: str
    roadmap_id: str
    tags: List[str]
