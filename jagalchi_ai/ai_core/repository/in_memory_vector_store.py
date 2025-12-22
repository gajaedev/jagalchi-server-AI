from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_community.embeddings.fake import FakeEmbeddings
from langchain_community.vectorstores import FAISS

from jagalchi_ai.ai_core.domain.vector_item import VectorItem
from jagalchi_ai.ai_core.repository.vector_store import VectorStore


class InMemoryVectorStore(VectorStore):
    """메모리 기반 벡터 스토어."""

    def __init__(self, embedding_dim: int = 32) -> None:
        self._items: Dict[str, VectorItem] = {}
        self._store: Optional[FAISS] = None
        # 외부 임베딩 대신 경량 임베딩 인터페이스를 사용한다.
        self._embeddings = FakeEmbeddings(size=embedding_dim)

    def upsert(self, item_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        payload = {**metadata, "item_id": item_id}
        self._items[item_id] = VectorItem(item_id=item_id, vector=vector, metadata=payload)
        self._add_embeddings([(item_id, vector, payload)])

    def batch_upsert(self, items: List[VectorItem]) -> None:
        prepared = []
        for item in items:
            payload = {**item.metadata, "item_id": item.item_id}
            self._items[item.item_id] = VectorItem(item_id=item.item_id, vector=item.vector, metadata=payload)
            prepared.append((item.item_id, item.vector, payload))
        if prepared:
            self._add_embeddings(prepared)

    def query(self, vector: List[float], top_k: int, filters: Optional[Dict[str, Any]] = None) -> List[VectorItem]:
        if not self._store:
            return []
        hits = self._store.similarity_search_with_score_by_vector(vector, k=top_k, filter=filters)
        results: List[VectorItem] = []
        for doc, _score in hits:
            item_id = doc.metadata.get("item_id")
            if not item_id:
                continue
            stored = self._items.get(item_id)
            if stored:
                results.append(stored)
        return results

    def _add_embeddings(self, items: List[tuple[str, List[float], Dict[str, Any]]]) -> None:
        text_embeddings = []
        metadatas = []
        ids = []
        for item_id, vector, metadata in items:
            text = str(metadata.get("text") or metadata.get("snippet") or "")
            text_embeddings.append((text, vector))
            metadatas.append(metadata)
            ids.append(item_id)

        if self._store is None:
            self._store = FAISS.from_embeddings(
                text_embeddings=text_embeddings,
                embedding=self._embeddings,
                metadatas=metadatas,
                ids=ids,
            )
        else:
            self._store.add_embeddings(text_embeddings=text_embeddings, metadatas=metadatas, ids=ids)
