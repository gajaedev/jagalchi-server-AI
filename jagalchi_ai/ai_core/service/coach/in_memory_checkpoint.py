from __future__ import annotations

from typing import Dict, List

from jagalchi_ai.ai_core.domain.workflow_state import WorkflowState


class InMemoryCheckpoint:
    """워크플로우 상태를 메모리에 저장."""

    def __init__(self) -> None:
        """
        메모리 기반 체크포인트 저장소를 초기화합니다.

        @returns {None} 상태 저장 딕셔너리를 준비합니다.
        """
        self._states: Dict[str, List[WorkflowState]] = {}

    def save(self, session_id: str, state: WorkflowState) -> None:
        """
        세션별 워크플로우 상태를 저장합니다.

        @param {str} session_id - 세션 식별자.
        @param {WorkflowState} state - 저장할 상태.
        @returns {None} 상태를 누적 저장합니다.
        """
        self._states.setdefault(session_id, []).append(state)

    def history(self, session_id: str) -> List[WorkflowState]:
        """
        세션의 상태 히스토리를 반환합니다.

        @param {str} session_id - 세션 식별자.
        @returns {List[WorkflowState]} 상태 히스토리 목록.
        """
        return self._states.get(session_id, [])
