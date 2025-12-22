from __future__ import annotations

import os
from typing import List, Optional

try:
    from exa_py import Exa
except ImportError:  # pragma: no cover - optional dependency
    Exa = None

from jagalchi_ai.ai_core.client.exa_result import ExaResult


class ExaSearchClient:
    """Exa 검색 클라이언트."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 10,
        include_text: bool = True,
    ) -> None:
        self._api_key = api_key or os.getenv("EXA_API_KEY", "")
        self._timeout = timeout
        self._include_text = include_text
        self._client = None
        if self._api_key and Exa is not None:
            self._client = Exa(self._api_key)

    def available(self) -> bool:
        return self._client is not None

    def search(self, query: str, max_results: int = 5) -> List[ExaResult]:
        if not self.available():
            return []
        try:
            raw = self._client.search(
                query=query,
                num_results=max_results,
                use_autoprompt=True,
                text=self._include_text,
            )
        except Exception:
            return []
        results = []
        for item in getattr(raw, "results", []) or []:
            title = getattr(item, "title", "") or ""
            url = getattr(item, "url", "") or ""
            content = _extract_content(item)
            score = float(getattr(item, "score", 0.0) or 0.0)
            published_date = getattr(item, "published_date", None) or getattr(item, "publishedDate", None)
            if not url:
                continue
            results.append(
                ExaResult(
                    title=title,
                    url=url,
                    content=content,
                    score=score,
                    published_date=published_date,
                )
            )
        return results


def _extract_content(item: object) -> str:
    summary = getattr(item, "summary", None)
    if isinstance(summary, str):
        return summary
    text = getattr(item, "text", None)
    if isinstance(text, str):
        return text
    highlights = getattr(item, "highlights", None)
    if isinstance(highlights, list):
        joined = " ".join(str(value) for value in highlights)
        if joined.strip():
            return joined
    return getattr(item, "snippet", "") or ""
