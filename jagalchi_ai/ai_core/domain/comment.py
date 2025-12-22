from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Comment:
    """로드맵/노드 코멘트."""

    comment_id: str
    roadmap_id: str
    node_id: Optional[str]
    body: str
    reactions_helpful: int = 0
    reactions_negative: int = 0
    resolved: bool = False
    created_at: Optional[datetime] = None
