# =============================================================================
# 웹 검색 서비스
# =============================================================================
# 외부 검색 API(Tavily, Exa)를 활용한 웹 검색 서비스입니다.
# 검색 결과를 스냅샷으로 캐시하여 중복 요청을 방지합니다.
#
# 주요 기능:
#   - Tavily/Exa 멀티 엔진 검색
#   - 검색 결과 스냅샷 캐싱
#   - 결과 중복 제거 및 점수 정렬
#   - RAG 파이프라인 통합 지원
#
# 아키텍처:
#   WebSearchService
#   ├── TavilySearchClient (웹 검색)
#   ├── ExaSearchClient (시맨틱 검색)
#   └── SnapshotStore (캐시)
#
# 사용 예시:
#   service = WebSearchService()
#   results = service.search("Python 학습 자료", top_k=5)
#   for result in results:
#       print(result["title"], result["score"])
# =============================================================================

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from jagalchi_ai.ai_core.client import ExaSearchClient, TavilySearchClient
from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore

# =============================================================================
# 로거 설정
# =============================================================================
logger = logging.getLogger(__name__)


# =============================================================================
# 열거형 정의
# =============================================================================

class SearchEngine(str, Enum):
    """
    검색 엔진 열거형.

    지원하는 검색 엔진 목록입니다.
    """

    TAVILY = "tavily"
    """Tavily 웹 검색 엔진."""

    EXA = "exa"
    """Exa 시맨틱 검색 엔진."""

    ALL = "all"
    """모든 사용 가능한 엔진."""


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class SearchResult:
    """
    웹 검색 결과 데이터 클래스.

    통합된 검색 결과 형식을 정의합니다.

    Attributes:
        title (str): 결과 제목.
        url (str): 결과 URL.
        content (str): 결과 내용/요약.
        score (float): 관련성 점수 (0.0 ~ 1.0).
        source (str): 검색 엔진 소스.
        fetched_at (str): 검색 수행 일시.
        metadata (Dict[str, Any]): 추가 메타데이터.
    """

    title: str
    url: str
    content: str
    score: float
    source: str
    fetched_at: str
    metadata: Dict[str, Any] = None

    def __post_init__(self) -> None:
        """초기화 후 메타데이터 기본값 설정."""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """
        결과를 딕셔너리로 변환합니다.

        Returns:
            Dict[str, Any]: 검색 결과 딕셔너리.
        """
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": round(self.score, 4),
            "source": self.source,
            "fetched_at": self.fetched_at,
            **self.metadata,
        }


# =============================================================================
# 웹 검색 서비스 클래스
# =============================================================================

class WebSearchService:
    """
    웹 검색 서비스 클래스.

    Tavily와 Exa 검색 엔진을 활용하여 웹 검색을 수행하고,
    결과를 스냅샷으로 캐시합니다.

    Attributes:
        is_available (bool): 서비스 사용 가능 여부.

    Example:
        >>> # 기본 사용
        >>> service = WebSearchService()
        >>> results = service.search("Python 웹 프레임워크", top_k=10)

        >>> # 특정 엔진만 사용
        >>> results = service.search("검색어", engine=SearchEngine.TAVILY)

        >>> # 컨텍스트 생성 (RAG용)
        >>> context = service.get_search_context("머신러닝 입문")
    """

    # -------------------------------------------------------------------------
    # 클래스 상수
    # -------------------------------------------------------------------------

    DEFAULT_TOP_K = 5
    """기본 검색 결과 수."""

    CACHE_VERSION = "web_search_v3"
    """캐시 버전 (변경 시 기존 캐시 무효화)."""

    # -------------------------------------------------------------------------
    # 초기화
    # -------------------------------------------------------------------------

    def __init__(
        self,
        tavily_client: Optional[TavilySearchClient] = None,
        exa_client: Optional[ExaSearchClient] = None,
        snapshot_store: Optional[SnapshotStore] = None,
    ) -> None:
        """
        WebSearchService 인스턴스를 초기화합니다.

        Args:
            tavily_client:
                Tavily 검색 클라이언트. None이면 새로 생성.
            exa_client:
                Exa 검색 클라이언트. None이면 새로 생성.
            snapshot_store:
                스냅샷 저장소. None이면 새로 생성.

        Example:
            >>> # 기본 설정
            >>> service = WebSearchService()

            >>> # 커스텀 클라이언트 사용
            >>> tavily = TavilySearchClient(api_key="your-key")
            >>> service = WebSearchService(tavily_client=tavily)
        """
        # 검색 클라이언트 초기화
        self._tavily = tavily_client or TavilySearchClient()
        self._exa = exa_client or ExaSearchClient()

        # 스냅샷 저장소 초기화
        self._snapshot_store = snapshot_store or SnapshotStore()

        # 초기화 로깅
        engines = []
        if self._tavily.available:
            engines.append("Tavily")
        if self._exa.available():
            engines.append("Exa")

        if engines:
            logger.info(
                "웹 검색 서비스 초기화 완료",
                extra={"available_engines": engines},
            )
        else:
            logger.warning("웹 검색 서비스: 사용 가능한 검색 엔진이 없습니다")

    # -------------------------------------------------------------------------
    # 프로퍼티
    # -------------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """
        서비스 사용 가능 여부를 확인합니다.

        환경변수로 비활성화되었거나 사용 가능한 검색 엔진이 없으면 False.

        Returns:
            bool: 서비스 사용 가능 여부.
        """
        # 환경변수로 비활성화 확인
        if os.getenv("AI_DISABLE_EXTERNAL", "").lower() == "true":
            return False

        return self._tavily.available or self._exa.available()

    @property
    def available_engines(self) -> List[str]:
        """
        사용 가능한 검색 엔진 목록을 반환합니다.

        Returns:
            List[str]: 사용 가능한 엔진 이름 리스트.
        """
        engines = []
        if self._tavily.available:
            engines.append("tavily")
        if self._exa.available():
            engines.append("exa")
        return engines

    # -------------------------------------------------------------------------
    # 호환성 메서드 (레거시)
    # -------------------------------------------------------------------------

    def available(self) -> bool:
        """
        서비스 사용 가능 여부 (레거시 메서드).

        Note:
            is_available 프로퍼티 사용을 권장합니다.

        Returns:
            bool: 사용 가능 여부.
        """
        return self.is_available

    # -------------------------------------------------------------------------
    # 검색 메서드
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        engine: SearchEngine = SearchEngine.ALL,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        웹 검색을 수행하고 결과를 반환합니다.

        검색 결과는 스냅샷으로 캐시되어 동일한 쿼리에 대해
        빠른 응답을 제공합니다.

        Args:
            query:
                검색 쿼리.
            top_k:
                반환할 최대 결과 수 (기본: 5).
            engine:
                사용할 검색 엔진 (기본: 모두 사용).
            use_cache:
                캐시 사용 여부 (기본: True).

        Returns:
            List[Dict[str, Any]]: 검색 결과 리스트.
                각 결과는 title, url, content, score, source, fetched_at 필드를 포함.

        Example:
            >>> results = service.search("Python 학습", top_k=10)
            >>> for result in results:
            ...     print(f"[{result['score']:.2f}] {result['title']}")
        """
        # 사용 가능한 엔진 확인
        engines = self._get_engines_to_use(engine)

        if not engines:
            logger.warning("사용 가능한 검색 엔진이 없습니다")
            return []

        # 캐시 키 생성
        cache_key = stable_hash_json({
            "query": query,
            "top_k": top_k,
            "engines": engines,
        })

        # 캐시 사용 시 스냅샷 조회
        if use_cache:
            snapshot = self._snapshot_store.get_or_create(
                cache_key,
                version=self.CACHE_VERSION,
                builder=lambda: self._fetch(query, top_k, engines),
                metadata={"query": query, "engines": engines},
            )
            return snapshot.payload.get("results", [])
        else:
            # 캐시 미사용 시 직접 검색
            payload = self._fetch(query, top_k, engines)
            return payload.get("results", [])

    def search_with_metadata(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> Dict[str, Any]:
        """
        검색 결과와 메타데이터를 함께 반환합니다.

        Args:
            query: 검색 쿼리.
            top_k: 최대 결과 수.

        Returns:
            Dict[str, Any]: 결과와 메타데이터를 포함한 딕셔너리.
                - query: 검색 쿼리
                - results: 검색 결과 리스트
                - generated_at: 생성 시각
                - engines_used: 사용된 검색 엔진
        """
        engines = self._get_engines_to_use(SearchEngine.ALL)
        return self._fetch(query, top_k, engines)

    def get_search_context(
        self,
        query: str,
        top_k: int = 5,
        max_chars: int = 8000,
    ) -> str:
        """
        RAG 파이프라인용 검색 컨텍스트를 생성합니다.

        검색 결과를 LLM이 사용하기 좋은 형식으로 포맷팅합니다.

        Args:
            query: 검색 쿼리.
            top_k: 포함할 최대 결과 수.
            max_chars: 최대 문자 수.

        Returns:
            str: RAG용 포맷팅된 컨텍스트.

        Example:
            >>> context = service.get_search_context("Python 비동기")
            >>> prompt = f"참고 자료:\\n{context}\\n\\n질문: ..."
        """
        results = self.search(query, top_k=top_k)

        if not results:
            return ""

        context_parts = []
        total_chars = 0

        for idx, result in enumerate(results, 1):
            # 각 결과를 포맷팅
            part = self._format_result_for_context(result, idx)

            # 최대 길이 확인
            if total_chars + len(part) > max_chars:
                break

            context_parts.append(part)
            total_chars += len(part)

        return "\n\n".join(context_parts)

    # -------------------------------------------------------------------------
    # 내부 메서드
    # -------------------------------------------------------------------------

    def _get_engines_to_use(self, engine: SearchEngine) -> List[str]:
        """
        사용할 검색 엔진 목록을 결정합니다.

        Args:
            engine: 요청된 검색 엔진.

        Returns:
            List[str]: 실제로 사용할 엔진 목록.
        """
        if not self.is_available:
            return []

        if engine == SearchEngine.TAVILY:
            return ["tavily"] if self._tavily.available else []
        elif engine == SearchEngine.EXA:
            return ["exa"] if self._exa.available() else []
        else:  # ALL
            return self.available_engines

    def _fetch(
        self,
        query: str,
        top_k: int,
        engines: List[str],
    ) -> Dict[str, Any]:
        """
        실제 검색을 수행하고 결과를 반환합니다.

        Args:
            query: 검색 쿼리.
            top_k: 최대 결과 수.
            engines: 사용할 엔진 목록.

        Returns:
            Dict[str, Any]: 검색 결과 페이로드.
        """
        if not engines:
            return self._create_empty_response(query)

        today = datetime.utcnow().date().isoformat()
        results: List[Dict[str, Any]] = []

        # Tavily 검색
        if "tavily" in engines and self._tavily.available:
            tavily_results = self._search_with_tavily(query, top_k, today)
            results.extend(tavily_results)
            logger.debug(
                "Tavily 검색 완료",
                extra={"query": query[:30], "count": len(tavily_results)},
            )

        # Exa 검색
        if "exa" in engines and self._exa.available():
            exa_results = self._search_with_exa(query, top_k, today)
            results.extend(exa_results)
            logger.debug(
                "Exa 검색 완료",
                extra={"query": query[:30], "count": len(exa_results)},
            )

        # 중복 제거 및 정렬
        deduped = _dedupe_results(results)

        return {
            "query": query,
            "results": deduped[:top_k],
            "generated_at": datetime.utcnow().isoformat(),
            "engines_used": engines,
            "total_results_before_dedup": len(results),
        }

    def _search_with_tavily(
        self,
        query: str,
        top_k: int,
        today: str,
    ) -> List[Dict[str, Any]]:
        """
        Tavily 검색을 수행합니다.

        Args:
            query: 검색 쿼리.
            top_k: 최대 결과 수.
            today: 오늘 날짜 문자열.

        Returns:
            List[Dict[str, Any]]: Tavily 검색 결과.
        """
        results = []
        try:
            for result in self._tavily.search(query, max_results=top_k):
                results.append({
                    "title": result.title,
                    "url": result.url,
                    "content": result.content,
                    "score": round(result.score, 4),
                    "fetched_at": result.published_date or today,
                    "source": "tavily",
                })
        except Exception as e:
            logger.error(
                "Tavily 검색 실패",
                extra={"query": query[:30], "error": str(e)},
                exc_info=True,
            )
        return results

    def _search_with_exa(
        self,
        query: str,
        top_k: int,
        today: str,
    ) -> List[Dict[str, Any]]:
        """
        Exa 검색을 수행합니다.

        Args:
            query: 검색 쿼리.
            top_k: 최대 결과 수.
            today: 오늘 날짜 문자열.

        Returns:
            List[Dict[str, Any]]: Exa 검색 결과.
        """
        results = []
        try:
            for result in self._exa.search(query, max_results=top_k):
                results.append({
                    "title": result.title,
                    "url": result.url,
                    "content": result.content,
                    "score": round(result.score, 4),
                    "fetched_at": result.published_date or today,
                    "source": "exa",
                })
        except Exception as e:
            logger.error(
                "Exa 검색 실패",
                extra={"query": query[:30], "error": str(e)},
                exc_info=True,
            )
        return results

    def _create_empty_response(self, query: str) -> Dict[str, Any]:
        """
        빈 응답을 생성합니다.

        Args:
            query: 검색 쿼리.

        Returns:
            Dict[str, Any]: 빈 결과 페이로드.
        """
        return {
            "query": query,
            "results": [],
            "generated_at": datetime.utcnow().isoformat(),
            "engines_used": [],
            "error": "no_available_engines",
        }

    def _format_result_for_context(
        self,
        result: Dict[str, Any],
        index: int,
    ) -> str:
        """
        검색 결과를 RAG 컨텍스트용으로 포맷팅합니다.

        Args:
            result: 검색 결과 딕셔너리.
            index: 결과 순번.

        Returns:
            str: 포맷팅된 결과 문자열.
        """
        title = result.get("title", "제목 없음")
        url = result.get("url", "")
        content = result.get("content", "")
        score = result.get("score", 0.0)
        source = result.get("source", "unknown")

        lines = [
            f"[{index}] {title}",
            f"    URL: {url}",
            f"    출처: {source} | 점수: {score:.2f}",
        ]

        if content:
            # 콘텐츠가 너무 길면 자름
            content_preview = content[:500] + "..." if len(content) > 500 else content
            lines.append(f"    내용: {content_preview}")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # 헬스 체크
    # -------------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """
        서비스 상태를 확인합니다.

        Returns:
            Dict[str, Any]: 상태 정보.
        """
        return {
            "available": self.is_available,
            "engines": {
                "tavily": self._tavily.available,
                "exa": self._exa.available(),
            },
            "cache_version": self.CACHE_VERSION,
        }

    def __repr__(self) -> str:
        """디버깅용 문자열 표현."""
        return (
            f"WebSearchService("
            f"available={self.is_available}, "
            f"engines={self.available_engines})"
        )


# =============================================================================
# 유틸리티 함수
# =============================================================================

def _dedupe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    검색 결과의 중복을 제거합니다.

    URL을 기준으로 중복을 제거하며, 점수가 높은 결과를 유지합니다.
    결과는 점수 기준 내림차순으로 정렬됩니다.

    Args:
        results: 중복 제거할 검색 결과 리스트.

    Returns:
        List[Dict[str, Any]]: 중복이 제거되고 정렬된 결과 리스트.
    """
    if not results:
        return []

    # URL을 키로 사용하여 중복 제거
    seen: Dict[str, Dict[str, Any]] = {}

    for item in results:
        url = str(item.get("url") or "").strip().lower()
        if not url:
            continue

        score = float(item.get("score") or 0.0)
        existing = seen.get(url)

        # 점수가 높은 결과를 유지
        if existing is None or score > float(existing.get("score") or 0.0):
            seen[url] = item

    # 점수 기준 내림차순 정렬
    merged = list(seen.values())
    merged.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)

    return merged


def merge_search_results(
    *result_lists: List[Dict[str, Any]],
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    여러 검색 결과 리스트를 병합합니다.

    Args:
        *result_lists: 병합할 검색 결과 리스트들.
        top_k: 반환할 최대 결과 수.

    Returns:
        List[Dict[str, Any]]: 병합된 결과 리스트.
    """
    all_results = []
    for results in result_lists:
        all_results.extend(results)

    deduped = _dedupe_results(all_results)
    return deduped[:top_k]
