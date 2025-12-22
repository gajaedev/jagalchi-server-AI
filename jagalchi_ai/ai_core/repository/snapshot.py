from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class Snapshot:
    """스냅샷 저장용 도메인 객체."""

    key: str
    payload: Dict[str, Any]
    version: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
