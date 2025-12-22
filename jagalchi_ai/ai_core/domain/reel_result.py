from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ReelResult:
    """REEL 파이프라인 결과."""

    metadata: Dict[str, Optional[str]]
    evidence: List[Dict[str, str]]
