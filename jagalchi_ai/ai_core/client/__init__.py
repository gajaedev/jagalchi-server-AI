# =============================================================================
# AI 클라이언트 모듈
# =============================================================================
# 외부 AI 서비스와 통신하는 클라이언트들을 제공합니다.
#
# 지원 서비스:
#   - Tavily: 웹 검색 API (RAG, 뉴스 검색)
#   - Exa: 시맨틱 검색 API (의미 기반 검색)
#   - Gemini: Google LLM API (텍스트 생성)
#
# 사용 예시:
#   from jagalchi_ai.ai_core.client import (
#       TavilySearchClient,
#       ExaSearchClient,
#       GeminiClient,
#   )
#
#   # Tavily 웹 검색
#   tavily = TavilySearchClient()
#   results = tavily.search("Python 학습 자료")
#
#   # Exa 시맨틱 검색
#   exa = ExaSearchClient()
#   results = exa.search("머신러닝 튜토리얼")
#
#   # Gemini 텍스트 생성
#   gemini = GeminiClient()
#   response = gemini.generate_text("안녕하세요!")
# =============================================================================

from __future__ import annotations

# -----------------------------------------------------------------------------
# Tavily 클라이언트 (웹 검색)
# -----------------------------------------------------------------------------
from jagalchi_ai.ai_core.client.tavily_client import (
    TavilySearchClient,
    TavilySearchOptions,
    SearchDepth,
    SearchTopic,
)
from jagalchi_ai.ai_core.client.tavily_result import TavilyResult

# -----------------------------------------------------------------------------
# Exa 클라이언트 (시맨틱 검색)
# -----------------------------------------------------------------------------
from jagalchi_ai.ai_core.client.exa_client import (
    ExaSearchClient,
    ExaSearchOptions,
    SearchType,
    ContentType,
    get_default_client as get_default_exa_client,
    quick_search as exa_quick_search,
)
from jagalchi_ai.ai_core.client.exa_result import (
    ExaResult,
    filter_results_by_score,
    filter_results_by_domain,
    deduplicate_results,
    sort_results,
    results_to_context,
)

# -----------------------------------------------------------------------------
# Gemini 클라이언트 (LLM)
# -----------------------------------------------------------------------------
from jagalchi_ai.ai_core.client.gemini_client import (
    GeminiClient,
    GeminiModel,
    SafetyLevel,
    GenerationConfig,
    get_default_client as get_default_gemini_client,
    quick_generate,
)
from jagalchi_ai.ai_core.client.gemini_response import (
    GeminiResponse,
    create_empty_response,
    create_error_response,
)


# =============================================================================
# 공개 API 정의
# =============================================================================

__all__ = [
    # -------------------------------------------------------------------------
    # Tavily (웹 검색)
    # -------------------------------------------------------------------------
    "TavilySearchClient",
    "TavilySearchOptions",
    "TavilyResult",
    "SearchDepth",
    "SearchTopic",

    # -------------------------------------------------------------------------
    # Exa (시맨틱 검색)
    # -------------------------------------------------------------------------
    "ExaSearchClient",
    "ExaSearchOptions",
    "ExaResult",
    "SearchType",
    "ContentType",
    "get_default_exa_client",
    "exa_quick_search",
    # 유틸리티 함수
    "filter_results_by_score",
    "filter_results_by_domain",
    "deduplicate_results",
    "sort_results",
    "results_to_context",

    # -------------------------------------------------------------------------
    # Gemini (LLM)
    # -------------------------------------------------------------------------
    "GeminiClient",
    "GeminiModel",
    "GeminiResponse",
    "SafetyLevel",
    "GenerationConfig",
    "get_default_gemini_client",
    "quick_generate",
    "create_empty_response",
    "create_error_response",
]


# =============================================================================
# 모듈 버전 정보
# =============================================================================

__version__ = "1.0.0"
__author__ = "Jagalchi AI Team"
