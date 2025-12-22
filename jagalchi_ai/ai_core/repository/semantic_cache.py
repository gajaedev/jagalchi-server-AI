from __future__ import annotations

from typing import Any, Dict, Optional

from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed, cosine_similarity
from jagalchi_ai.ai_core.domain.cache_entry import CacheEntry
from jagalchi_ai.ai_core.repository.in_memory_vector_store import InMemoryVectorStore


class SemanticCache:
    """검색 질의의 유사도를 이용해 답변을 재사용하는 캐시."""

    def __init__(self, threshold: float = 0.9) -> None:
        """
        @param threshold 유사도 임계값.
        @returns None
        """
        self._store = InMemoryVectorStore()
        self._entries: Dict[str, CacheEntry] = {}
        self._threshold = threshold

    def get(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[CacheEntry]:
        """
        @param query 검색 질의.
        @param metadata 메타데이터 필터.
        @returns 유사도가 임계값 이상이면 캐시 엔트리.
        """
        metadata = metadata or {}
        vector = cheap_embed(query)
        items = self._store.query(vector, top_k=1, filters=metadata)
        if not items:
            return None
        item = items[0]
        score = cosine_similarity(vector, item.vector)
        if score < self._threshold:
            return None
        entry_id = item.item_id
        return self._entries.get(entry_id)

    def set(self, query: str, answer: str, metadata: Optional[Dict[str, Any]] = None) -> CacheEntry:
        """
        @param query 검색 질의.
        @param answer 캐시할 답변.
        @param metadata 메타데이터.
        @returns 저장된 캐시 엔트리.
        """
        metadata = metadata or {}
        entry_id = f"cache:{len(self._entries) + 1}"
        entry = CacheEntry(entry_id=entry_id, query=query, answer=answer, metadata=metadata)
        vector = cheap_embed(query)
        self._entries[entry_id] = entry
        self._store.upsert(entry_id, vector=vector, metadata=metadata)
        return entry
