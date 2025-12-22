from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp
from typing import Dict, List

from ai_core.core.mock_data import USER_FEEDBACKS


@dataclass
class Feedback:
    from_user: str
    to_user: str
    positive: int
    negative: int


class ReliabilityService:
    def __init__(self, feedbacks: List[Dict[str, object]] | None = None) -> None:
        self._feedbacks = feedbacks or USER_FEEDBACKS

    def compute_user_trust(self, iterations: int = 8, alpha: float = 0.15) -> Dict[str, float]:
        feedbacks = [Feedback(**item) for item in self._feedbacks]
        users = sorted({f.from_user for f in feedbacks} | {f.to_user for f in feedbacks})
        if not users:
            return {}

        matrix = _build_local_trust(users, feedbacks)
        trust = {user: 1.0 / len(users) for user in users}

        for _ in range(iterations):
            next_trust = {user: alpha / len(users) for user in users}
            for i, src in enumerate(users):
                for j, dst in enumerate(users):
                    next_trust[dst] += (1 - alpha) * matrix[i][j] * trust[src]
            trust = next_trust
        return trust

    def content_score(self, author_trust: float, updated_at: datetime, decay_lambda: float = 0.01) -> float:
        days = (datetime.utcnow() - updated_at).days
        freshness = exp(-decay_lambda * days)
        return round(author_trust * 0.7 + freshness * 0.3, 4)

    def generate_snapshot(self) -> Dict[str, object]:
        scores = self.compute_user_trust()
        return {
            "user_scores": scores,
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": "eigentrust_v1",
        }


def _build_local_trust(users: List[str], feedbacks: List[Feedback]) -> List[List[float]]:
    index = {user: idx for idx, user in enumerate(users)}
    matrix = [[0.0 for _ in users] for _ in users]
    row_sums = [0.0 for _ in users]

    for feedback in feedbacks:
        score = max(feedback.positive - feedback.negative, 0)
        if score <= 0:
            continue
        i = index[feedback.from_user]
        j = index[feedback.to_user]
        matrix[i][j] += score
        row_sums[i] += score

    for i in range(len(users)):
        if row_sums[i] == 0:
            matrix[i][i] = 1.0
            continue
        for j in range(len(users)):
            matrix[i][j] = matrix[i][j] / row_sums[i]
    return matrix
