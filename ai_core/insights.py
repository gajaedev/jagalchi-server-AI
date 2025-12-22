from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .clustering import density_cluster
from .mock_data import EVENT_LOGS, ROLE_REQUIREMENTS, USER_MASTERED_SKILLS
from .text_utils import jaccard_similarity
from .types import EventLog


class InsightsService:
    def __init__(self, events: Optional[List[EventLog]] = None) -> None:
        self._events = events or EVENT_LOGS

    def knowledge_gap(self, user_id: str, target_role: str) -> Dict[str, object]:
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
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [event for event in self._events if event.created_at >= cutoff]
        event_counts = Counter(event.event_type for event in recent)
        return {
            "period": f"last_{days}d",
            "event_counts": dict(event_counts),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def social_proof(self, top_k: int = 3) -> Dict[str, object]:
        viewed = Counter(event.node_id for event in self._events if event.node_id)
        top_nodes = [node for node, _ in viewed.most_common(top_k)]
        return {"top_nodes": top_nodes, "generated_at": datetime.utcnow().isoformat()}
