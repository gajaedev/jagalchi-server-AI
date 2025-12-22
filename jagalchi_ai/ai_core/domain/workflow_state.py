from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class WorkflowState:
    """워크플로우 상태 스냅샷."""

    name: str
    payload: Dict[str, object]
    created_at: str
