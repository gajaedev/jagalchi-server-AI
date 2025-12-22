from __future__ import annotations

from typing import Dict, List

from jagalchi_ai.ai_core.domain.workflow_state import WorkflowState


class InMemoryCheckpoint:
    """워크플로우 상태를 메모리에 저장."""

    def __init__(self) -> None:
        self._states: Dict[str, List[WorkflowState]] = {}

    def save(self, session_id: str, state: WorkflowState) -> None:
        self._states.setdefault(session_id, []).append(state)

    def history(self, session_id: str) -> List[WorkflowState]:
        return self._states.get(session_id, [])
