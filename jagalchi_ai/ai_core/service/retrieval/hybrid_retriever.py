from __future__ import annotations

from typing import Dict, List, Optional

from jagalchi_ai.ai_core.domain.retrieval_item import RetrievalItem


class HybridRetriever:
    """BM25/Vector 등을 합산하는 하이브리드 검색기."""

    def __init__(self, retrievers: List[tuple[str, callable]], weights: Optional[Dict[str, float]] = None) -> None:
        self._retrievers = retrievers
        self._weights = weights or {}

    def search(self, query: str, top_k: int = 5) -> List[RetrievalItem]:
        combined: Dict[str, RetrievalItem] = {}
        for name, retriever in self._retrievers:
            weight = self._weights.get(name, 1.0)
            items = retriever(query, top_k)
            for item in items:
                existing = combined.get(item.item_id)
                scored = item.score * weight
                if existing:
                    existing.score += scored
                else:
                    combined[item.item_id] = RetrievalItem(
                        source=item.source,
                        item_id=item.item_id,
                        score=scored,
                        snippet=item.snippet,
                        metadata=item.metadata,
                    )
        ranked = sorted(combined.values(), key=lambda item: item.score, reverse=True)
        return ranked[:top_k]
