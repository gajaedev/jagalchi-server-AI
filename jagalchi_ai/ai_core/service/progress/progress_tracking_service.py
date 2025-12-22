from __future__ import annotations

from datetime import datetime
from math import exp
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.domain.learning_state import LearningState
from jagalchi_ai.ai_core.domain.roadmap import Roadmap


class ProgressTrackingService:
    """학습 진행 상태를 관리하는 서비스."""

    def __init__(self) -> None:
        """
        사용자별 학습 상태 저장소를 초기화합니다.

        @returns {None} 상태 맵을 준비합니다.
        """
        self._state: Dict[str, Dict[str, LearningState]] = {}

    def initialize(self, user_id: str, roadmap: Roadmap) -> None:
        """
        사용자 학습 상태를 로드맵 기준으로 초기화합니다.

        @param {str} user_id - 사용자 ID.
        @param {Roadmap} roadmap - 로드맵 데이터.
        @returns {None} 상태를 생성합니다.
        """
        state_map: Dict[str, LearningState] = {}
        prereq_map = _build_prereq_map(roadmap.edges)
        for node in roadmap.nodes:
            status = "AVAILABLE" if not prereq_map.get(node.node_id) else "LOCKED"
            state_map[node.node_id] = LearningState(
                status=status,
                proficiency=0.0,
                last_reviewed=None,
                decay_factor=0.08,
            )
        self._state[user_id] = state_map

    def complete_node(self, user_id: str, node_id: str, quiz_score: float) -> None:
        """
        노드를 완료 상태로 업데이트합니다.

        @param {str} user_id - 사용자 ID.
        @param {str} node_id - 노드 ID.
        @param {float} quiz_score - 퀴즈 점수.
        @returns {None} 상태를 갱신합니다.
        """
        state = self._state[user_id][node_id]
        state.status = "COMPLETED"
        state.proficiency = min(1.0, max(0.0, quiz_score / 100))
        state.last_reviewed = datetime.utcnow()

    def unlock_children(self, user_id: str, roadmap: Roadmap, completed_node_id: str) -> List[str]:
        """
        완료된 노드를 기준으로 다음 노드를 해제합니다.

        @param {str} user_id - 사용자 ID.
        @param {Roadmap} roadmap - 로드맵 데이터.
        @param {str} completed_node_id - 완료된 노드 ID.
        @returns {List[str]} 해제된 노드 ID 목록.
        """
        unlocked: List[str] = []
        prereq_map = _build_prereq_map(roadmap.edges)
        children = [target for source, target in roadmap.edges if source == completed_node_id]
        for child in children:
            prereqs = prereq_map.get(child, [])
            if all(self._state[user_id][pr].status == "COMPLETED" for pr in prereqs):
                child_state = self._state[user_id][child]
                if child_state.status == "LOCKED":
                    child_state.status = "AVAILABLE"
                    unlocked.append(child)
        return unlocked

    def apply_spaced_repetition(self, user_id: str, now: Optional[datetime] = None) -> List[str]:
        """
        간격 반복 로직을 적용해 복습 필요 노드를 계산합니다.

        @param {str} user_id - 사용자 ID.
        @param {Optional[datetime]} now - 기준 시간 (없으면 현재).
        @returns {List[str]} 복습 필요 노드 ID 목록.
        """
        now = now or datetime.utcnow()
        needs_review = []
        for node_id, state in self._state.get(user_id, {}).items():
            if not state.last_reviewed:
                continue
            days = (now - state.last_reviewed).days
            if days <= 0:
                continue
            decayed = state.proficiency * exp(-state.decay_factor * days)
            state.proficiency = max(0.0, decayed)
            if state.proficiency < 0.4 and state.status == "COMPLETED":
                state.status = "NEEDS_REVIEW"
                needs_review.append(node_id)
        return needs_review

    def summary(self, user_id: str) -> Dict[str, int]:
        """
        사용자 상태 요약을 반환합니다.

        @param {str} user_id - 사용자 ID.
        @returns {Dict[str, int]} 상태별 카운트.
        """
        summary = {"LOCKED": 0, "AVAILABLE": 0, "IN_PROGRESS": 0, "COMPLETED": 0, "NEEDS_REVIEW": 0}
        for state in self._state.get(user_id, {}).values():
            summary[state.status] = summary.get(state.status, 0) + 1
        return summary

    def get_state(self, user_id: str, node_id: str) -> LearningState:
        """
        특정 노드의 학습 상태를 반환합니다.

        @param {str} user_id - 사용자 ID.
        @param {str} node_id - 노드 ID.
        @returns {LearningState} 학습 상태 객체.
        """
        return self._state[user_id][node_id]


def _build_prereq_map(edges: List[tuple[str, str]]) -> Dict[str, List[str]]:
    """
    엣지 목록에서 선수 학습 맵을 구성합니다.

    @param {List[tuple[str, str]]} edges - (source, target) 엣지 목록.
    @returns {Dict[str, List[str]]} 노드별 선수 조건 목록.
    """
    prereq_map: Dict[str, List[str]] = {}
    for source, target in edges:
        prereq_map.setdefault(target, []).append(source)
    return prereq_map
