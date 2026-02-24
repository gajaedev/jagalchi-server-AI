from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ApifyResult:
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None


class ApifySearchClient:
    """Apify Actor 기반 웹 검색 클라이언트.

    기본 Actor: apify/google-search-scraper
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        actor: Optional[str] = None,
        timeout_seconds: int = 60,
    ) -> None:
        self._api_token = api_token or os.getenv("APIFY_API_TOKEN", "")
        self._actor = actor or os.getenv("APIFY_SEARCH_ACTOR", "apify/google-search-scraper")
        self._timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return bool(self._api_token)

    @property
    def actor(self) -> str:
        return self._actor

    def search(
        self,
        query: str,
        max_results: int = 5,
        country_code: str = "kr",
        language_code: str = "ko",
    ) -> List[ApifyResult]:
        if not self.available:
            return []

        actor_path = self._actor.replace("/", "~")
        url = f"https://api.apify.com/v2/acts/{actor_path}/run-sync-get-dataset-items"
        params = {
            "token": self._api_token,
            "format": "json",
            "clean": "true",
        }
        payload: Dict[str, Any] = {
            "queries": query,
            "resultsPerPage": max_results,
            "maxPagesPerQuery": 1,
            "countryCode": (country_code or "kr").lower(),
            "languageCode": (language_code or "ko").lower(),
            "mobileResults": False,
            "includeUnfilteredResults": False,
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(url, params=params, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            logger.error("Apify 검색 실패", extra={"error": str(e), "query": query[:50]}, exc_info=True)
            return []

        if not isinstance(data, list):
            return []

        now = datetime.utcnow().date().isoformat()
        results: List[ApifyResult] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            organic_results = item.get("organicResults") or []
            if isinstance(organic_results, list) and organic_results:
                for organic in organic_results:
                    if not isinstance(organic, dict):
                        continue
                    url_val = str(organic.get("url") or "")
                    if not url_val:
                        continue
                    title = str(organic.get("title") or url_val)
                    description = str(organic.get("description") or "")
                    rank = organic.get("position") or 999
                    score = 1.0 / max(float(rank), 1.0)
                    results.append(
                        ApifyResult(
                            title=title,
                            url=url_val,
                            content=description,
                            score=round(score, 4),
                            published_date=now,
                        )
                    )
                continue

            # fallback: 평면 구조 결과 대응
            title = str(item.get("title") or "")
            url_val = str(item.get("url") or "")
            if not url_val:
                continue
            description = str(item.get("description") or item.get("snippet") or "")
            rank = item.get("position") or 999
            score = 1.0 / max(float(rank), 1.0)
            results.append(
                ApifyResult(
                    title=title or url_val,
                    url=url_val,
                    content=description,
                    score=round(score, 4),
                    published_date=now,
                )
            )

        return results[:max_results]
