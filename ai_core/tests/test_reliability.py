import unittest
from datetime import datetime, timedelta

from ai_core.trust.reliability import ReliabilityService
from ai_core.core.schema_validation import validate_reliability_output


class ReliabilityTests(unittest.TestCase):
    def test_eigentrust_scores(self) -> None:
        service = ReliabilityService()
        scores = service.compute_user_trust()
        self.assertTrue(scores)
        total = round(sum(scores.values()), 2)
        self.assertAlmostEqual(total, 1.0, places=1)

    def test_content_score(self) -> None:
        service = ReliabilityService()
        score = service.content_score(0.8, datetime.utcnow() - timedelta(days=10))
        self.assertGreater(score, 0)

    def test_reliability_schema(self) -> None:
        service = ReliabilityService()
        payload = service.generate_snapshot()
        validate_reliability_output(payload)


if __name__ == "__main__":
    unittest.main()
