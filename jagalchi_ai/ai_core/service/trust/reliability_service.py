from __future__ import annotations

from datetime import datetime
from math import exp
from typing import Dict, List

from jagalchi_ai.ai_core.domain.feedback import Feedback
from jagalchi_ai.ai_core.repository.mock_data import USER_FEEDBACKS


class ReliabilityService:
    """EigenTrust 기반 신뢰 점수 계산."""

    def __init__(self, feedbacks: List[Dict[str, object]] | None = None) -> None:
        """
        신뢰도 계산에 필요한 피드백 데이터를 초기화합니다.

        @param {List[Dict[str, object]] | None} feedbacks - 피드백 목록.
        @returns {None} 내부 피드백을 설정합니다.
        """
        self._feedbacks = feedbacks or USER_FEEDBACKS

    def compute_user_trust(self, iterations: int = 8, alpha: float = 0.15) -> Dict[str, float]:
        """
        EigenTrust 알고리즘으로 사용자 신뢰 점수를 계산합니다.

        @param {int} iterations - 반복 횟수.
        @param {float} alpha - 텔레포트 계수.
        @returns {Dict[str, float]} 사용자별 신뢰 점수.
        """
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
        """
        작성자 신뢰도와 문서 신선도를 결합해 콘텐츠 점수를 계산합니다.

        @param {float} author_trust - 작성자 신뢰 점수.
        @param {datetime} updated_at - 문서 업데이트 시각.
        @param {float} decay_lambda - 시간 감쇠 계수.
        @returns {float} 콘텐츠 점수.
        """
        days = (datetime.utcnow() - updated_at).days
        freshness = exp(-decay_lambda * days)
        return round(author_trust * 0.7 + freshness * 0.3, 4)

    def generate_snapshot(self) -> Dict[str, object]:
        """
        신뢰 점수 스냅샷을 생성합니다.

        @returns {Dict[str, object]} 신뢰 점수 스냅샷.
        """
        scores = self.compute_user_trust()
        return {
            "user_scores": scores,
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": "eigentrust_v1",
        }


def _build_local_trust(users: List[str], feedbacks: List[Feedback]) -> List[List[float]]:
    """
    사용자 간 로컬 트러스트 행렬을 구성합니다.

    @param {List[str]} users - 사용자 목록.
    @param {List[Feedback]} feedbacks - 피드백 목록.
    @returns {List[List[float]]} 로컬 트러스트 행렬.
    """
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
