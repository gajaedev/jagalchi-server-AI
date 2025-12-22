from __future__ import annotations

from typing import Dict, List

from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed


class GraphSAGE:
    """GraphSAGE 기반 임베딩 추정기."""

    def __init__(self, dim: int = 32) -> None:
        self._dim = dim

    def embed(self, node_text: Dict[str, str], adjacency: Dict[str, List[str]], iterations: int = 2) -> Dict[str, List[float]]:
        embeddings = {node_id: cheap_embed(text, dim=self._dim) for node_id, text in node_text.items()}
        for _ in range(iterations):
            updated = {}
            for node_id, vector in embeddings.items():
                neighbors = adjacency.get(node_id, [])
                if not neighbors:
                    updated[node_id] = vector
                    continue
                agg = [0.0 for _ in range(self._dim)]
                for neighbor in neighbors:
                    neighbor_vec = embeddings.get(neighbor, vector)
                    agg = [a + b for a, b in zip(agg, neighbor_vec)]
                agg = [value / max(len(neighbors), 1) for value in agg]
                updated[node_id] = _normalize([a + b for a, b in zip(vector, agg)])
            embeddings = updated
        return embeddings

    def predict_next(self, node_id: str, embeddings: Dict[str, List[float]], adjacency: Dict[str, List[str]], top_k: int = 3) -> List[str]:
        target = embeddings.get(node_id)
        if not target:
            return []
        candidates = []
        for neighbor in adjacency.get(node_id, []):
            score = _dot(target, embeddings.get(neighbor, target))
            candidates.append((score, neighbor))
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        return [node for _, node in candidates[:top_k]]


def _normalize(vector: List[float]) -> List[float]:
    norm = sum(v * v for v in vector) ** 0.5
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
