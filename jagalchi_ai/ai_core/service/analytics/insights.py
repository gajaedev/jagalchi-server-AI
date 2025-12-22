from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.common.nlp.clustering import density_cluster
from jagalchi_ai.ai_core.domain.event_log import EventLog
from jagalchi_ai.ai_core.repository.mock_data import EVENT_LOGS, ROLE_REQUIREMENTS, USER_MASTERED_SKILLS


class InsightsService:
    """학습 인사이트 요약 서비스."""

    def __init__(self, events: Optional[List[EventLog]] = None) -> None:
        """
        인사이트 분석에 사용할 이벤트 로그를 초기화합니다.

        @param {Optional[List[EventLog]]} events - 분석 대상 이벤트 로그 목록.
        @returns {None} 초기화만 수행합니다.
        """
        self._events = events or EVENT_LOGS

    def knowledge_gap(self, user_id: str, target_role: str) -> Dict[str, object]:
        """
        목표 직군 대비 부족한 기술을 계산합니다.

        @param {str} user_id - 사용자 식별자.
        @param {str} target_role - 목표 직군 키.
        @returns {Dict[str, object]} 부족 기술과 생성 시각을 담은 페이로드.
        """
        required = set(ROLE_REQUIREMENTS.get(target_role, []))
        mastered = set(USER_MASTERED_SKILLS.get(user_id, set()))
        gap = sorted(required - mastered)
        return {
            "user_id": user_id,
            "target_role": target_role,
            "gap_set": gap,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def user_segmentation(self, threshold: float = 0.5) -> Dict[str, object]:
        """
        숙련 기술 프로필을 기반으로 사용자 클러스터를 생성합니다.

        @param {float} threshold - 밀도 기반 클러스터링 임계값.
        @returns {Dict[str, object]} 군집별 대표 기술 요약.
        """
        users = list(USER_MASTERED_SKILLS.keys())
        profiles = [" ".join(sorted(USER_MASTERED_SKILLS[user])) for user in users]
        clusters = density_cluster(profiles, threshold=threshold)
        cluster_payload = []
        for cluster in clusters:
            skills = Counter()
            cluster_users = []
            for profile in cluster:
                for user in users:
                    if profile == " ".join(sorted(USER_MASTERED_SKILLS[user])):
                        cluster_users.append(user)
                        skills.update(USER_MASTERED_SKILLS.get(user, set()))
            top_skills = [skill for skill, _ in skills.most_common(3)]
            cluster_payload.append({"users": cluster_users, "top_skills": top_skills})

        return {"clusters": cluster_payload, "generated_at": datetime.utcnow().isoformat()}

    def learning_trends(self, days: int = 14) -> Dict[str, object]:
        """
        최근 학습 이벤트 트렌드를 집계합니다.

        @param {int} days - 집계할 기간(일).
        @returns {Dict[str, object]} 이벤트 타입별 카운트 요약.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [event for event in self._events if event.created_at >= cutoff]
        event_counts = Counter(event.event_type for event in recent)
        return {
            "period": f"last_{days}d",
            "event_counts": dict(event_counts),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def social_proof(self, top_k: int = 3) -> Dict[str, object]:
        """
        인기 있는 노드를 기반으로 사회적 증거를 계산합니다.

        @param {int} top_k - 상위 노드 개수.
        @returns {Dict[str, object]} 상위 노드 목록.
        """
        viewed = Counter(event.node_id for event in self._events if event.node_id)
        top_nodes = [node for node, _ in viewed.most_common(top_k)]
        return {"top_nodes": top_nodes, "generated_at": datetime.utcnow().isoformat()}
