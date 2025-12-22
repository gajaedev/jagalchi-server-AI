from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class RoadmapNode:
    """로드맵을 구성하는 개별 노드."""

    node_id: str
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
