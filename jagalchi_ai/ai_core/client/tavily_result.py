from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TavilyResult:
    """Tavily 검색 결과."""

    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None
