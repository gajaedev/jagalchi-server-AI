from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class LinkMeta:
    """학습 기록 링크 메타 정보."""

    url: str
    title: str = ""
    is_public: bool = False
    status_code: Optional[int] = None
