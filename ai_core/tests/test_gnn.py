import unittest

from ai_core.gnn import GraphSAGE


class GnnTests(unittest.TestCase):
    def test_predict_next(self) -> None:
        model = GraphSAGE()
        node_text = {"a": "react", "b": "hooks", "c": "redux"}
        adjacency = {"a": ["b", "c"], "b": ["c"]}
        embeddings = model.embed(node_text, adjacency)
        predictions = model.predict_next("a", embeddings, adjacency, top_k=1)
        self.assertTrue(predictions)


if __name__ == "__main__":
    unittest.main()
