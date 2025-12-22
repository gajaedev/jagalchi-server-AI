from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DocChange:
    """문서 변경 요약 결과."""

    changed: bool
    change_ratio: float
    summary: str
