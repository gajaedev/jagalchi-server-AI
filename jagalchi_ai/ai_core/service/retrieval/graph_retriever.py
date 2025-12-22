from __future__ import annotations

from typing import Dict, List

from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary
from jagalchi_ai.ai_core.domain.retrieval_item import RetrievalItem


class GraphRetriever:
    """그래프 인접 노드 기반 검색기."""

    def __init__(self, adjacency: Dict[str, List[str]], node_text: Dict[str, str]) -> None:
        self._adjacency = adjacency
        self._node_text = node_text

    def search(self, node_id: str, top_k: int = 5) -> List[RetrievalItem]:
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
