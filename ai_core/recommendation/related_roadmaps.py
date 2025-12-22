from __future__ import annotations

from datetime import datetime
from math import log
from typing import Dict, List, Optional

from ai_core.core.mock_data import CO_COMPLETE, CO_FOLLOW, CREATOR_TRUST, POPULARITY, ROADMAPS, SIMILAR_USER
from ai_core.recommendation.ranking import RankingFeature, normalize_ranked, score_candidate
from ai_core.core.types import Roadmap


class RelatedRoadmapsService:
    def __init__(self, roadmaps: Optional[Dict[str, Roadmap]] = None) -> None:
        self._roadmaps = roadmaps or ROADMAPS

    def generate_snapshot(self, roadmap_id: str) -> Dict[str, object]:
        roadmap = self._roadmaps[roadmap_id]
        candidates = self._generate_candidates(roadmap)
        ranked = self._rank_candidates(roadmap, candidates)

        payload = {
            "roadmap_id": roadmap_id,
            "generated_at": datetime.utcnow().isoformat(),
            "candidates": ranked,
            "model_version": "ranker_v1",
            "evidence_snapshot": {
                "tracks": ["co_follow", "co_complete", "content", "social"],
                "candidate_count": len(ranked),
            },
        }
        return payload

    def _generate_candidates(self, roadmap: Roadmap) -> Dict[str, Dict[str, object]]:
        candidates: Dict[str, Dict[str, object]] = {}
        source_id = roadmap.roadmap_id

        for related_id, value in CO_FOLLOW.get(source_id, {}).items():
            candidates.setdefault(related_id, {"reasons": []})["reasons"].append(
                {"type": "co_follow", "value": value}
            )

        for related_id, value in CO_COMPLETE.get(source_id, {}).items():
            candidates.setdefault(related_id, {"reasons": []})["reasons"].append(
                {"type": "co_complete", "value": value}
            )

        for related_id, value in SIMILAR_USER.get(source_id, {}).items():
            candidates.setdefault(related_id, {"reasons": []})["reasons"].append(
                {"type": "social", "value": value}
            )

        for related_id, related in self._roadmaps.items():
            if related_id == source_id:
                continue
            overlap = len(set(roadmap.tags) & set(related.tags))
            if overlap > 0:
                candidates.setdefault(related_id, {"reasons": []})["reasons"].append(
                    {"type": "tag_overlap", "value": overlap}
                )

        return candidates

    def _rank_candidates(self, roadmap: Roadmap, candidates: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
        ranked: List[Dict[str, object]] = []
        for related_id, payload in candidates.items():
            related = self._roadmaps.get(related_id)
            if not related:
                continue
            overlap = len(set(roadmap.tags) & set(related.tags))
            features = RankingFeature(
                tag_overlap=overlap,
                creator_trust_score=CREATOR_TRUST.get(related.creator_id, 0.5),
                completion_rate=CO_COMPLETE.get(roadmap.roadmap_id, {}).get(related_id, 0.0),
                freshness=_freshness_score(related.updated_at),
                popularity=_popularity_score(POPULARITY.get(related_id, 0)),
                difficulty_match=1 - abs(roadmap.difficulty - related.difficulty),
            )
            score = score_candidate(features)
            ranked.append(
                {
                    "related_roadmap_id": related_id,
                    "score": score,
                    "reasons": payload["reasons"],
                }
            )

        ranked.sort(key=lambda item: (-item["score"], item["related_roadmap_id"]))
        return normalize_ranked(ranked)


def _freshness_score(updated_at) -> float:
    if not updated_at:
        return 0.5
    delta = (datetime.utcnow() - updated_at).days
    return 1 / (1 + delta)


def _popularity_score(raw: int) -> float:
    if raw <= 0:
        return 0.0
    return log(raw + 1) / 10
