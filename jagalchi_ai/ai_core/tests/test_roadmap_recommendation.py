import unittest

from jagalchi_ai.ai_core.domain.graph_edge import GraphEdge
from jagalchi_ai.ai_core.repository.mock_data import ROADMAPS
from jagalchi_ai.ai_core.service.graph.graph_ontology import GraphOntology
from jagalchi_ai.ai_core.service.graph.roadmap_recommendation_service import RoadmapRecommendationService


class RoadmapRecommendationTests(unittest.TestCase):
    def test_recommendation_generates_nodes(self) -> None:
        service = RoadmapRecommendationService(ROADMAPS)
        payload = service.recommend("frontend_dev", "user_1")
        self.assertTrue(payload["nodes"])
        self.assertEqual(payload["target_role"], "frontend_dev")
        self.assertIn("gnn_predictions", payload)

    def test_cycle_detection(self) -> None:
        ontology = GraphOntology()
        ontology.add_node("a", "skill")
        ontology.add_node("b", "skill")
        ontology.add_edge(GraphEdge(source="a", target="b"))
        with self.assertRaises(ValueError):
            ontology.add_edge(GraphEdge(source="b", target="a"))


if __name__ == "__main__":
    unittest.main()
