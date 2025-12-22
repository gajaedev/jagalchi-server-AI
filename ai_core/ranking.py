from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RankingFeature:
    tag_overlap: int
    creator_trust_score: float
    completion_rate: float
    freshness: float
    popularity: float
    difficulty_match: float


DEFAULT_WEIGHTS = {
    "tag_overlap": 0.2,
    "creator_trust_score": 0.2,
    "completion_rate": 0.2,
    "freshness": 0.15,
    "popularity": 0.15,
    "difficulty_match": 0.1,
}


def score_candidate(features: RankingFeature, weights: Dict[str, float] | None = None) -> float:
    weights = weights or DEFAULT_WEIGHTS
    return (
        features.tag_overlap * weights["tag_overlap"]
        + features.creator_trust_score * weights["creator_trust_score"]
        + features.completion_rate * weights["completion_rate"]
        + features.freshness * weights["freshness"]
        + features.popularity * weights["popularity"]
        + features.difficulty_match * weights["difficulty_match"]
    )


def normalize_ranked(candidates: List[dict]) -> List[dict]:
    if not candidates:
        return []
    max_score = max(candidate["score"] for candidate in candidates) or 1.0
    for candidate in candidates:
        candidate["score"] = round(candidate["score"] / max_score, 4)
    return candidates
