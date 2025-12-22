from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.clients.tavily_client import TavilySearchClient
from jagalchi_ai.ai_core.core.hashing import stable_hash_json
from jagalchi_ai.ai_core.core.snapshot import SnapshotStore


class WebSearchService:
    def __init__(
        self,
        client: Optional[TavilySearchClient] = None,
        snapshot_store: Optional[SnapshotStore] = None,
    ) -> None:
        self._client = client or TavilySearchClient()
        self._snapshot_store = snapshot_store or SnapshotStore()

    def available(self) -> bool:
        return self._client.available()

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, object]]:
        cache_key = stable_hash_json(
            {"query": query, "top_k": top_k, "engine": "tavily" if self.available() else "offline"}
        )
        snapshot = self._snapshot_store.get_or_create(
            cache_key,
            version="tavily_search_v1",
            builder=lambda: self._fetch(query, top_k),
            metadata={"query": query},
        )
        return snapshot.payload.get("results", [])

    def _fetch(self, query: str, top_k: int) -> Dict[str, object]:
        if not self.available():
            return {"query": query, "results": [], "generated_at": datetime.utcnow().isoformat()}
        today = datetime.utcnow().date().isoformat()
        results = []
        for result in self._client.search(query, max_results=top_k):
            results.append(
                {
                    "title": result.title,
                    "url": result.url,
                    "content": result.content,
                    "score": round(result.score, 4),
                    "fetched_at": result.published_date or today,
                    "source": "tavily",
                }
            )
        return {"query": query, "results": results, "generated_at": datetime.utcnow().isoformat()}
