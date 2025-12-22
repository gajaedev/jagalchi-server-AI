from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class GeminiResponse:
    """Gemini 응답 래퍼."""

    data: Optional[Dict[str, Any]]
    raw_text: str
