import unittest

from jagalchi_ai.ai_core.recommendation.related_roadmaps import RelatedRoadmapsService


class RankingTests(unittest.TestCase):
    def test_ranking_stability(self) -> None:
        service = RelatedRoadmapsService()
        result = service.generate_snapshot("rm_frontend")
        candidates = result["candidates"]
        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["related_roadmap_id"], "rm_react")


if __name__ == "__main__":
    unittest.main()
