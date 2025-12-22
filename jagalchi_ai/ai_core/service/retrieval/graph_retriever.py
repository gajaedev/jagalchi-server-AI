from __future__ import annotations

from typing import Dict, List

from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary
from jagalchi_ai.ai_core.domain.retrieval_item import RetrievalItem


class GraphRetriever:
    """그래프 인접 노드 기반 검색기."""

    def __init__(self, adjacency: Dict[str, List[str]], node_text: Dict[str, str]) -> None:
        """
        @param adjacency 그래프 인접 리스트.
        @param node_text 노드 ID별 텍스트 맵.
        @returns None
        """
        self._adjacency = adjacency
        self._node_text = node_text

    def search(self, node_id: str, top_k: int = 5) -> List[RetrievalItem]:
        """
        @param node_id 기준 노드 ID.
        @param top_k 상위 결과 수.
        @returns 인접 노드 기반 검색 결과 리스트.
        """
        related = self._adjacency.get(node_id, [])[:top_k]
        results = []
        for related_id in related:
            text = self._node_text.get(related_id, "")
            results.append(
                RetrievalItem(
                    source="graph",
                    item_id=related_id,
                    score=1.0,
                    snippet=extractive_summary(text),
                    metadata={"source": "graph"},
                )
            )
        return results
