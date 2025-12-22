import unittest

from jagalchi_ai.ai_core.service.analytics.insights import InsightsService


class InsightsTests(unittest.TestCase):
    def test_knowledge_gap(self) -> None:
        """
        지식 격차 분석 결과에 필드가 포함되는지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        service = InsightsService()
        payload = service.knowledge_gap("user_1", "frontend_dev")
        self.assertIn("gap_set", payload)

    def test_social_proof(self) -> None:
        """
        사회적 증거 분석 결과를 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        service = InsightsService()
        payload = service.social_proof()
        self.assertIn("top_nodes", payload)


if __name__ == "__main__":
    unittest.main()
