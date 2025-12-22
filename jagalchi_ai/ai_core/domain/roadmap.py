from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from jagalchi_ai.ai_core.domain.roadmap_node import RoadmapNode


@dataclass
class Roadmap:
    """학습 로드맵 도메인 모델."""

    roadmap_id: str
    title: str
    description: str
    nodes: List[RoadmapNode]
    edges: List[tuple[str, str]]
    tags: List[str]
    creator_id: str = ""
    updated_at: Optional[datetime] = None
    difficulty: float = 0.5
