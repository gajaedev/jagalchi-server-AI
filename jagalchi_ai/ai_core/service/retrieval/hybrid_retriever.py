from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from langchain.retrievers import EnsembleRetriever

from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary
from jagalchi_ai.ai_core.domain.retrieval_item import RetrievalItem


class _RetrieverProtocol(Protocol):
    def get_relevant_documents(self, query: str):  # pragma: no cover - langchain interface
        """
        LangChain 리트리버 인터페이스를 만족하는 검색 메서드입니다.

        @param {str} query - 검색 질의.
        @returns {list} LangChain 문서 리스트.
        """
        ...


class HybridRetriever:
    """LangChain 기반 하이브리드 검색기."""

    def __init__(self, retrievers: List[tuple[str, _RetrieverProtocol]], weights: Optional[Dict[str, float]] = None) -> None:
        """
        @param retrievers (이름, retriever) 튜플 리스트.
        @param weights retriever 가중치 맵.
        @returns None
        """
        self._retrievers = retrievers
        self._weights = weights or {}

    def search(self, query: str, top_k: int = 5) -> List[RetrievalItem]:
        """
        @param query 검색 질의.
        @param top_k 상위 결과 수.
        @returns 하이브리드 검색 결과 리스트.
        """
        retriever_list = []
        weights: List[float] = []
        for name, retriever in self._retrievers:
            _apply_top_k(retriever, top_k)
            retriever_list.append(retriever)
            weights.append(self._weights.get(name, 1.0))
        if not retriever_list:
            return []
        ensemble = EnsembleRetriever(retrievers=retriever_list, weights=weights)
        docs = ensemble.invoke(query)
        results = []
        for idx, doc in enumerate(docs):
            metadata = doc.metadata or {}
            item_id = metadata.get("doc_id") or metadata.get("item_id") or f"hybrid_{idx}"
            results.append(
                RetrievalItem(
                    source=metadata.get("source", "hybrid"),
                    item_id=item_id,
                    score=1.0 / (idx + 1),
                    snippet=metadata.get("snippet", extractive_summary(doc.page_content)),
                    metadata=metadata,
                )
            )
        return results


def _apply_top_k(retriever: object, top_k: int) -> None:
    """
    @param retriever LangChain 리트리버 인스턴스.
    @param top_k 상위 결과 수.
    @returns None
    """
    if hasattr(retriever, "k"):
        setattr(retriever, "k", top_k)
    elif hasattr(retriever, "search_kwargs"):
        kwargs = getattr(retriever, "search_kwargs", {}) or {}
        kwargs["k"] = top_k
        setattr(retriever, "search_kwargs", kwargs)
