import unittest

from ai_core.insights import InsightsService


class InsightsTests(unittest.TestCase):
    def test_knowledge_gap(self) -> None:
        service = InsightsService()
        payload = service.knowledge_gap("user_1", "frontend_dev")
        self.assertIn("gap_set", payload)


if __name__ == "__main__":
    unittest.main()
