from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.core.hashing import stable_hash_json
from jagalchi_ai.ai_core.retrieval.retrieval import BM25Index, Document, HybridRetriever, VectorRetriever
from jagalchi_ai.ai_core.core.snapshot import SnapshotStore
from jagalchi_ai.ai_core.nlp.text_utils import cheap_embed, extractive_summary
from jagalchi_ai.ai_core.retrieval.vector_store import InMemoryVectorStore
from jagalchi_ai.ai_core.core.mock_data import TECH_SOURCES


class ResourceRecommendationService:
    def __init__(self, snapshot_store: Optional[SnapshotStore] = None) -> None:
        self._snapshot_store = snapshot_store or SnapshotStore()
        self._retriever = self._build_retriever()

    def recommend(self, query: str, top_k: int = 5) -> Dict[str, object]:
        cache_key = stable_hash_json({"query": query, "top_k": top_k})
        snapshot = self._snapshot_store.get_or_create(
            cache_key,
            version="resource_rec_v1",
            builder=lambda: self._build_payload(query, top_k),
        )
        return snapshot.payload

    def _build_payload(self, query: str, top_k: int) -> Dict[str, object]:
        results = self._retriever.search(query, top_k=top_k)
        items = [
            {
                "title": item.metadata.get("title", ""),
                "url": item.metadata.get("url", ""),
                "source": item.source,
                "score": round(item.score, 4),
            }
            for item in results
        ]
        return {
            "query": query,
            "generated_at": datetime.utcnow().isoformat(),
            "items": items,
            "model_version": "retriever_v1",
            "retrieval_evidence": [
                {"source": item.source, "id": item.item_id, "snippet": item.snippet} for item in results
            ],
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
