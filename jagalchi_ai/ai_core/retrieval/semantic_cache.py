from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from jagalchi_ai.ai_core.nlp.text_utils import cheap_embed, cosine_similarity
from jagalchi_ai.ai_core.retrieval.vector_store import InMemoryVectorStore


@dataclass
class CacheEntry:
    entry_id: str
    query: str
    answer: str
    metadata: Dict[str, Any]


class SemanticCache:
    def __init__(self, threshold: float = 0.9) -> None:
        self._store = InMemoryVectorStore()
        self._entries: Dict[str, CacheEntry] = {}
        self._threshold = threshold

    def get(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[CacheEntry]:
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
        metadata = metadata or {}
        entry_id = f"cache:{len(self._entries) + 1}"
        entry = CacheEntry(entry_id=entry_id, query=query, answer=answer, metadata=metadata)
        vector = cheap_embed(query)
        self._entries[entry_id] = entry
        self._store.upsert(entry_id, vector=vector, metadata=metadata)
        return entry
