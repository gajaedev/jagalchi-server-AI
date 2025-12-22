from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.core.hashing import stable_hash_json
from jagalchi_ai.ai_core.retrieval.retrieval import BM25Index, Document, HybridRetriever, VectorRetriever
from jagalchi_ai.ai_core.core.snapshot import SnapshotStore
from jagalchi_ai.ai_core.retrieval.web_search import WebSearchService
from jagalchi_ai.ai_core.nlp.text_utils import cheap_embed, extractive_summary
from jagalchi_ai.ai_core.retrieval.vector_store import InMemoryVectorStore
from jagalchi_ai.ai_core.core.mock_data import TECH_SOURCES


class ResourceRecommendationService:
    def __init__(
        self,
        snapshot_store: Optional[SnapshotStore] = None,
        web_search: Optional[WebSearchService] = None,
    ) -> None:
        self._snapshot_store = snapshot_store or SnapshotStore()
        self._retriever = self._build_retriever()
        self._web_search = web_search or WebSearchService(snapshot_store=self._snapshot_store)

    def recommend(self, query: str, top_k: int = 5) -> Dict[str, object]:
        cache_key = stable_hash_json(
            {"query": query, "top_k": top_k, "web": self._web_search.available()}
        )
        snapshot = self._snapshot_store.get_or_create(
            cache_key,
            version="resource_rec_v2",
            builder=lambda: self._build_payload(query, top_k),
        )
        return snapshot.payload

    def _build_payload(self, query: str, top_k: int) -> Dict[str, object]:
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
        web_results = self._web_search.search(query, top_k=top_k) if self._web_search.available() else []
        web_items = [
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "source": "tavily",
                "score": round(float(result.get("score") or 0.5), 4),
            }
            for result in web_results
        ]
        items = _merge_items(web_items, local_items, top_k=top_k)
        web_evidence = [
            {"source": "tavily", "id": result.get("url", ""), "snippet": result.get("content", "")}
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
        bm25 = BM25Index()
        vector_store = InMemoryVectorStore()
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
                vector_store.upsert(
                    doc_id,
                    vector=cheap_embed(text),
                    metadata={
                        "source": "resource",
                        "title": source["title"],
                        "url": source["url"],
                        "snippet": extractive_summary(text),
                    },
                )

        bm25.add_documents(documents)
        vector_retriever = VectorRetriever(vector_store)
        return HybridRetriever(
            retrievers=[("bm25", bm25.search), ("vector", vector_retriever.search)],
            weights={"bm25": 1.0, "vector": 0.6},
        )


def _merge_items(web_items: List[Dict[str, object]], local_items: List[Dict[str, object]], top_k: int) -> List[Dict[str, object]]:
    normalized_web = _normalize_items(web_items)
    normalized_local = _normalize_items(local_items)
    for item in normalized_web:
        item["score"] = round(min(1.0, float(item["score"]) * 1.05), 4)
    merged = sorted(normalized_web + normalized_local, key=lambda item: item["score"], reverse=True)
    return merged[:top_k]


def _normalize_items(items: List[Dict[str, object]]) -> List[Dict[str, object]]:
    if not items:
        return []
    max_score = max(float(item.get("score") or 0.0) for item in items) or 1.0
    normalized = []
    for item in items:
        score = float(item.get("score") or 0.0)
        normalized.append({**item, "score": round(score / max_score, 4)})
    return normalized
