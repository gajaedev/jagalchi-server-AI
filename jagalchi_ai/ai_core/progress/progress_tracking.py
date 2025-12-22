from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.core.types import Roadmap


@dataclass
class LearningState:
    status: str
    proficiency: float
    last_reviewed: Optional[datetime]
    decay_factor: float


class ProgressTrackingService:
    def __init__(self) -> None:
        self._state: Dict[str, Dict[str, LearningState]] = {}

    def initialize(self, user_id: str, roadmap: Roadmap) -> None:
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
        state = self._state[user_id][node_id]
        state.status = "COMPLETED"
        state.proficiency = min(1.0, max(0.0, quiz_score / 100))
        state.last_reviewed = datetime.utcnow()

    def unlock_children(self, user_id: str, roadmap: Roadmap, completed_node_id: str) -> List[str]:
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
        summary = {"LOCKED": 0, "AVAILABLE": 0, "IN_PROGRESS": 0, "COMPLETED": 0, "NEEDS_REVIEW": 0}
        for state in self._state.get(user_id, {}).values():
            summary[state.status] = summary.get(state.status, 0) + 1
        return summary

    def get_state(self, user_id: str, node_id: str) -> LearningState:
        return self._state[user_id][node_id]


def _build_prereq_map(edges: List[tuple[str, str]]) -> Dict[str, List[str]]:
    prereq_map: Dict[str, List[str]] = {}
    for source, target in edges:
        prereq_map.setdefault(target, []).append(source)
    return prereq_map
