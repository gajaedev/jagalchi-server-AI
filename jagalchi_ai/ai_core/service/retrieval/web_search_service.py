from __future__ import annotations

import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from jagalchi_ai.ai_core.client import ApifySearchClient
from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore
from jagalchi_ai.ai_core.service.retrieval.search_quality import (
    SearchLang,
    apply_result_quality,
    canonicalize_url,
    get_domain_blacklist,
    normalize_search_lang,
)

logger = logging.getLogger(__name__)


class SearchEngine(str, Enum):
    APIFY = "apify"
    TAVILY = "tavily"  # backward compatibility alias
    EXA = "exa"        # backward compatibility alias
    ALL = "all"


class WebSearchService:
    DEFAULT_TOP_K = 5
    DEFAULT_RECENCY_DAYS = 30
    CACHE_VERSION = "web_search_v6_quality"

    def __init__(
        self,
        apify_client: Optional[ApifySearchClient] = None,
        snapshot_store: Optional[SnapshotStore] = None,
        **_: Any,
    ) -> None:
        # **_ 로 tavily_client/exa_client 같은 기존 인자도 무시하고 호환 유지
        self._apify = apify_client or ApifySearchClient()
        self._snapshot_store = snapshot_store or SnapshotStore()

        if self._apify.available:
            logger.info("웹 검색 서비스 초기화 완료", extra={"engine": "apify", "actor": self._apify.actor})
        else:
            logger.warning("웹 검색 서비스: APIFY_API_TOKEN 미설정")

    @property
    def is_available(self) -> bool:
        if os.getenv("AI_DISABLE_EXTERNAL", "").lower() == "true":
            return False
        return self._apify.available

    @property
    def available_engines(self) -> List[str]:
        return ["apify"] if self._apify.available else []

    def available(self) -> bool:
        return self.is_available

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        engine: SearchEngine = SearchEngine.ALL,
        use_cache: bool = True,
        recency_days: Optional[int] = DEFAULT_RECENCY_DAYS,
        lang: str | SearchLang | None = SearchLang.KO_FIRST,
    ) -> List[Dict[str, Any]]:
        lang_mode = normalize_search_lang(lang)
        engines = self._get_engines_to_use(engine)
        if not engines:
            return []

        cache_key = stable_hash_json({
            "query": query,
            "top_k": top_k,
            "engines": engines,
            "recency_days": recency_days,
            "lang": lang_mode.value,
        })
        if use_cache:
            snapshot = self._snapshot_store.get_or_create(
                cache_key,
                version=self.CACHE_VERSION,
                builder=lambda: self._fetch(query, top_k, engines, recency_days, lang_mode),
                metadata={
                    "query": query,
                    "engines": engines,
                    "recency_days": recency_days,
                    "lang": lang_mode.value,
                },
            )
            return snapshot.payload.get("results", [])

        return self._fetch(query, top_k, engines, recency_days, lang_mode).get("results", [])

    def search_with_metadata(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        engine: SearchEngine = SearchEngine.ALL,
        use_cache: bool = True,
        recency_days: Optional[int] = DEFAULT_RECENCY_DAYS,
        lang: str | SearchLang | None = SearchLang.KO_FIRST,
    ) -> Dict[str, Any]:
        lang_mode = normalize_search_lang(lang)
        engines = self._get_engines_to_use(engine)
        cache_key = stable_hash_json({
            "query": query,
            "top_k": top_k,
            "engines": engines,
            "recency_days": recency_days,
            "lang": lang_mode.value,
            "metadata": True,
        })
        if use_cache:
            snapshot = self._snapshot_store.get_or_create(
                cache_key,
                version=self.CACHE_VERSION,
                builder=lambda: self._fetch(query, top_k, engines, recency_days, lang_mode),
                metadata={
                    "query": query,
                    "engines": engines,
                    "recency_days": recency_days,
                    "lang": lang_mode.value,
                },
            )
            return snapshot.payload
        return self._fetch(query, top_k, engines, recency_days, lang_mode)

    def _get_engines_to_use(self, engine: SearchEngine) -> List[str]:
        if not self.is_available:
            return []
        # tavily/exa 요청도 apify로 라우팅
        if engine in (SearchEngine.APIFY, SearchEngine.TAVILY, SearchEngine.EXA, SearchEngine.ALL):
            return ["apify"]
        return []

    def _fetch(
        self,
        query: str,
        top_k: int,
        engines: List[str],
        recency_days: Optional[int],
        lang: SearchLang,
    ) -> Dict[str, Any]:
        if not engines:
            return {
                "query": query,
                "results": [],
                "generated_at": datetime.utcnow().isoformat(),
                "engines_used": [],
                "error": "no_available_engines",
            }

        results: List[Dict[str, Any]] = []
        if "apify" in engines and self._apify.available:
            max_results = max(top_k * 3, top_k)
            country_code = "kr"
            language_code = "ko"
            if lang == SearchLang.GLOBAL:
                # global은 기존 동작 유지(언어 필터링/가점 미적용)만 보장한다.
                country_code = "kr"
                language_code = "ko"
            for item in self._apify.search(
                query=query,
                max_results=max_results,
                country_code=country_code,
                language_code=language_code,
            ):
                results.append({
                    "title": item.title,
                    "url": item.url,
                    "content": item.content,
                    "score": round(item.score, 4),
                    "fetched_at": item.published_date or datetime.utcnow().date().isoformat(),
                    "source": "apify",
                })

        ranked = apply_result_quality(
            results,
            query=query,
            top_k=top_k,
            lang=lang,
            snippet_fields=("content",),
            domain_blacklist=get_domain_blacklist(),
        )
        return {
            "query": query,
            "results": ranked[:top_k],
            "generated_at": datetime.utcnow().isoformat(),
            "engines_used": ["apify"] if results else [],
            "total_results_before_dedup": len(results),
            "recency_days": recency_days,
            "lang": lang.value,
        }

    def health_check(self) -> Dict[str, Any]:
        return {
            "available": self.is_available,
            "engines": {"apify": self._apify.available},
            "cache_version": self.CACHE_VERSION,
            "actor": self._apify.actor,
            "domain_blacklist": get_domain_blacklist(),
        }


def _dedupe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for item in results:
        url = str(item.get("url") or "").strip()
        canonical = canonicalize_url(url)
        if not canonical:
            continue
        score = float(item.get("score") or 0.0)
        existing = seen.get(canonical)
        if existing is None or score > float(existing.get("score") or 0.0):
            seen[canonical] = item
    merged = list(seen.values())
    merged.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    return merged


def merge_search_results(*result_lists: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
    all_results: List[Dict[str, Any]] = []
    for results in result_lists:
        all_results.extend(results)
    deduped = _dedupe_results(all_results)
    return deduped[:top_k]
