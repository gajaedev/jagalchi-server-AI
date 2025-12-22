from __future__ import annotations

from datetime import datetime
from typing import List

from jagalchi_ai.ai_core.domain.workflow_state import WorkflowState
from jagalchi_ai.ai_core.service.coach.in_memory_checkpoint import InMemoryCheckpoint


class SimpleWorkflow:
    """기본 3단계 워크플로우."""

    def __init__(self, checkpoint: InMemoryCheckpoint | None = None) -> None:
        self._checkpoint = checkpoint or InMemoryCheckpoint()

    def run(self, session_id: str, intent: str, tools: List[str]) -> List[str]:
        plan = ["route", "retrieve", "compose"]
        self._checkpoint.save(
            session_id,
            WorkflowState(
                name="route",
                payload={"intent": intent},
                created_at=datetime.utcnow().isoformat(),
            ),
        )
        self._checkpoint.save(
            session_id,
            WorkflowState(
                name="retrieve",
                payload={"tools": tools},
                created_at=datetime.utcnow().isoformat(),
            ),
        )
        self._checkpoint.save(
            session_id,
            WorkflowState(
                name="compose",
                payload={},
                created_at=datetime.utcnow().isoformat(),
            ),
        )
        return plan
