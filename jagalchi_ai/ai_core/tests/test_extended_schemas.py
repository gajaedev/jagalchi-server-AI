import unittest

from jagalchi_ai.ai_core.analytics.learning_analytics import LearningPatternService
from jagalchi_ai.ai_core.recommendation.resource_recommender import ResourceRecommendationService
from jagalchi_ai.ai_core.graph.roadmap_generator import RoadmapGeneratorService
from jagalchi_ai.ai_core.core.schema_validation import (
    validate_learning_pattern_output,
    validate_resource_recommendation_output,
    validate_roadmap_generation_output,
)


class ExtendedSchemaTests(unittest.TestCase):
    def test_roadmap_generation_schema(self) -> None:
        service = RoadmapGeneratorService()
        payload = service.generate("React 학습", preferred_tags=["react"], compose_level="quick")
        validate_roadmap_generation_output(payload)

    def test_resource_recommendation_schema(self) -> None:
        service = ResourceRecommendationService()
        payload = service.recommend("React hooks", top_k=2)
        validate_resource_recommendation_output(payload)

    def test_learning_pattern_schema(self) -> None:
        service = LearningPatternService()
        payload = service.analyze("user_1", days=14)
        validate_learning_pattern_output(payload)


if __name__ == "__main__":
    unittest.main()
