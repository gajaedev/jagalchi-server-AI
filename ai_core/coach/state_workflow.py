from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class WorkflowState:
    name: str
    payload: Dict[str, object]
    created_at: str


class InMemoryCheckpoint:
    def __init__(self) -> None:
        self._states: Dict[str, List[WorkflowState]] = {}

    def save(self, session_id: str, state: WorkflowState) -> None:
        self._states.setdefault(session_id, []).append(state)

    def history(self, session_id: str) -> List[WorkflowState]:
        return self._states.get(session_id, [])


class SimpleWorkflow:
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
