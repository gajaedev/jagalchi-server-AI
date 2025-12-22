from __future__ import annotations

import json
import os
from typing import List, Optional
from urllib import request


from jagalchi_ai.ai_core.client.exa_result import ExaResult


class ExaSearchClient:
    """Exa 검색 클라이언트."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: str = "https://api.exa.ai/search",
        timeout: int = 10,
        include_text: bool = True,
    ) -> None:
        self._api_key = api_key or os.getenv("EXA_API_KEY", "")
        self._endpoint = endpoint
        self._timeout = timeout
        self._include_text = include_text

    def available(self) -> bool:
        return bool(self._api_key)

    def search(self, query: str, max_results: int = 5) -> List[ExaResult]:
        if not self.available():
            return []
        payload = {"query": query, "numResults": max_results}
        if self._include_text:
            payload["contents"] = {"text": True, "summary": True, "highlights": True}
        raw = self._post_json(payload)
        if not raw:
            return []
        results = []
        for item in raw.get("results", []) or []:
            title = item.get("title") or ""
            url = item.get("url") or ""
            content = _extract_content(item)
            score = float(item.get("score") or 0.0)
            published_date = item.get("publishedDate") or item.get("published_date")
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

    def _post_json(self, payload: dict) -> Optional[dict]:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._endpoint,
            data=data,
            headers={"Content-Type": "application/json", "x-api-key": self._api_key},
        )
        try:
            with request.urlopen(req, timeout=self._timeout) as response:
                raw = response.read().decode("utf-8")
        except Exception:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None


def _extract_content(item: dict) -> str:
    if isinstance(item.get("summary"), str):
        return item["summary"]
    if isinstance(item.get("text"), str):
        return item["text"]
    highlights = item.get("highlights")
    if isinstance(highlights, list):
        joined = " ".join(str(value) for value in highlights)
        if joined.strip():
            return joined
    return item.get("snippet") or ""
