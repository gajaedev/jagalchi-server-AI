from __future__ import annotations

from typing import Dict, List

from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed


class GraphSAGE:
    """GraphSAGE 기반 임베딩 추정기."""

    def __init__(self, dim: int = 32) -> None:
        """
        임베딩 차원을 설정합니다.

        @param {int} dim - 임베딩 차원.
        @returns {None} 설정값을 저장합니다.
        """
        self._dim = dim

    def embed(self, node_text: Dict[str, str], adjacency: Dict[str, List[str]], iterations: int = 2) -> Dict[str, List[float]]:
        """
        노드 텍스트와 그래프 구조를 기반으로 임베딩을 계산합니다.

        @param {Dict[str, str]} node_text - 노드별 텍스트.
        @param {Dict[str, List[str]]} adjacency - 인접 리스트.
        @param {int} iterations - 메시지 패싱 반복 횟수.
        @returns {Dict[str, List[float]]} 노드별 임베딩.
        """
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
        """
        특정 노드에서 다음으로 이동할 후보 노드를 추천합니다.

        @param {str} node_id - 기준 노드 ID.
        @param {Dict[str, List[float]]} embeddings - 노드 임베딩.
        @param {Dict[str, List[str]]} adjacency - 인접 리스트.
        @param {int} top_k - 반환할 상위 후보 수.
        @returns {List[str]} 추천 노드 ID 목록.
        """
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
    """
    벡터를 L2 정규화합니다.

    @param {List[float]} vector - 입력 벡터.
    @returns {List[float]} 정규화된 벡터.
    """
    norm = sum(v * v for v in vector) ** 0.5
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def _dot(a: List[float], b: List[float]) -> float:
    """
    두 벡터의 내적을 계산합니다.

    @param {List[float]} a - 벡터 A.
    @param {List[float]} b - 벡터 B.
    @returns {float} 내적 결과.
    """
    return sum(x * y for x, y in zip(a, b))
