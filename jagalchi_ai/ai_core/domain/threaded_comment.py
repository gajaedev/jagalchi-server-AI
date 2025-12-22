from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ThreadedComment:
    """대댓글 트리용 코멘트."""

    comment_id: str
    roadmap_id: str
    node_id: str
    body: str
    path: str
    created_at: datetime
