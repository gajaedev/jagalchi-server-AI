from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Feedback:
    """신뢰 점수 계산용 피드백."""

    from_user: str
    to_user: str
    positive: int
    negative: int
