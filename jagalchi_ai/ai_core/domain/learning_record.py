from __future__ import annotations

from dataclasses import dataclass
from typing import List

from jagalchi_ai.ai_core.domain.link_meta import LinkMeta


@dataclass
class LearningRecord:
    """사용자 학습 기록."""

    record_id: str
    memo: str
    links: List[LinkMeta]
    node_id: str
    roadmap_id: str
