from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional
from urllib import request


@dataclass
class TavilyResult:
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None


class TavilySearchClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: str = "https://api.tavily.com/search",
        timeout: int = 10,
    ) -> None:
        self._api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self._endpoint = endpoint
        self._timeout = timeout

    def available(self) -> bool:
        return bool(self._api_key)

    def search(self, query: str, max_results: int = 5, include_raw_content: bool = False) -> List[TavilyResult]:
        if not self.available():
            return []
        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": max_results,
            "include_raw_content": include_raw_content,
            "include_answer": False,
            "include_images": False,
        }
        raw = self._post_json(payload)
        if not raw:
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

    def _post_json(self, payload: dict) -> Optional[dict]:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
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
