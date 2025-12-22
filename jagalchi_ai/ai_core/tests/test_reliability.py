import unittest
from datetime import datetime, timedelta

from jagalchi_ai.ai_core.common.schema_validation import validate_reliability_output
from jagalchi_ai.ai_core.service.trust.reliability_service import ReliabilityService


class ReliabilityTests(unittest.TestCase):
    def test_eigentrust_scores(self) -> None:
        """
        EigenTrust 점수 합이 정상 범위인지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        service = ReliabilityService()
        scores = service.compute_user_trust()
        self.assertTrue(scores)
        total = round(sum(scores.values()), 2)
        self.assertAlmostEqual(total, 1.0, places=1)

    def test_content_score(self) -> None:
        """
        콘텐츠 신뢰도 점수가 0 이상인지 확인합니다.

        @returns {None} 테스트만 수행합니다.
        """
        service = ReliabilityService()
        score = service.content_score(0.8, datetime.utcnow() - timedelta(days=10))
        self.assertGreater(score, 0)

    def test_reliability_schema(self) -> None:
        """
        신뢰도 스냅샷 스키마를 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        service = ReliabilityService()
        payload = service.generate_snapshot()
        validate_reliability_output(payload)


if __name__ == "__main__":
    unittest.main()
