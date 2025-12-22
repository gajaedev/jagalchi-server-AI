import unittest

from ai_core.analytics.insights import InsightsService


class InsightsTests(unittest.TestCase):
    def test_knowledge_gap(self) -> None:
        service = InsightsService()
        payload = service.knowledge_gap("user_1", "frontend_dev")
        self.assertIn("gap_set", payload)

    def test_social_proof(self) -> None:
        service = InsightsService()
        payload = service.social_proof()
        self.assertIn("top_nodes", payload)


if __name__ == "__main__":
    unittest.main()
