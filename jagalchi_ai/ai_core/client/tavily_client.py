from __future__ import annotations

import os
from typing import List, Optional

try:
    from tavily import TavilyClient
except ImportError:  # pragma: no cover - optional dependency
    TavilyClient = None

from jagalchi_ai.ai_core.client.tavily_result import TavilyResult


class TavilySearchClient:
    """Tavily 검색 클라이언트."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        self._api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self._timeout = timeout
        self._client = None
        if self._api_key and TavilyClient is not None:
            self._client = TavilyClient(api_key=self._api_key)

    def available(self) -> bool:
        return self._client is not None

    def search(self, query: str, max_results: int = 5, include_raw_content: bool = False) -> List[TavilyResult]:
        if not self.available():
            return []
        try:
            raw = self._client.search(
                query=query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                include_answer=False,
                include_images=False,
                search_depth="basic",
            )
        except Exception:
            return []
        results = []
        for item in raw.get("results", []) or []:
            title = item.get("title") or ""
            url = item.get("url") or ""
            content = (
                item.get("content")
                or item.get("raw_content")
                or item.get("description")
                or ""
            )
            score = float(item.get("score") or 0.0)
            published_date = item.get("published_date")
            if not url:
                continue
            results.append(
                TavilyResult(
                    title=title,
                    url=url,
                    content=content,
                    score=score,
                    published_date=published_date,
                )
            )
        return results
