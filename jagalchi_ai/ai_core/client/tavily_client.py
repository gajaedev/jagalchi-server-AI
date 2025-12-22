"""
=============================================================================
Tavily 검색 클라이언트 모듈 (Tavily Search Client Module)

이 모듈은 Tavily API를 사용하여 고품질의 웹 검색을 수행하는 클라이언트를 제공합니다.
단순한 API 래퍼를 넘어, 엔터프라이즈급 애플리케이션에 필요한 견고성, 확장성,
그리고 개발자 편의성을 갖추도록 설계되었습니다.

설계 철학 및 주요 기능:
    1.  **타입 안전성 (Type Safety)**: Pydantic 모델을 사용하여 입출력 데이터를 엄격하게 검증합니다.
        이는 런타임 오류를 방지하고 IDE의 자동 완성 기능을 극대화합니다.
    2.  **비동기 지원 (Async Support)**: Django의 비동기 뷰나 FastAPI와 같은 최신 프레임워크와의
        호환성을 위해 `search_async` 메서드를 제공합니다. I/O 바운드 작업의 성능을 최적화합니다.
    3.  **결함 감내 (Fault Tolerance)**: `tenacity` 라이브러리를 활용한 지수 백오프(Exponential Backoff)
        재시도 로직을 적용하여, 일시적인 네트워크 장애나 API 속도 제한에 유연하게 대처합니다.
    4.  **확장성 (Extensibility)**: 옵션 패턴과 Pydantic 설정을 통해 검색 파라미터를 손쉽게 확장하고
        관리할 수 있습니다.

사용 예시:
    >>> # 동기 방식 사용
    >>> client = TavilySearchClient()
    >>> results = client.search("최신 AI 트렌드", max_results=3)

    >>> # 비동기 방식 사용
    >>> results = await client.search_async("비동기 Python", max_results=3)

환경변수:
    - `TAVILY_API_KEY`: Tavily API 인증 키 (필수)
    - `AI_DISABLE_EXTERNAL`: 외부 API 호출 비활성화 (테스트/개발용)

참고:
    - Tavily API Docs: https://docs.tavily.com/
    - Pydantic Docs: https://docs.pydantic.dev/
=============================================================================
"""

from __future__ import annotations

import asyncio
import logging
import os
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

# -----------------------------------------------------------------------------
# 서드파티 라이브러리 (조건부 임포트 및 타입 체크)
# -----------------------------------------------------------------------------
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TavilyClient = None  # type: ignore
    TAVILY_AVAILABLE = False

try:
    from tenacity import (
        before_sleep_log,
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

from pydantic import BaseModel, Field, SecretStr, field_validator

# -----------------------------------------------------------------------------
# 로컬 모듈 임포트
# -----------------------------------------------------------------------------
from jagalchi_ai.ai_core.client.tavily_result import TavilyResult

# -----------------------------------------------------------------------------
# 로거 설정
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 상수 및 열거형 정의
# -----------------------------------------------------------------------------
class SearchDepth(str, Enum):
    """
    검색 깊이 수준을 정의합니다.

    - BASIC: 빠른 응답 속도, 일반적인 검색 결과 (약 1초 소요)
    - ADVANCED: 심층 분석, 더 높은 품질의 결과 (약 3-5초 소요)
    """
    BASIC = "basic"
    ADVANCED = "advanced"


class SearchTopic(str, Enum):
    """
    검색 주제 도메인을 정의합니다.

    - GENERAL: 일반적인 웹 검색
    - NEWS: 뉴스 기사 위주의 검색 (최신성 중시)
    """
    GENERAL = "general"
    NEWS = "news"


# 기본 설정값
DEFAULT_MAX_RESULTS = 5
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3


# -----------------------------------------------------------------------------
# Pydantic 모델 정의 (데이터 검증 및 직렬화)
# -----------------------------------------------------------------------------
class TavilySearchOptions(BaseModel):
    """
    Tavily 검색 옵션 모델.

    검색 요청 시 사용할 다양한 파라미터를 정의하고 검증합니다.
    Pydantic을 사용하여 잘못된 값이 전달되는 것을 사전에 방지합니다.
    """
    max_results: int = Field(
        default=DEFAULT_MAX_RESULTS,
        ge=1,
        le=20,
        description="반환할 최대 검색 결과 수 (1-20)"
    )
    search_depth: SearchDepth = Field(
        default=SearchDepth.BASIC,
        description="검색 깊이 (basic/advanced)"
    )
    topic: SearchTopic = Field(
        default=SearchTopic.GENERAL,
        description="검색 주제 (general/news)"
    )
    include_answer: bool = Field(
        default=False,
        description="AI가 생성한 답변 포함 여부"
    )
    include_raw_content: bool = Field(
        default=False,
        description="HTML 원본 콘텐츠 포함 여부 (토큰 소모 주의)"
    )
    include_images: bool = Field(
        default=False,
        description="관련 이미지 포함 여부"
    )
    include_domains: List[str] = Field(
        default_factory=list,
        description="검색 대상 도메인 리스트 (화이트리스트)"
    )
    exclude_domains: List[str] = Field(
        default_factory=list,
        description="검색 제외 도메인 리스트 (블랙리스트)"
    )
    days: Optional[int] = Field(
        default=None,
        ge=1,
        description="최근 N일간의 데이터로 제한 (뉴스 검색 시 유효)"
    )

    class Config:
        """Pydantic 설정: 열거형 값을 문자열로 사용"""
        use_enum_values = True

    def to_api_params(self) -> Dict[str, Any]:
        """
        Tavily API 호환 파라미터 딕셔너리로 변환합니다.

        None 값인 필드는 제외하여 API 호출 시 불필요한 파라미터 전달을 막습니다.

        @returns {Dict[str, Any]} Tavily API 파라미터 딕셔너리.
        """
        data = self.model_dump(exclude_none=True)
        # API에서 days가 0이거나 None이면 무시하도록 처리
        if 'days' in data and data['days'] is None:
            del data['days']
        return data


# -----------------------------------------------------------------------------
# 유틸리티: 재시도 데코레이터 팩토리
# -----------------------------------------------------------------------------
def create_retry_decorator(
    max_retries: int = DEFAULT_MAX_RETRIES,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """
    네트워크 요청 실패 시 재시도를 위한 데코레이터를 생성합니다.

    `tenacity` 라이브러리가 설치되어 있다면 지수 백오프(Exponential Backoff)를 적용하여
    서버 부하를 줄이면서 안정적으로 재시도합니다.

    Args:
        max_retries: 최대 재시도 횟수
        min_wait: 최소 대기 시간 (초)
        max_wait: 최대 대기 시간 (초)

    Returns:
        함수를 래핑하는 데코레이터

    @param {int} max_retries - 최대 재시도 횟수.
    @param {float} min_wait - 최소 대기 시간(초).
    @param {float} max_wait - 최대 대기 시간(초).
    @returns {Callable} 재시도 데코레이터.
    """
    if TENACITY_AVAILABLE:
        return retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type((Exception, TimeoutError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
    
    # Tenacity가 없는 경우 (No-op)
    def fallback_decorator(func: Callable) -> Callable:
        """
        재시도 미지원 환경에서 원본 함수를 그대로 반환합니다.

        @param {Callable} func - 래핑 대상 함수.
        @returns {Callable} 원본 함수.
        """
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            원본 함수를 그대로 호출합니다.

            @param {Any} args - 위치 인자.
            @param {Any} kwargs - 키워드 인자.
            @returns {Any} 원본 함수의 반환값.
            """
            return func(*args, **kwargs)
        return wrapper
    
    return fallback_decorator


# -----------------------------------------------------------------------------
# Tavily 검색 클라이언트 클래스
# -----------------------------------------------------------------------------
class TavilySearchClient:
    """
    Tavily Web Search API 클라이언트.

    이 클래스는 Tavily 검색 엔진의 기능을 파이썬 애플리케이션에 손쉽게 통합할 수 있도록 돕습니다.
    동기(Sync) 및 비동기(Async) 메서드를 모두 지원하여 다양한 환경에 대응합니다.

    Attributes:
        _api_key (str): Tavily API 키
        _client (Optional[TavilyClient]): 내부 Tavily 클라이언트 객체
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        클라이언트를 초기화합니다.

        Args:
            api_key: API 키. 제공되지 않으면 환경변수 `TAVILY_API_KEY`를 사용합니다.
            timeout: 요청 타임아웃 (초).
            max_retries: 요청 실패 시 최대 재시도 횟수.

        @param {Optional[str]} api_key - Tavily API 키.
        @param {int} timeout - 요청 타임아웃(초).
        @param {int} max_retries - 최대 재시도 횟수.
        @returns {None} 클라이언트를 초기화합니다.
        """
        # API 키 로드 (인자 -> 환경변수 순)
        self._api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self._timeout = timeout
        self._max_retries = max_retries

        # 테스트 모드 확인
        self._disabled = os.getenv("AI_DISABLE_EXTERNAL", "false").lower() == "true"

        self._client: Optional[TavilyClient] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """
        내부 Tavily 클라이언트를 안전하게 초기화합니다.
        SDK 미설치, API 키 누락, 비활성화 설정 등을 체크합니다.

        @returns {None} 내부 클라이언트를 초기화합니다.
        """
        if self._disabled:
            logger.info("외부 API 호출이 비활성화되었습니다 (AI_DISABLE_EXTERNAL=True).")
            return

        if not TAVILY_AVAILABLE:
            logger.warning("Tavily SDK('tavily-python')가 설치되지 않았습니다.")
            return

        if not self._api_key:
            logger.warning("Tavily API 키가 설정되지 않았습니다.")
            return

        try:
            self._client = TavilyClient(api_key=self._api_key)
            logger.info("Tavily 검색 클라이언트가 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.error(f"Tavily 클라이언트 초기화 중 오류 발생: {e}")
            self._client = None

    @property
    def available(self) -> bool:
        """
        클라이언트가 사용 가능한 상태인지 확인합니다.

        @returns {bool} 사용 가능 여부.
        """
        return self._client is not None and not self._disabled

    # -------------------------------------------------------------------------
    # 동기 검색 메서드 (Synchronous Search)
    # -------------------------------------------------------------------------
    def search(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        search_depth: SearchDepth = SearchDepth.BASIC,
        include_raw_content: bool = False,
        **kwargs: Any,
    ) -> List[TavilyResult]:
        """
        동기 방식으로 웹 검색을 수행합니다.

        Args:
            query: 검색어
            max_results: 최대 결과 수
            search_depth: 검색 깊이
            include_raw_content: 본문 포함 여부
            **kwargs: 기타 TavilySearchOptions 파라미터

        Returns:
            검색 결과 리스트 (TavilyResult 객체의 리스트)

        @param {str} query - 검색어.
        @param {int} max_results - 최대 결과 수.
        @param {SearchDepth} search_depth - 검색 깊이.
        @param {bool} include_raw_content - 본문 포함 여부.
        @param {Any} kwargs - 기타 옵션.
        @returns {List[TavilyResult]} 검색 결과 리스트.
        """
        options = TavilySearchOptions(
            max_results=max_results,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
            **kwargs
        )
        return self.search_with_options(query, options)

    def search_with_options(
        self,
        query: str,
        options: TavilySearchOptions,
    ) -> List[TavilyResult]:
        """
        상세 옵션을 적용하여 검색을 수행합니다.

        Args:
            query: 검색어
            options: 검증된 검색 옵션 객체

        Returns:
            검색 결과 리스트

        @param {str} query - 검색어.
        @param {TavilySearchOptions} options - 검색 옵션 객체.
        @returns {List[TavilyResult]} 검색 결과 리스트.
        """
        if not self.available:
            logger.warning("Tavily 클라이언트를 사용할 수 없습니다.")
            return []

        if not query.strip():
            return []

        return self._execute_search(query, options)

    # -------------------------------------------------------------------------
    # 비동기 검색 메서드 (Asynchronous Search)
    # -------------------------------------------------------------------------
    async def search_async(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        search_depth: SearchDepth = SearchDepth.BASIC,
        **kwargs: Any,
    ) -> List[TavilyResult]:
        """
        비동기 방식으로 웹 검색을 수행합니다. (Non-blocking)

        이 메서드는 내부적으로 `asyncio.to_thread`를 사용하여 동기식 Tavily 클라이언트를
        별도 스레드에서 실행합니다. 이를 통해 메인 이벤트 루프의 차단을 방지합니다.

        Args:
            query: 검색어
            max_results: 최대 결과 수
            search_depth: 검색 깊이
            **kwargs: 기타 옵션

        Returns:
            검색 결과 리스트 (Coroutine)

        @param {str} query - 검색어.
        @param {int} max_results - 최대 결과 수.
        @param {SearchDepth} search_depth - 검색 깊이.
        @param {Any} kwargs - 기타 옵션.
        @returns {List[TavilyResult]} 검색 결과 리스트.
        """
        options = TavilySearchOptions(
            max_results=max_results,
            search_depth=search_depth,
            **kwargs
        )
        return await self.search_with_options_async(query, options)

    async def search_with_options_async(
        self,
        query: str,
        options: TavilySearchOptions,
    ) -> List[TavilyResult]:
        """
        옵션 객체를 사용하여 비동기 검색을 수행합니다.

        @param {str} query - 검색어.
        @param {TavilySearchOptions} options - 검색 옵션 객체.
        @returns {List[TavilyResult]} 검색 결과 리스트.
        """
        if not self.available:
            return []

        # 동기 메서드를 스레드 풀에서 실행
        return await asyncio.to_thread(self.search_with_options, query, options)

    # -------------------------------------------------------------------------
    # 뉴스 및 컨텍스트 검색 편의 메서드
    # -------------------------------------------------------------------------
    def search_news(
        self,
        query: str,
        days: int = 7,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> List[TavilyResult]:
        """
        뉴스 기사 전용 검색 메서드입니다.

        Args:
            query: 검색어
            days: 검색 기간 (최근 N일)
            max_results: 결과 수

        Returns:
            뉴스 검색 결과 리스트

        @param {str} query - 검색어.
        @param {int} days - 검색 기간(일).
        @param {int} max_results - 최대 결과 수.
        @returns {List[TavilyResult]} 뉴스 검색 결과 리스트.
        """
        options = TavilySearchOptions(
            topic=SearchTopic.NEWS,
            days=days,
            max_results=max_results,
            search_depth=SearchDepth.BASIC
        )
        return self.search_with_options(query, options)

    async def get_search_context_async(
        self,
        query: str,
        max_results: int = 5,
        max_tokens: int = 4000,
    ) -> str:
        """
        LLM 프롬프트에 주입할 컨텍스트 문자열을 비동기로 생성합니다.
        RAG(Retrieval-Augmented Generation) 파이프라인에서 유용합니다.

        Args:
            query: 검색어
            max_results: 결과 수
            max_tokens: 최대 허용 토큰 수 (문자 수 기반 근사치)

        Returns:
            포맷팅된 컨텍스트 문자열

        @param {str} query - 검색어.
        @param {int} max_results - 결과 수.
        @param {int} max_tokens - 최대 토큰 수.
        @returns {str} 컨텍스트 문자열.
        """
        results = await self.search_async(query, max_results=max_results)
        return self._format_results_to_context(results, max_tokens)

    # -------------------------------------------------------------------------
    # 내부 로직 (Private Implementation)
    # -------------------------------------------------------------------------
    @create_retry_decorator()
    def _execute_search(
        self,
        query: str,
        options: TavilySearchOptions,
    ) -> List[TavilyResult]:
        """
        실제 API 호출을 수행하는 내부 메서드. (재시도 로직 적용됨)

        @param {str} query - 검색어.
        @param {TavilySearchOptions} options - 검색 옵션 객체.
        @returns {List[TavilyResult]} 검색 결과 리스트.
        """
        try:
            params = options.to_api_params()
            logger.debug(f"Tavily 검색 요청: query='{query}', params={params}")

            # SDK 호출
            # TavilyClient의 search 메서드는 딕셔너리를 반환함
            response = self._client.search(query=query, **params)  # type: ignore

            results = self._parse_response(response)
            logger.info(f"Tavily 검색 성공: {len(results)}건 반환")
            return results

        except Exception as e:
            logger.error(f"Tavily API 호출 중 오류 발생: {e}", exc_info=True)
            raise  # 재시도 데코레이터가 처리하도록 전파

    def _parse_response(self, raw_response: Dict[str, Any]) -> List[TavilyResult]:
        """
        API 원본 응답을 도메인 모델(TavilyResult)로 변환합니다.

        @param {Dict[str, Any]} raw_response - 원본 응답.
        @returns {List[TavilyResult]} 파싱된 결과 리스트.
        """
        results: List[TavilyResult] = []
        raw_items = raw_response.get("results", [])

        for item in raw_items:
            try:
                # 점수 보정 (0~1 사이로 클램핑)
                raw_score = float(item.get("score", 0.0))
                score = max(0.0, min(1.0, raw_score))

                # 본문 추출 (content -> raw_content -> snippet 순서)
                content = (
                    item.get("content") or
                    item.get("raw_content") or
                    item.get("snippet") or
                    ""
                ).strip()

                result = TavilyResult(
                    title=item.get("title", "No Title").strip(),
                    url=item.get("url", "").strip(),
                    content=content,
                    score=round(score, 4),
                    published_date=item.get("published_date")
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"결과 항목 파싱 중 오류 (건너뜀): {e}")
                continue

        # 관련성 점수 기준 내림차순 정렬
        return sorted(results, key=lambda x: x.score, reverse=True)

    def _format_results_to_context(
        self,
        results: List[TavilyResult],
        max_chars_approx: int
    ) -> str:
        """
        검색 결과를 LLM 컨텍스트 포맷으로 변환합니다.

        @param {List[TavilyResult]} results - 검색 결과 리스트.
        @param {int} max_chars_approx - 최대 문자 수 추정치.
        @returns {str} 컨텍스트 문자열.
        """
        if not results:
            return ""

        context_parts = []
        current_length = 0
        # 토큰 수 대략 계산 (한글/영어 혼용 고려하여 넉넉하게 4배수)
        char_limit = max_chars_approx * 4

        for i, res in enumerate(results, 1):
            part = (
                f"[{i}] {res.title}\n"
                f"Source: {res.url}\n"
                f"Content: {res.content}\n"
            )
            
            if current_length + len(part) > char_limit:
                break
                
            context_parts.append(part)
            current_length += len(part)

        return "\n".join(context_parts)
