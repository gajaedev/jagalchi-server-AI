from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary
from jagalchi_ai.ai_core.domain.document import Document
from jagalchi_ai.ai_core.repository.mock_data import TECH_SOURCES
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore
from jagalchi_ai.ai_core.service.retrieval.bm25_index import BM25Index
from jagalchi_ai.ai_core.service.retrieval.hybrid_retriever import HybridRetriever
from jagalchi_ai.ai_core.service.retrieval.web_search_service import WebSearchService
from langchain_community.embeddings.fake import FakeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LangchainDocument


class ResourceRecommendationService:
    """자료 추천 검색 서비스."""

    DEFAULT_RECENCY_DAYS = WebSearchService.DEFAULT_RECENCY_DAYS
    """최신 자료 우선 검색 기본 기간(일)."""

    def __init__(
        self,
        snapshot_store: Optional[SnapshotStore] = None,
        web_search: Optional[WebSearchService] = None,
    ) -> None:
        """
        @param snapshot_store 스냅샷 캐시 저장소.
        @param web_search 외부 검색 서비스.
        @returns None
        """
        self._snapshot_store = snapshot_store or SnapshotStore()
        self._retriever = self._build_retriever()
        self._web_search = web_search or WebSearchService(snapshot_store=self._snapshot_store)

    def recommend(
        self,
        query: str,
        top_k: int = 5,
        recency_days: Optional[int] = DEFAULT_RECENCY_DAYS,
    ) -> Dict[str, object]:
        """
        @param query 검색 질의.
        @param top_k 추천 개수.
        @param recency_days 최신 자료 필터 기간(일).
        @returns 자료 추천 결과 JSON.
        """
        cache_key = stable_hash_json(
            {
                "query": query,
                "top_k": top_k,
                "web": self._web_search.available(),
                "recency_days": recency_days,
            }
        )
        snapshot = self._snapshot_store.get_or_create(
            cache_key,
            version="resource_rec_v3",
            builder=lambda: self._build_payload(query, top_k, recency_days),
        )
        return snapshot.payload

    def _build_payload(
        self,
        query: str,
        top_k: int,
        recency_days: Optional[int],
    ) -> Dict[str, object]:
        """
        @param query 검색 질의.
        @param top_k 추천 개수.
        @param recency_days 최신 자료 필터 기간(일).
        @returns 추천 결과 페이로드.
        """
        local_results = self._retriever.search(query, top_k=top_k)
        local_items = [
            {
                "title": item.metadata.get("title", ""),
                "url": item.metadata.get("url", ""),
                "source": item.source,
                "score": round(item.score, 4),
            }
            for item in local_results
        ]
        web_results = (
            self._web_search.search(query, top_k=top_k, recency_days=recency_days)
            if self._web_search.available()
            else []
        )
        web_items = [
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "source": result.get("source", "web"),
                "score": round(float(result.get("score") or 0.5), 4),
            }
            for result in web_results
        ]
        items = _merge_items(web_items, local_items, top_k=top_k)
        web_evidence = [
            {
                "source": result.get("source", "web"),
                "id": result.get("url", ""),
                "snippet": result.get("content", ""),
            }
            for result in web_results
        ]
        local_evidence = [
            {"source": item.source, "id": item.item_id, "snippet": item.snippet} for item in local_results
        ]
        return {
            "query": query,
            "generated_at": datetime.utcnow().isoformat(),
            "items": items,
            "model_version": "retriever_v2",
            "retrieval_evidence": local_evidence + web_evidence,
        }

    def _build_retriever(self) -> HybridRetriever:
        """
        @returns 로컬 문서 기반 하이브리드 리트리버.
        """
        bm25 = BM25Index()
        documents: List[Document] = []
        for tech_slug, sources in TECH_SOURCES.items():
            for idx, source in enumerate(sources):
                doc_id = f"resource:{tech_slug}:{idx}"
                text = source["content"]
                documents.append(
                    Document(
                        doc_id=doc_id,
                        text=text,
                        metadata={
                            "source": "resource",
                            "title": source["title"],
                            "url": source["url"],
                            "snippet": extractive_summary(text),
                        },
                    )
                )

        bm25.add_documents(documents)
        langchain_docs = [
            LangchainDocument(
                page_content=doc.text,
                metadata={**doc.metadata, "doc_id": doc.doc_id, "snippet": extractive_summary(doc.text)},
            )
            for doc in documents
        ]
        embeddings = FakeEmbeddings(size=32)
        vector_store = FAISS.from_documents(langchain_docs, embeddings)
        vector_retriever = vector_store.as_retriever(search_kwargs={"k": 5})

        retrievers = []
        if bm25.retriever:
            retrievers.append(("bm25", bm25.retriever))
        retrievers.append(("vector", vector_retriever))

        return HybridRetriever(
            retrievers=retrievers,
            weights={"bm25": 1.0, "vector": 0.6},
        )


def _merge_items(web_items: List[Dict[str, object]], local_items: List[Dict[str, object]], top_k: int) -> List[Dict[str, object]]:
    """
    @param web_items 웹 검색 결과 리스트.
    @param local_items 로컬 검색 결과 리스트.
    @param top_k 반환할 최대 개수.
    @returns 병합된 추천 아이템 리스트.
    """
    normalized_web = _normalize_items(web_items)
    normalized_local = _normalize_items(local_items)
    for item in normalized_web:
        item["score"] = round(min(1.0, float(item["score"]) * 1.05), 4)
    merged = sorted(normalized_web + normalized_local, key=lambda item: item["score"], reverse=True)
    return merged[:top_k]


def _normalize_items(items: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """
    @param items 점수 포함 아이템 리스트.
    @returns 최대 점수 기준 정규화된 리스트.
    """
    if not items:
        return []
    max_score = max(float(item.get("score") or 0.0) for item in items) or 1.0
    normalized = []
    for item in items:
        score = float(item.get("score") or 0.0)
        normalized.append({**item, "score": round(score / max_score, 4)})
    return normalized
