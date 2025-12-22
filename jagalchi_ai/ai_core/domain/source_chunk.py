from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class SourceChunk:
    """기술 카드용 소스 청크."""

    chunk_id: str
    text: str
    metadata: Dict[str, str]
