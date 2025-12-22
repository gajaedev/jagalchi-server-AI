from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.clients.exa_client import ExaSearchClient
from jagalchi_ai.ai_core.clients.tavily_client import TavilySearchClient
from jagalchi_ai.ai_core.core.hashing import stable_hash_json
from jagalchi_ai.ai_core.core.snapshot import SnapshotStore


class WebSearchService:
    def __init__(
        self,
        tavily_client: Optional[TavilySearchClient] = None,
        exa_client: Optional[ExaSearchClient] = None,
        snapshot_store: Optional[SnapshotStore] = None,
    ) -> None:
        self._tavily = tavily_client or TavilySearchClient()
        self._exa = exa_client or ExaSearchClient()
        self._snapshot_store = snapshot_store or SnapshotStore()

    def available(self) -> bool:
        return self._tavily.available() or self._exa.available()

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, object]]:
        engines: List[str] = []
        if self._tavily.available():
            engines.append("tavily")
        if self._exa.available():
            engines.append("exa")
        cache_key = stable_hash_json({"query": query, "top_k": top_k, "engines": engines})
        snapshot = self._snapshot_store.get_or_create(
            cache_key,
            version="web_search_v2",
            builder=lambda: self._fetch(query, top_k),
            metadata={"query": query},
        )
        return snapshot.payload.get("results", [])

    def _fetch(self, query: str, top_k: int) -> Dict[str, object]:
        if not self.available():
            return {"query": query, "results": [], "generated_at": datetime.utcnow().isoformat()}
        today = datetime.utcnow().date().isoformat()
        results = []
        if self._tavily.available():
            for result in self._tavily.search(query, max_results=top_k):
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
        if self._exa.available():
            for result in self._exa.search(query, max_results=top_k):
                results.append(
                    {
                        "title": result.title,
                        "url": result.url,
                        "content": result.content,
                        "score": round(result.score, 4),
                        "fetched_at": result.published_date or today,
                        "source": "exa",
                    }
                )
        deduped = _dedupe_results(results)
        return {
            "query": query,
            "results": deduped[:top_k],
            "generated_at": datetime.utcnow().isoformat(),
        }


def _dedupe_results(results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    seen: Dict[str, Dict[str, object]] = {}
    for item in results:
        url = str(item.get("url") or "")
        if not url:
            continue
        score = float(item.get("score") or 0.0)
        existing = seen.get(url)
        if existing is None or score > float(existing.get("score") or 0.0):
            seen[url] = item
    merged = list(seen.values())
    merged.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    return merged
