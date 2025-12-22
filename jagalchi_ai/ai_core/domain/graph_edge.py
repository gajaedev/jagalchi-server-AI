from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GraphEdge:
    """그래프 엣지 정의."""

    source: str
    target: str
    weight: float = 1.0
    edge_type: str = "hard"  # hard | soft | role
