from __future__ import annotations

from typing import List

from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed
from jagalchi_ai.ai_core.domain.retrieval_item import RetrievalItem
from jagalchi_ai.ai_core.repository.vector_store import VectorStore


class VectorRetriever:
    """벡터 유사도 기반 검색기."""

    def __init__(self, store: VectorStore, namespace: str = "") -> None:
        self._store = store
        self._namespace = namespace

    def search(self, query: str, top_k: int = 5) -> List[RetrievalItem]:
        vector = cheap_embed(query)
        filters = {"namespace": self._namespace} if self._namespace else None
        items = self._store.query(vector, top_k=top_k, filters=filters)
        results = []
        for item in items:
            results.append(
                RetrievalItem(
                    source=item.metadata.get("source", "vector"),
                    item_id=item.item_id,
                    score=1.0,
                    snippet=item.metadata.get("snippet", ""),
                    metadata=item.metadata,
                )
            )
        return results
