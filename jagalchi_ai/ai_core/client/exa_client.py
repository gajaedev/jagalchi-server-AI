# =============================================================================
# Exa 검색 API 클라이언트
# =============================================================================
# Exa(구 Metaphor)의 시맨틱 검색 API와 통신하는 클라이언트 클래스입니다.
# 자연어 쿼리를 이해하고 의미적으로 관련된 콘텐츠를 검색합니다.
#
# 주요 기능:
#   - 시맨틱 검색 (자연어 기반)
#   - 유사 콘텐츠 검색
#   - 콘텐츠 추출 (텍스트, 하이라이트)
#   - 도메인 필터링
#   - 재시도 로직 (지수 백오프)
#   - 헬스 체크
#
# 환경 변수:
#   - EXA_API_KEY: Exa에서 발급받은 API 키
#
# 사용 예시:
#   client = ExaSearchClient()
#   if client.available():
#       results = client.search("Python 학습 자료")
#       for result in results:
#           print(result.title, result.score)
#
# Exa vs Tavily:
#   - Exa: 시맨틱 검색에 특화, 의미 기반 결과
#   - Tavily: 범용 웹 검색, 최신 정보 검색에 적합
# =============================================================================

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

# -----------------------------------------------------------------------------
# 선택적 의존성 임포트
# -----------------------------------------------------------------------------
# exa_py 패키지가 설치되지 않은 환경에서도 모듈 로드가 가능하도록 함
try:
    from exa_py import Exa

    EXA_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    Exa = None  # type: ignore
    EXA_AVAILABLE = False

# -----------------------------------------------------------------------------
# 재시도 로직을 위한 tenacity 임포트
# -----------------------------------------------------------------------------
try:
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
        before_sleep_log,
    )

    TENACITY_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    TENACITY_AVAILABLE = False

from jagalchi_ai.ai_core.client.exa_result import (
    ExaResult,
    filter_results_by_score,
    filter_results_by_domain,
    deduplicate_results,
    sort_results,
    results_to_context,
)

# =============================================================================
# 로거 설정
# =============================================================================
logger = logging.getLogger(__name__)

# =============================================================================
# 열거형 정의
# =============================================================================


class SearchType(str, Enum):
    """
    검색 유형 열거형.

    Exa는 두 가지 검색 모드를 제공합니다:
        - NEURAL: 시맨틱 검색 (의미 기반)
        - KEYWORD: 키워드 검색 (전통적인 방식)

    Example:
        >>> results = client.search("Python 학습", search_type=SearchType.NEURAL)
    """

    NEURAL = "neural"
    """시맨틱(의미 기반) 검색. 자연어 쿼리에 최적화."""

    KEYWORD = "keyword"
    """키워드 기반 검색. 정확한 문구 매칭에 적합."""

    AUTO = "auto"
    """자동 선택. 쿼리 특성에 따라 최적의 모드 선택."""


class ContentType(str, Enum):
    """
    콘텐츠 유형 열거형.

    검색 결과에 포함할 콘텐츠 유형을 지정합니다.
    """

    TEXT = "text"
    """전체 텍스트 콘텐츠."""

    HIGHLIGHTS = "highlights"
    """쿼리 관련 하이라이트만."""

    SUMMARY = "summary"
    """요약 텍스트."""


# =============================================================================
# 설정 데이터클래스
# =============================================================================


@dataclass
class ExaSearchOptions:
    """
    Exa 검색 옵션 설정.

    검색 동작을 세밀하게 제어하기 위한 옵션들입니다.

    Attributes:
        num_results (int):
            반환할 최대 결과 수 (기본: 10).
        search_type (SearchType):
            검색 유형 (neural, keyword, auto).
        include_text (bool):
            전체 텍스트 포함 여부.
        include_highlights (bool):
            하이라이트 포함 여부.
        include_summary (bool):
            요약 포함 여부.
        include_domains (List[str]):
            포함할 도메인 목록 (빈 리스트면 모든 도메인).
        exclude_domains (List[str]):
            제외할 도메인 목록.
        start_crawl_date (Optional[str]):
            검색할 콘텐츠의 시작 날짜 (ISO 8601).
        end_crawl_date (Optional[str]):
            검색할 콘텐츠의 종료 날짜 (ISO 8601).
        start_published_date (Optional[str]):
            발행일 시작 범위.
        end_published_date (Optional[str]):
            발행일 종료 범위.
        category (Optional[str]):
            콘텐츠 카테고리 필터.

    Example:
        >>> options = ExaSearchOptions(
        ...     num_results=20,
        ...     search_type=SearchType.NEURAL,
        ...     include_domains=["github.com", "stackoverflow.com"],
        ... )
        >>> results = client.search_with_options("Python 튜토리얼", options)
    """

    # -------------------------------------------------------------------------
    # 기본 설정
    # -------------------------------------------------------------------------

    num_results: int = 10
    """반환할 최대 결과 수."""

    search_type: SearchType = SearchType.NEURAL
    """검색 유형 (neural/keyword/auto)."""

    # -------------------------------------------------------------------------
    # 콘텐츠 포함 설정
    # -------------------------------------------------------------------------

    include_text: bool = True
    """전체 텍스트 콘텐츠 포함."""

    include_highlights: bool = True
    """쿼리 관련 하이라이트 포함."""

    include_summary: bool = False
    """요약 텍스트 포함."""

    # -------------------------------------------------------------------------
    # 도메인 필터링
    # -------------------------------------------------------------------------

    include_domains: List[str] = field(default_factory=list)
    """포함할 도메인 목록 (빈 리스트면 모든 도메인)."""

    exclude_domains: List[str] = field(default_factory=list)
    """제외할 도메인 목록."""

    # -------------------------------------------------------------------------
    # 날짜 필터링
    # -------------------------------------------------------------------------

    start_crawl_date: Optional[str] = None
    """크롤링 시작 날짜 (ISO 8601 형식)."""

    end_crawl_date: Optional[str] = None
    """크롤링 종료 날짜 (ISO 8601 형식)."""

    start_published_date: Optional[str] = None
    """발행일 시작 범위 (ISO 8601 형식)."""

    end_published_date: Optional[str] = None
    """발행일 종료 범위 (ISO 8601 형식)."""

    # -------------------------------------------------------------------------
    # 추가 필터
    # -------------------------------------------------------------------------

    category: Optional[str] = None
    """콘텐츠 카테고리 (예: 'company', 'research paper', 'news')."""

    def to_api_params(self) -> Dict[str, Any]:
        """
        API 호출을 위한 파라미터 딕셔너리로 변환합니다.

        Returns:
            Dict[str, Any]: Exa API 호출에 사용할 파라미터.

        @returns {Dict[str, Any]} Exa API 파라미터 딕셔너리.
        """
        params: Dict[str, Any] = {
            "num_results": self.num_results,
            "text": self.include_text,
        }

        # 검색 유형 (auto가 아닌 경우에만)
        if self.search_type != SearchType.AUTO:
            params["type"] = self.search_type.value

        # 도메인 필터
        if self.include_domains:
            params["include_domains"] = self.include_domains
        if self.exclude_domains:
            params["exclude_domains"] = self.exclude_domains

        # 날짜 필터
        if self.start_crawl_date:
            params["start_crawl_date"] = self.start_crawl_date
        if self.end_crawl_date:
            params["end_crawl_date"] = self.end_crawl_date
        if self.start_published_date:
            params["start_published_date"] = self.start_published_date
        if self.end_published_date:
            params["end_published_date"] = self.end_published_date

        # 카테고리
        if self.category:
            params["category"] = self.category

        return params


# =============================================================================
# 재시도 데코레이터 생성
# =============================================================================


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """
    재시도 데코레이터를 생성합니다.

    지수 백오프(exponential backoff) 전략을 사용하여
    일시적인 오류에서 자동으로 복구합니다.

    Args:
        max_attempts: 최대 재시도 횟수.
        min_wait: 최소 대기 시간(초).
        max_wait: 최대 대기 시간(초).

    Returns:
        Callable: 재시도 데코레이터 또는 패스스루 데코레이터.

    @param {int} max_attempts - 최대 재시도 횟수.
    @param {float} min_wait - 최소 대기 시간(초).
    @param {float} max_wait - 최대 대기 시간(초).
    @returns {Callable} 재시도 데코레이터.
    """
    if TENACITY_AVAILABLE:
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
    else:
        # tenacity가 없으면 단순 패스스루
        def passthrough(func: Callable) -> Callable:
            """
            데코레이터가 없는 환경에서 원본 함수를 그대로 반환합니다.

            @param {Callable} func - 래핑 대상 함수.
            @returns {Callable} 수정 없이 전달된 함수.
            """
            return func

        return passthrough


# =============================================================================
# Exa 검색 클라이언트 클래스
# =============================================================================


class ExaSearchClient:
    """
    Exa 시맨틱 검색 API 클라이언트.

    Exa의 시맨틱 검색 기능을 활용하여 자연어 쿼리에 대한
    의미적으로 관련된 콘텐츠를 검색합니다.

    Attributes:
        is_available (bool): 클라이언트 사용 가능 여부.

    Example:
        >>> # 기본 사용
        >>> client = ExaSearchClient()
        >>> results = client.search("Python 머신러닝 튜토리얼")
        >>> for result in results:
        ...     print(f"{result.title}: {result.score:.2f}")

        >>> # 고급 옵션 사용
        >>> options = ExaSearchOptions(
        ...     num_results=20,
        ...     include_domains=["medium.com", "towardsdatascience.com"],
        ... )
        >>> results = client.search_with_options("딥러닝 입문", options)

        >>> # 유사 콘텐츠 검색
        >>> similar = client.find_similar("https://example.com/article")
    """

    # -------------------------------------------------------------------------
    # 클래스 상수
    # -------------------------------------------------------------------------

    DEFAULT_MAX_RESULTS = 10
    """기본 최대 결과 수."""

    DEFAULT_TIMEOUT = 30
    """기본 타임아웃(초)."""

    DEFAULT_MAX_RETRIES = 3
    """기본 최대 재시도 횟수."""

    # -------------------------------------------------------------------------
    # 초기화
    # -------------------------------------------------------------------------

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        include_text: bool = True,
    ) -> None:
        """
        ExaSearchClient 인스턴스를 초기화합니다.

        Args:
            api_key:
                Exa API 키. 미제공 시 EXA_API_KEY 환경변수 사용.
            timeout:
                API 요청 타임아웃(초).
            max_retries:
                실패 시 최대 재시도 횟수.
            include_text:
                검색 결과에 전체 텍스트 포함 여부.

        Example:
            >>> # 환경변수에서 API 키 로드
            >>> client = ExaSearchClient()

            >>> # API 키 직접 지정
            >>> client = ExaSearchClient(api_key="your-api-key")

            >>> # 타임아웃 및 텍스트 설정
            >>> client = ExaSearchClient(timeout=60, include_text=True)

        @param {Optional[str]} api_key - Exa API 키.
        @param {int} timeout - 요청 타임아웃(초).
        @param {int} max_retries - 최대 재시도 횟수.
        @param {bool} include_text - 텍스트 포함 여부.
        @returns {None} 클라이언트를 초기화합니다.
        """
        # API 키 설정 (파라미터 > 환경변수)
        self._api_key = api_key or os.getenv("EXA_API_KEY", "")

        # 설정 저장
        self._timeout = timeout
        self._max_retries = max_retries
        self._include_text = include_text

        # Exa 클라이언트 초기화
        self._client: Optional[Any] = None
        if self._api_key and EXA_AVAILABLE:
            try:
                self._client = Exa(self._api_key)
                logger.info("Exa 검색 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(
                    "Exa 클라이언트 초기화 실패",
                    extra={"error": str(e)},
                )
                self._client = None
        elif not EXA_AVAILABLE:
            logger.warning(
                "exa_py 패키지가 설치되지 않음. "
                "'pip install exa_py'로 설치하세요."
            )

        # 재시도 데코레이터 적용
        self._execute_search_with_retry = create_retry_decorator(
            max_attempts=max_retries,
        )(self._execute_search)

    # -------------------------------------------------------------------------
    # 프로퍼티
    # -------------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """
        클라이언트가 사용 가능한지 확인합니다.

        Returns:
            bool: API 키가 있고 클라이언트가 초기화되었으면 True.

        @returns {bool} 사용 가능 여부.
        """
        return self._client is not None

    # -------------------------------------------------------------------------
    # 호환성 메서드 (레거시 지원)
    # -------------------------------------------------------------------------

    def available(self) -> bool:
        """
        클라이언트 사용 가능 여부 (레거시 메서드).

        Note:
            is_available 프로퍼티 사용을 권장합니다.

        Returns:
            bool: 사용 가능 여부.

        @returns {bool} 사용 가능 여부.
        """
        return self.is_available

    # -------------------------------------------------------------------------
    # 검색 메서드
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        search_type: SearchType = SearchType.NEURAL,
    ) -> List[ExaResult]:
        """
        시맨틱 검색을 수행합니다.

        자연어 쿼리를 이해하고 의미적으로 관련된 콘텐츠를 찾습니다.

        Args:
            query:
                검색 쿼리 (자연어).
            max_results:
                반환할 최대 결과 수 (기본: 10).
            search_type:
                검색 유형 (neural/keyword/auto).

        Returns:
            List[ExaResult]: 검색 결과 리스트 (관련성 점수순 정렬).

        Example:
            >>> results = client.search("Python 웹 프레임워크 비교")
            >>> for result in results[:5]:
            ...     print(f"[{result.score:.2f}] {result.title}")

        @param {str} query - 검색 쿼리.
        @param {int} max_results - 최대 결과 수.
        @param {SearchType} search_type - 검색 유형.
        @returns {List[ExaResult]} 검색 결과 리스트.
        """
        if not self.is_available:
            logger.warning("Exa 클라이언트가 사용 불가능한 상태")
            return []

        try:
            start_time = time.time()
            results = self._execute_search_with_retry(
                query=query,
                num_results=max_results,
                text=self._include_text,
                search_type=search_type,
            )
            elapsed = time.time() - start_time

            logger.debug(
                "Exa 검색 완료",
                extra={
                    "query": query[:50],
                    "result_count": len(results),
                    "elapsed_seconds": round(elapsed, 2),
                },
            )

            return results

        except Exception as e:
            logger.error(
                "Exa 검색 실패",
                extra={"query": query[:50], "error": str(e)},
                exc_info=True,
            )
            return []

    def search_with_options(
        self,
        query: str,
        options: ExaSearchOptions,
    ) -> List[ExaResult]:
        """
        상세 옵션을 지정하여 검색을 수행합니다.

        도메인 필터, 날짜 범위, 카테고리 등 세부 옵션을 설정할 수 있습니다.

        Args:
            query:
                검색 쿼리.
            options:
                검색 옵션 설정 객체.

        Returns:
            List[ExaResult]: 검색 결과 리스트.

        Example:
            >>> options = ExaSearchOptions(
            ...     num_results=15,
            ...     include_domains=["arxiv.org"],
            ...     start_published_date="2024-01-01",
            ... )
            >>> results = client.search_with_options("transformer architecture", options)

        @param {str} query - 검색 쿼리.
        @param {ExaSearchOptions} options - 검색 옵션.
        @returns {List[ExaResult]} 검색 결과 리스트.
        """
        if not self.is_available:
            return []

        try:
            params = options.to_api_params()
            return self._execute_search_with_retry(
                query=query,
                search_type=options.search_type,
                **params,
            )

        except Exception as e:
            logger.error(
                "Exa 옵션 검색 실패",
                extra={"query": query[:50], "error": str(e)},
                exc_info=True,
            )
            return []

    def find_similar(
        self,
        url: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        exclude_source: bool = True,
    ) -> List[ExaResult]:
        """
        주어진 URL과 유사한 콘텐츠를 검색합니다.

        Args:
            url:
                기준이 되는 웹페이지 URL.
            max_results:
                반환할 최대 결과 수.
            exclude_source:
                원본 URL을 결과에서 제외할지 여부.

        Returns:
            List[ExaResult]: 유사 콘텐츠 리스트.

        Example:
            >>> similar = client.find_similar(
            ...     "https://example.com/python-tutorial",
            ...     max_results=10,
            ... )

        @param {str} url - 기준 URL.
        @param {int} max_results - 최대 결과 수.
        @param {bool} exclude_source - 원본 제외 여부.
        @returns {List[ExaResult]} 유사 콘텐츠 리스트.
        """
        if not self.is_available:
            return []

        try:
            raw = self._client.find_similar_and_contents(
                url=url,
                num_results=max_results,
                text=self._include_text,
                exclude_source_domain=exclude_source,
            )

            results = self._parse_response(raw)

            logger.debug(
                "Exa 유사 검색 완료",
                extra={
                    "url": url[:50],
                    "result_count": len(results),
                },
            )

            return results

        except Exception as e:
            logger.error(
                "Exa 유사 검색 실패",
                extra={"url": url[:50], "error": str(e)},
                exc_info=True,
            )
            return []

    def search_news(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        days: int = 7,
    ) -> List[ExaResult]:
        """
        최근 뉴스/기사를 검색합니다.

        지정된 기간 내의 뉴스 콘텐츠만 검색합니다.

        Args:
            query:
                검색 쿼리.
            max_results:
                반환할 최대 결과 수.
            days:
                검색할 기간 (오늘로부터 N일 이내).

        Returns:
            List[ExaResult]: 뉴스 검색 결과 리스트.

        Example:
            >>> news = client.search_news("인공지능 발전", days=3)
            >>> for article in news:
            ...     print(f"{article.published_date}: {article.title}")

        @param {str} query - 검색 쿼리.
        @param {int} max_results - 최대 결과 수.
        @param {int} days - 검색 기간(일).
        @returns {List[ExaResult]} 뉴스 검색 결과 리스트.
        """
        if not self.is_available:
            return []

        # 날짜 범위 계산
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        options = ExaSearchOptions(
            num_results=max_results,
            search_type=SearchType.NEURAL,
            category="news",
            start_published_date=start_date.strftime("%Y-%m-%d"),
            end_published_date=end_date.strftime("%Y-%m-%d"),
        )

        return self.search_with_options(query, options)

    def search_research(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> List[ExaResult]:
        """
        학술/연구 논문을 검색합니다.

        학술 관련 도메인과 카테고리로 필터링합니다.

        Args:
            query:
                검색 쿼리.
            max_results:
                반환할 최대 결과 수.

        Returns:
            List[ExaResult]: 연구 논문 검색 결과.

        Example:
            >>> papers = client.search_research("neural network optimization")

        @param {str} query - 검색 쿼리.
        @param {int} max_results - 최대 결과 수.
        @returns {List[ExaResult]} 연구 논문 결과 리스트.
        """
        if not self.is_available:
            return []

        options = ExaSearchOptions(
            num_results=max_results,
            search_type=SearchType.NEURAL,
            category="research paper",
            include_domains=[
                "arxiv.org",
                "scholar.google.com",
                "semanticscholar.org",
                "papers.ssrn.com",
                "researchgate.net",
            ],
        )

        return self.search_with_options(query, options)

    # -------------------------------------------------------------------------
    # 내부 메서드
    # -------------------------------------------------------------------------

    def _execute_search(
        self,
        query: str,
        search_type: SearchType = SearchType.NEURAL,
        **kwargs: Any,
    ) -> List[ExaResult]:
        """
        실제 검색 API 호출을 수행합니다 (내부 메서드).

        재시도 데코레이터가 적용되어 일시적 오류 시 자동 재시도합니다.

        Args:
            query: 검색 쿼리.
            search_type: 검색 유형.
            **kwargs: 추가 API 파라미터.

        Returns:
            List[ExaResult]: 검색 결과 리스트.

        @param {str} query - 검색 쿼리.
        @param {SearchType} search_type - 검색 유형.
        @param {Any} kwargs - 추가 API 파라미터.
        @returns {List[ExaResult]} 검색 결과 리스트.
        """
        if self._client is None:
            return []

        # API 파라미터 구성
        api_params = {
            "query": query,
            **kwargs,
        }

        # 검색 유형 설정
        if search_type != SearchType.AUTO:
            api_params["type"] = search_type.value

        # API 호출
        raw = self._client.search_and_contents(**api_params)

        return self._parse_response(raw)

    def _parse_response(self, raw: Any) -> List[ExaResult]:
        """
        API 응답을 ExaResult 리스트로 파싱합니다.

        Args:
            raw: Exa API 원본 응답.

        Returns:
            List[ExaResult]: 파싱된 검색 결과 리스트.

        @param {Any} raw - Exa API 원본 응답.
        @returns {List[ExaResult]} 파싱된 검색 결과 리스트.
        """
        results: List[ExaResult] = []

        for item in getattr(raw, "results", []) or []:
            # 기본 필드 추출
            title = getattr(item, "title", "") or ""
            url = getattr(item, "url", "") or ""
            content = self._extract_content(item)
            score = float(getattr(item, "score", 0.0) or 0.0)

            # 날짜 추출 (여러 속성명 시도)
            published_date = (
                getattr(item, "published_date", None)
                or getattr(item, "publishedDate", None)
            )

            # 추가 필드
            author = getattr(item, "author", None)
            highlights = getattr(item, "highlights", []) or []

            # URL이 없으면 건너뛰기
            if not url:
                continue

            results.append(
                ExaResult(
                    title=title,
                    url=url,
                    content=content,
                    score=score,
                    published_date=published_date,
                    author=author,
                    highlights=highlights if isinstance(highlights, list) else [],
                )
            )

        return results

    def _extract_content(self, item: Any) -> str:
        """
        검색 결과 항목에서 콘텐츠를 추출합니다.

        여러 필드를 우선순위에 따라 확인합니다:
        1. summary (요약)
        2. text (전체 텍스트)
        3. highlights (하이라이트, 결합)
        4. snippet (짧은 미리보기)

        Args:
            item: 검색 결과 항목 객체.

        Returns:
            str: 추출된 콘텐츠 텍스트.

        @param {Any} item - 검색 결과 항목 객체.
        @returns {str} 추출된 콘텐츠 텍스트.
        """
        # 1. 요약 확인
        summary = getattr(item, "summary", None)
        if isinstance(summary, str) and summary.strip():
            return summary.strip()

        # 2. 전체 텍스트 확인
        text = getattr(item, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        # 3. 하이라이트 결합
        highlights = getattr(item, "highlights", None)
        if isinstance(highlights, list) and highlights:
            joined = " ".join(str(h) for h in highlights if h)
            if joined.strip():
                return joined.strip()

        # 4. 스니펫 확인
        snippet = getattr(item, "snippet", "")
        return str(snippet).strip() if snippet else ""

    # -------------------------------------------------------------------------
    # RAG 파이프라인 지원
    # -------------------------------------------------------------------------

    def get_search_context(
        self,
        query: str,
        max_results: int = 5,
        max_tokens: int = 4000,
    ) -> str:
        """
        RAG 파이프라인용 검색 컨텍스트를 생성합니다.

        검색 결과를 LLM이 사용하기 좋은 형식으로 포맷팅합니다.

        Args:
            query:
                검색 쿼리.
            max_results:
                포함할 최대 결과 수.
            max_tokens:
                대략적인 최대 토큰 수.

        Returns:
            str: RAG용 포맷팅된 컨텍스트.

        Example:
            >>> context = client.get_search_context("Python 비동기 프로그래밍")
            >>> # LLM에 전달
            >>> prompt = f"다음 정보를 참고하여 답변하세요:\\n{context}\\n\\n질문: ..."

        @param {str} query - 검색 쿼리.
        @param {int} max_results - 최대 결과 수.
        @param {int} max_tokens - 최대 토큰 수.
        @returns {str} RAG 컨텍스트 문자열.
        """
        results = self.search(query, max_results=max_results)

        if not results:
            return ""

        return results_to_context(
            results=results,
            max_results=max_results,
            max_tokens=max_tokens,
        )

    # -------------------------------------------------------------------------
    # 유틸리티 메서드
    # -------------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """
        클라이언트 상태를 확인합니다.

        Returns:
            Dict[str, Any]: 상태 정보 딕셔너리.

        Example:
            >>> status = client.health_check()
            >>> print(status)
            {'available': True, 'api_key_set': True, ...}

        @returns {Dict[str, Any]} 상태 정보 딕셔너리.
        """
        status = {
            "available": self.is_available,
            "api_key_set": bool(self._api_key),
            "exa_installed": EXA_AVAILABLE,
            "tenacity_installed": TENACITY_AVAILABLE,
            "timeout": self._timeout,
            "max_retries": self._max_retries,
            "include_text": self._include_text,
        }

        # 연결 테스트 (선택적)
        if self.is_available:
            try:
                # 간단한 테스트 쿼리
                test_results = self.search("test", max_results=1)
                status["connection_test"] = "success"
                status["test_result_count"] = len(test_results)
            except Exception as e:
                status["connection_test"] = "failed"
                status["connection_error"] = str(e)

        return status

    def __repr__(self) -> str:
        """
        디버깅용 문자열 표현.

        @returns {str} 디버깅 문자열.
        """
        return (
            f"ExaSearchClient("
            f"available={self.is_available}, "
            f"include_text={self._include_text})"
        )


# =============================================================================
# 편의 함수
# =============================================================================


def get_default_client() -> ExaSearchClient:
    """
    기본 설정의 Exa 클라이언트를 반환합니다.

    Returns:
        ExaSearchClient: 기본 설정의 클라이언트 인스턴스.

    Example:
        >>> client = get_default_client()
        >>> results = client.search("query")

    @returns {ExaSearchClient} 기본 설정 클라이언트.
    """
    return ExaSearchClient()


def quick_search(query: str, max_results: int = 5) -> List[ExaResult]:
    """
    간단한 검색을 위한 편의 함수.

    클라이언트 인스턴스 생성 없이 빠르게 검색합니다.

    Args:
        query: 검색 쿼리.
        max_results: 최대 결과 수.

    Returns:
        List[ExaResult]: 검색 결과 리스트.

    Example:
        >>> results = quick_search("Python 학습 자료")
        >>> for r in results:
        ...     print(r.title)

    @param {str} query - 검색 쿼리.
    @param {int} max_results - 최대 결과 수.
    @returns {List[ExaResult]} 검색 결과 리스트.
    """
    client = ExaSearchClient()
    return client.search(query, max_results=max_results)
