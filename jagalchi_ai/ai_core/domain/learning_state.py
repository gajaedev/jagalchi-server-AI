from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LearningState:
    """노드별 학습 상태."""

    status: str
    proficiency: float
    last_reviewed: Optional[datetime]
    decay_factor: float
