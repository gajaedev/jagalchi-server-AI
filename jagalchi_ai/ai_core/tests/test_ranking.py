import unittest

from jagalchi_ai.ai_core.service.recommendation.related_roadmaps import RelatedRoadmapsService


class RankingTests(unittest.TestCase):
    def test_ranking_stability(self) -> None:
        """
        로드맵 추천 랭킹의 일관성을 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        service = RelatedRoadmapsService()
        result = service.generate_snapshot("rm_frontend")
        candidates = result["candidates"]
        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["related_roadmap_id"], "rm_react")


if __name__ == "__main__":
    unittest.main()
