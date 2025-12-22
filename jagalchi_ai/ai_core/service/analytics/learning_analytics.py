from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.domain.event_log import EventLog
from jagalchi_ai.ai_core.repository.mock_data import EVENT_LOGS
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore


class LearningPatternService:
    """학습 패턴 분석 서비스."""

    def __init__(self, events: Optional[List[EventLog]] = None, snapshot_store: Optional[SnapshotStore] = None) -> None:
        """
        학습 이벤트와 스냅샷 저장소를 초기화합니다.

        @param {Optional[List[EventLog]]} events - 분석 대상 이벤트 로그 목록.
        @param {Optional[SnapshotStore]} snapshot_store - 캐시/스냅샷 저장소.
        @returns {None} 초기화만 수행합니다.
        """
        self._events = events or EVENT_LOGS
        self._snapshot_store = snapshot_store or SnapshotStore()

    def analyze(self, user_id: str, days: int = 30) -> Dict[str, object]:
        """
        사용자의 최근 학습 패턴을 분석하고 스냅샷을 반환합니다.

        @param {str} user_id - 사용자 식별자.
        @param {int} days - 분석 기간(일).
        @returns {Dict[str, object]} 패턴 요약과 추천을 담은 결과.
        """
        cache_key = stable_hash_json({"user_id": user_id, "days": days})
        snapshot = self._snapshot_store.get_or_create(
            cache_key,
            version="pattern_v1",
            builder=lambda: self._build_payload(user_id, days),
        )
        return snapshot.payload

    def _build_payload(self, user_id: str, days: int) -> Dict[str, object]:
        """
        학습 패턴 분석 결과를 구성합니다.

        @param {str} user_id - 사용자 식별자.
        @param {int} days - 분석 기간(일).
        @returns {Dict[str, object]} 패턴/추천이 포함된 페이로드.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        events = [event for event in self._events if event.user_id == user_id and event.created_at >= cutoff]

        active_days = _count_active_days(events)
        completion_velocity = _completion_velocity(events, days)
        avg_gap = _average_gap_days(events)

        recommendations = []
        if completion_velocity < 0.1:
            recommendations.append("주간 목표를 더 작은 작업 단위로 쪼개보세요")
        if avg_gap > 3:
            recommendations.append("학습 세션 간격이 길어요. 리마인드 알림을 설정해보세요")
        if not recommendations:
            recommendations.append("현재 학습 패턴이 안정적입니다. 난이도를 조금 올려보세요")

        return {
            "user_id": user_id,
            "period": f"last_{days}d",
            "patterns": {
                "active_days": active_days,
                "avg_session_gap_days": round(avg_gap, 2),
                "completion_velocity": round(completion_velocity, 3),
            },
            "recommendations": recommendations,
            "model_version": "pattern_v1",
            "generated_at": datetime.utcnow().isoformat(),
        }


def _count_active_days(events: List[EventLog]) -> int:
    """
    활동한 날짜 수를 계산합니다.

    @param {List[EventLog]} events - 이벤트 로그 목록.
    @returns {int} 활동한 날짜 수.
    """
    days = {event.created_at.date() for event in events}
    return len(days)


def _completion_velocity(events: List[EventLog], days: int) -> float:
    """
    완료 이벤트의 속도를 계산합니다.

    @param {List[EventLog]} events - 이벤트 로그 목록.
    @param {int} days - 기간(일).
    @returns {float} 하루당 완료 이벤트 비율.
    """
    completed = sum(1 for event in events if event.event_type in {"record_feedback_view", "rec_click"})
    return completed / max(days, 1)


def _average_gap_days(events: List[EventLog]) -> float:
    """
    학습 세션 간 평균 간격(일)을 계산합니다.

    @param {List[EventLog]} events - 이벤트 로그 목록.
    @returns {float} 평균 간격(일).
    """
    if len(events) < 2:
        return 0.0
    sorted_events = sorted(events, key=lambda e: e.created_at)
    gaps = []
    for prev, curr in zip(sorted_events, sorted_events[1:]):
        gaps.append((curr.created_at - prev.created_at).days)
    return sum(gaps) / max(len(gaps), 1)
