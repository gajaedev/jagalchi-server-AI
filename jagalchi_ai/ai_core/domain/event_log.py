from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EventLog:
    """추천/학습 이벤트 로그."""

    event_type: str
    user_id: str
    roadmap_id: str
    node_id: Optional[str]
    created_at: datetime
