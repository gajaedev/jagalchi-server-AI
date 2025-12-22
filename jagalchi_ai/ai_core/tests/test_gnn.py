import unittest

from jagalchi_ai.ai_core.service.graph.graph_sage import GraphSAGE


class GnnTests(unittest.TestCase):
    def test_predict_next(self) -> None:
        """
        그래프 임베딩 기반 추천이 동작하는지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        model = GraphSAGE()
        node_text = {"a": "react", "b": "hooks", "c": "redux"}
        adjacency = {"a": ["b", "c"], "b": ["c"]}
        embeddings = model.embed(node_text, adjacency)
        predictions = model.predict_next("a", embeddings, adjacency, top_k=1)
        self.assertTrue(predictions)


if __name__ == "__main__":
    unittest.main()
