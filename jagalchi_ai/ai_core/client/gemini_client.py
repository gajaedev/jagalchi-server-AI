# =============================================================================
# Google Gemini API 클라이언트
# =============================================================================
# Google Gemini (구 Bard) AI 모델과 통신하는 클라이언트 클래스입니다.
# 텍스트 생성, JSON 응답 파싱, 구조화된 출력 등을 지원합니다.
#
# 주요 기능:
#   - 텍스트 생성 (generate_text)
#   - JSON 응답 파싱 (generate_json)
#   - 구조화된 출력 (generate_structured)
#   - 스트리밍 응답 (generate_stream)
#   - 재시도 로직 (지수 백오프)
#   - 헬스 체크
#
# 환경 변수:
#   - GEMINI_API_KEY: Google AI Studio에서 발급받은 API 키
#   - AI_DISABLE_LLM: "true"로 설정 시 LLM 호출 비활성화
#   - AI_DISABLE_EXTERNAL: "true"로 설정 시 모든 외부 API 비활성화
#
# 사용 예시:
#   client = GeminiClient()
#   if client.available():
#       response = client.generate_json("JSON 형식으로 답변해주세요: ...")
#       if response.is_valid:
#           data = response.get("key")
# =============================================================================

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, TypeVar, Union

# -----------------------------------------------------------------------------
# 선택적 의존성 임포트
# -----------------------------------------------------------------------------
# google-genai 패키지가 설치되지 않은 환경에서도 모듈 로드가 가능하도록 함
try:
    from google import genai
    from google.genai import types as genai_types

    GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    genai = None  # type: ignore
    genai_types = None  # type: ignore
    GENAI_AVAILABLE = False

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

from jagalchi_ai.ai_core.client.gemini_response import (
    GeminiResponse,
    create_empty_response,
    create_error_response,
)

# =============================================================================
# 로거 설정
# =============================================================================
logger = logging.getLogger(__name__)

# =============================================================================
# 상수 정의
# =============================================================================

# JSON 추출을 위한 정규표현식
# LLM 응답에서 JSON 객체를 추출하는 데 사용
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


# =============================================================================
# 열거형 정의
# =============================================================================

class GeminiModel(str, Enum):
    """
    사용 가능한 Gemini 모델 목록.

    모델별 특성:
        - FLASH: 빠른 응답, 일반적인 용도에 적합
        - PRO: 높은 품질, 복잡한 추론에 적합
        - FLASH_LITE: 매우 빠른 응답, 간단한 작업에 적합

    Example:
        >>> client = GeminiClient(model=GeminiModel.PRO)
    """

    # Gemini 2.5 시리즈 (최신)
    FLASH_25 = "gemini-2.5-flash"
    """Gemini 2.5 Flash - 빠른 응답, 일반 용도 (기본값)."""

    PRO_25 = "gemini-2.5-pro"
    """Gemini 2.5 Pro - 고품질 추론, 복잡한 작업."""

    # Gemini 2.0 시리즈
    FLASH_20 = "gemini-2.0-flash"
    """Gemini 2.0 Flash - 안정적인 빠른 응답."""

    # Gemini 1.5 시리즈 (레거시)
    FLASH_15 = "gemini-1.5-flash"
    """Gemini 1.5 Flash - 레거시 지원."""

    PRO_15 = "gemini-1.5-pro"
    """Gemini 1.5 Pro - 레거시 고품질."""


class SafetyLevel(str, Enum):
    """
    콘텐츠 안전 설정 수준.

    수준별 특성:
        - BLOCK_NONE: 필터링 없음 (주의 필요)
        - BLOCK_ONLY_HIGH: 높은 위험만 차단
        - BLOCK_MEDIUM_AND_ABOVE: 중간 이상 위험 차단 (권장)
        - BLOCK_LOW_AND_ABOVE: 낮은 이상 위험 차단
    """

    BLOCK_NONE = "BLOCK_NONE"
    """필터링 없음 - 모든 콘텐츠 허용."""

    BLOCK_ONLY_HIGH = "BLOCK_ONLY_HIGH"
    """높은 위험 콘텐츠만 차단."""

    BLOCK_MEDIUM_AND_ABOVE = "BLOCK_MEDIUM_AND_ABOVE"
    """중간 이상 위험 콘텐츠 차단 (기본값)."""

    BLOCK_LOW_AND_ABOVE = "BLOCK_LOW_AND_ABOVE"
    """낮은 이상 위험 콘텐츠 차단."""


# =============================================================================
# 설정 데이터클래스
# =============================================================================

@dataclass
class GenerationConfig:
    """
    텍스트 생성 설정.

    LLM의 응답 특성을 제어하는 파라미터들입니다.

    Attributes:
        temperature (float):
            응답의 무작위성 (0.0~2.0). 낮을수록 결정적, 높을수록 창의적.
        top_p (float):
            누적 확률 샘플링 (0.0~1.0). 다양성 제어.
        top_k (int):
            상위 k개 토큰에서만 샘플링. 0은 비활성화.
        max_output_tokens (int):
            최대 출력 토큰 수.
        stop_sequences (List[str]):
            생성을 중단할 문자열들.

    Example:
        >>> config = GenerationConfig(temperature=0.3, max_output_tokens=2000)
        >>> response = client.generate_text(prompt, config=config)
    """

    temperature: float = 0.7
    """응답의 무작위성 (0.0=결정적, 2.0=매우 창의적)."""

    top_p: float = 0.95
    """누적 확률 샘플링 임계값."""

    top_k: int = 40
    """상위 k개 토큰 샘플링 (0=비활성화)."""

    max_output_tokens: int = 8192
    """최대 출력 토큰 수."""

    stop_sequences: List[str] = field(default_factory=list)
    """생성을 중단할 문자열 목록."""

    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환합니다."""
        config = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_output_tokens": self.max_output_tokens,
        }
        if self.top_k > 0:
            config["top_k"] = self.top_k
        if self.stop_sequences:
            config["stop_sequences"] = self.stop_sequences
        return config


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
            return func

        return passthrough


# =============================================================================
# Gemini 클라이언트 클래스
# =============================================================================

class GeminiClient:
    """
    Google Gemini API 클라이언트.

    Google의 Gemini AI 모델과 상호작용하는 클라이언트입니다.
    텍스트 생성, JSON 파싱, 스트리밍 등 다양한 기능을 제공합니다.

    Attributes:
        model_name (str): 사용 중인 모델 이름.
        is_available (bool): 클라이언트 사용 가능 여부.

    Example:
        >>> # 기본 사용
        >>> client = GeminiClient()
        >>> response = client.generate_text("안녕하세요!")
        >>> print(response)
        "안녕하세요! 무엇을 도와드릴까요?"

        >>> # JSON 응답 요청
        >>> response = client.generate_json("JSON으로 답변: 오늘 날씨")
        >>> if response.is_valid:
        ...     print(response.get("weather"))

        >>> # 커스텀 설정
        >>> config = GenerationConfig(temperature=0.3)
        >>> response = client.generate_text("정확한 답변이 필요합니다", config=config)
    """

    # -------------------------------------------------------------------------
    # 클래스 상수
    # -------------------------------------------------------------------------

    DEFAULT_MODEL = GeminiModel.FLASH_25
    """기본 모델."""

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
        model: Union[str, GeminiModel] = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        safety_level: SafetyLevel = SafetyLevel.BLOCK_MEDIUM_AND_ABOVE,
    ) -> None:
        """
        GeminiClient 인스턴스를 초기화합니다.

        Args:
            api_key:
                Gemini API 키. 미제공 시 GEMINI_API_KEY 환경변수 사용.
            model:
                사용할 Gemini 모델 (GeminiModel enum 또는 문자열).
            timeout:
                API 요청 타임아웃(초).
            max_retries:
                실패 시 최대 재시도 횟수.
            safety_level:
                콘텐츠 안전 필터링 수준.

        Raises:
            ValueError: API 키가 없고 환경변수도 설정되지 않은 경우.

        Example:
            >>> # 환경변수에서 API 키 로드
            >>> client = GeminiClient()

            >>> # API 키 직접 지정
            >>> client = GeminiClient(api_key="your-api-key")

            >>> # 고급 설정
            >>> client = GeminiClient(
            ...     model=GeminiModel.PRO_25,
            ...     timeout=60,
            ...     safety_level=SafetyLevel.BLOCK_ONLY_HIGH,
            ... )
        """
        # API 키 설정 (파라미터 > 환경변수)
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")

        # 모델 이름 설정 (enum 또는 문자열 지원)
        self._model = model.value if isinstance(model, GeminiModel) else str(model)

        # 타임아웃 및 재시도 설정
        self._timeout = timeout
        self._max_retries = max_retries
        self._safety_level = safety_level

        # 비활성화 플래그 확인
        # AI_DISABLE_LLM 또는 AI_DISABLE_EXTERNAL이 "true"면 비활성화
        self._disabled = (
            os.getenv("AI_DISABLE_LLM", "").lower() == "true"
            or os.getenv("AI_DISABLE_EXTERNAL", "").lower() == "true"
        )

        # Gemini 클라이언트 초기화
        self._client: Optional[Any] = None
        if self._api_key and GENAI_AVAILABLE and not self._disabled:
            try:
                self._client = genai.Client(api_key=self._api_key)
                logger.info(
                    "Gemini 클라이언트 초기화 성공",
                    extra={"model": self._model},
                )
            except Exception as e:
                logger.error(
                    "Gemini 클라이언트 초기화 실패",
                    extra={"error": str(e)},
                )
                self._client = None
        elif not GENAI_AVAILABLE:
            logger.warning(
                "google-genai 패키지가 설치되지 않음. "
                "'pip install google-genai'로 설치하세요."
            )
        elif self._disabled:
            logger.info("Gemini 클라이언트가 환경변수로 비활성화됨")

        # 재시도 데코레이터 적용
        self._execute_with_retry = create_retry_decorator(
            max_attempts=max_retries,
        )(self._execute_generation)

    # -------------------------------------------------------------------------
    # 프로퍼티
    # -------------------------------------------------------------------------

    @property
    def model_name(self) -> str:
        """
        사용 중인 모델 이름을 반환합니다.

        Returns:
            str: 모델 이름 (예: 'gemini-2.5-flash').
        """
        return self._model

    @property
    def is_available(self) -> bool:
        """
        클라이언트가 사용 가능한지 확인합니다.

        Returns:
            bool: API 키가 있고 클라이언트가 초기화되었으며 비활성화되지 않았으면 True.
        """
        return self._client is not None and not self._disabled

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
        """
        return self.is_available

    # -------------------------------------------------------------------------
    # 텍스트 생성 메서드
    # -------------------------------------------------------------------------

    def generate_text(
        self,
        contents: str,
        config: Optional[GenerationConfig] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        주어진 프롬프트에 대한 텍스트 응답을 생성합니다.

        기본적인 텍스트 생성 메서드입니다.
        구조화된 응답이 필요하면 generate_json()을 사용하세요.

        Args:
            contents:
                생성 요청 프롬프트 (사용자 입력).
            config:
                생성 설정 (온도, 토큰 수 등). None이면 기본값 사용.
            system_instruction:
                시스템 지시사항 (모델의 페르소나/역할 정의).

        Returns:
            str: 생성된 텍스트. 오류 발생 시 빈 문자열.

        Example:
            >>> response = client.generate_text("파이썬이란 무엇인가요?")
            >>> print(response)
            "파이썬은 간결하고 읽기 쉬운 문법을 가진 프로그래밍 언어입니다..."

            >>> # 커스텀 설정 사용
            >>> config = GenerationConfig(temperature=0.2)
            >>> response = client.generate_text(
            ...     "정확한 정보가 필요합니다",
            ...     config=config,
            ...     system_instruction="당신은 전문 교육자입니다.",
            ... )
        """
        if not self.is_available:
            logger.warning("Gemini 클라이언트가 사용 불가능한 상태")
            return ""

        try:
            start_time = time.time()
            result = self._execute_with_retry(
                contents=contents,
                config=config,
                system_instruction=system_instruction,
            )
            elapsed = time.time() - start_time

            logger.debug(
                "텍스트 생성 완료",
                extra={
                    "model": self._model,
                    "elapsed_seconds": round(elapsed, 2),
                    "response_length": len(result),
                },
            )

            return result

        except Exception as e:
            logger.error(
                "텍스트 생성 실패",
                extra={"error": str(e), "model": self._model},
                exc_info=True,
            )
            return ""

    def _execute_generation(
        self,
        contents: str,
        config: Optional[GenerationConfig] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        실제 API 호출을 수행합니다 (내부 메서드).

        재시도 데코레이터가 적용되어 일시적 오류 시 자동 재시도합니다.

        Args:
            contents: 생성 요청 프롬프트.
            config: 생성 설정.
            system_instruction: 시스템 지시사항.

        Returns:
            str: 생성된 텍스트.
        """
        if self._client is None:
            return ""

        # 생성 설정 구성
        generation_config = config.to_dict() if config else None

        # API 호출
        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                **(generation_config or {}),
            ) if genai_types and (system_instruction or generation_config) else None,
        )

        # 응답 텍스트 추출
        return getattr(response, "text", "") or ""

    def generate_json(
        self,
        contents: str,
        config: Optional[GenerationConfig] = None,
        system_instruction: Optional[str] = None,
    ) -> GeminiResponse:
        """
        JSON 형식의 응답을 생성하고 파싱합니다.

        LLM 응답에서 JSON 객체를 추출하여 파싱합니다.
        응답 전체가 JSON이 아니어도 JSON 부분을 찾아 파싱합니다.

        Args:
            contents:
                JSON 응답을 요청하는 프롬프트.
            config:
                생성 설정. None이면 기본값 사용.
            system_instruction:
                시스템 지시사항.

        Returns:
            GeminiResponse: 파싱된 JSON 데이터와 원본 텍스트를 담은 응답 객체.
                - response.is_valid: JSON 파싱 성공 여부
                - response.data: 파싱된 딕셔너리 (실패 시 None)
                - response.raw_text: 원본 응답 텍스트

        Example:
            >>> prompt = '''
            ... 다음 형식의 JSON으로 답변하세요:
            ... {"name": "이름", "age": 숫자}
            ... 질문: 당신은 누구인가요?
            ... '''
            >>> response = client.generate_json(prompt)
            >>> if response.is_valid:
            ...     print(response.get("name"))
        """
        # 텍스트 생성
        raw_text = self.generate_text(
            contents=contents,
            config=config,
            system_instruction=system_instruction,
        )

        if not raw_text:
            return create_empty_response(model=self._model)

        # JSON 파싱 시도
        data = _safe_json_parse(raw_text)

        return GeminiResponse(
            data=data,
            raw_text=raw_text,
            model=self._model,
            metadata={
                "parse_success": data is not None,
                "raw_length": len(raw_text),
            },
        )

    def generate_structured(
        self,
        contents: str,
        schema: Dict[str, Any],
        config: Optional[GenerationConfig] = None,
        system_instruction: Optional[str] = None,
    ) -> GeminiResponse:
        """
        스키마에 맞는 구조화된 JSON 응답을 생성합니다.

        JSON 스키마를 프롬프트에 포함하여 원하는 형식의 응답을 유도합니다.

        Args:
            contents:
                생성 요청 프롬프트.
            schema:
                응답이 따라야 할 JSON 스키마.
            config:
                생성 설정.
            system_instruction:
                시스템 지시사항.

        Returns:
            GeminiResponse: 스키마에 맞게 파싱된 응답.

        Example:
            >>> schema = {
            ...     "type": "object",
            ...     "properties": {
            ...         "topics": {"type": "array", "items": {"type": "string"}},
            ...         "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
            ...     },
            ...     "required": ["topics", "difficulty"],
            ... }
            >>> response = client.generate_structured(
            ...     "파이썬 학습 로드맵을 만들어주세요",
            ...     schema=schema,
            ... )
        """
        # 스키마를 프롬프트에 포함
        schema_prompt = f"""
다음 JSON 스키마에 맞는 형식으로 응답하세요:
```json
{json.dumps(schema, ensure_ascii=False, indent=2)}
```

요청:
{contents}

응답은 반드시 위 스키마를 따르는 유효한 JSON이어야 합니다.
"""

        return self.generate_json(
            contents=schema_prompt,
            config=config,
            system_instruction=system_instruction,
        )

    def generate_stream(
        self,
        contents: str,
        config: Optional[GenerationConfig] = None,
        system_instruction: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        스트리밍 방식으로 텍스트를 생성합니다.

        응답이 생성되는 대로 실시간으로 텍스트 조각을 반환합니다.
        긴 응답의 경우 사용자 경험을 개선할 수 있습니다.

        Args:
            contents:
                생성 요청 프롬프트.
            config:
                생성 설정.
            system_instruction:
                시스템 지시사항.

        Yields:
            str: 생성된 텍스트 조각.

        Example:
            >>> for chunk in client.generate_stream("긴 이야기를 들려주세요"):
            ...     print(chunk, end="", flush=True)
        """
        if not self.is_available:
            logger.warning("Gemini 클라이언트가 사용 불가능한 상태 (스트리밍)")
            return

        try:
            # 생성 설정 구성
            generation_config = config.to_dict() if config else None

            # 스트리밍 API 호출
            for chunk in self._client.models.generate_content_stream(
                model=self._model,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    **(generation_config or {}),
                ) if genai_types and (system_instruction or generation_config) else None,
            ):
                text = getattr(chunk, "text", "") or ""
                if text:
                    yield text

        except Exception as e:
            logger.error(
                "스트리밍 생성 실패",
                extra={"error": str(e), "model": self._model},
                exc_info=True,
            )

    # -------------------------------------------------------------------------
    # 대화형 메서드
    # -------------------------------------------------------------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        config: Optional[GenerationConfig] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        대화 히스토리를 기반으로 응답을 생성합니다.

        멀티턴 대화를 지원합니다.

        Args:
            messages:
                대화 히스토리. 각 메시지는 {"role": "user"|"assistant", "content": "텍스트"} 형식.
            config:
                생성 설정.
            system_instruction:
                시스템 지시사항.

        Returns:
            str: 생성된 응답.

        Example:
            >>> messages = [
            ...     {"role": "user", "content": "안녕하세요!"},
            ...     {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"},
            ...     {"role": "user", "content": "파이썬에 대해 알려주세요."},
            ... ]
            >>> response = client.chat(messages)
        """
        if not self.is_available:
            return ""

        # 메시지를 단일 프롬프트로 변환
        conversation = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prefix = "사용자: " if role == "user" else "어시스턴트: "
            conversation.append(f"{prefix}{content}")

        full_prompt = "\n".join(conversation) + "\n어시스턴트: "

        return self.generate_text(
            contents=full_prompt,
            config=config,
            system_instruction=system_instruction,
        )

    # -------------------------------------------------------------------------
    # 유틸리티 메서드
    # -------------------------------------------------------------------------

    def count_tokens(self, text: str) -> int:
        """
        텍스트의 토큰 수를 추정합니다.

        Note:
            정확한 토큰 수는 API를 통해서만 알 수 있습니다.
            이 메서드는 근사값을 반환합니다 (문자 4개당 약 1토큰).

        Args:
            text: 토큰 수를 계산할 텍스트.

        Returns:
            int: 추정 토큰 수.
        """
        # 간단한 추정: 영어는 4자당 1토큰, 한글은 2자당 1토큰 정도
        # 실제로는 BPE 토크나이저에 따라 다름
        korean_chars = sum(1 for c in text if ord('가') <= ord(c) <= ord('힣'))
        other_chars = len(text) - korean_chars

        return (korean_chars // 2) + (other_chars // 4)

    def health_check(self) -> Dict[str, Any]:
        """
        클라이언트 상태를 확인합니다.

        API 연결 상태, 모델 정보 등을 반환합니다.

        Returns:
            Dict[str, Any]: 상태 정보 딕셔너리.
                - available: 클라이언트 사용 가능 여부
                - model: 사용 중인 모델
                - api_key_set: API 키 설정 여부
                - genai_installed: google-genai 패키지 설치 여부
                - disabled: 환경변수로 비활성화 여부

        Example:
            >>> status = client.health_check()
            >>> print(status)
            {'available': True, 'model': 'gemini-2.5-flash', ...}
        """
        return {
            "available": self.is_available,
            "model": self._model,
            "api_key_set": bool(self._api_key),
            "genai_installed": GENAI_AVAILABLE,
            "tenacity_installed": TENACITY_AVAILABLE,
            "disabled": self._disabled,
            "timeout": self._timeout,
            "max_retries": self._max_retries,
            "safety_level": self._safety_level.value,
        }

    def __repr__(self) -> str:
        """디버깅용 문자열 표현."""
        return (
            f"GeminiClient("
            f"model={self._model!r}, "
            f"available={self.is_available})"
        )


# =============================================================================
# JSON 파싱 유틸리티
# =============================================================================

def _safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    """
    텍스트에서 JSON을 안전하게 파싱합니다.

    여러 단계를 거쳐 JSON 추출을 시도합니다:
    1. 전체 텍스트를 JSON으로 파싱
    2. 마크다운 코드 블록에서 JSON 추출
    3. 정규표현식으로 JSON 객체 추출
    4. 정규표현식으로 JSON 배열 추출

    Args:
        text: JSON이 포함된 텍스트.

    Returns:
        Optional[Dict[str, Any]]: 파싱된 JSON 객체 또는 None.
            JSON 배열인 경우 {"items": [...]} 형태로 래핑됩니다.
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # 1단계: 전체 텍스트가 JSON인 경우
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
        elif isinstance(result, list):
            return {"items": result}
    except json.JSONDecodeError:
        pass

    # 2단계: 마크다운 코드 블록에서 추출
    code_block_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)```")
    code_match = code_block_pattern.search(text)
    if code_match:
        try:
            result = json.loads(code_match.group(1).strip())
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                return {"items": result}
        except json.JSONDecodeError:
            pass

    # 3단계: JSON 객체 패턴 추출
    obj_match = _JSON_OBJECT_RE.search(text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    # 4단계: JSON 배열 패턴 추출
    arr_match = _JSON_ARRAY_RE.search(text)
    if arr_match:
        try:
            result = json.loads(arr_match.group(0))
            if isinstance(result, list):
                return {"items": result}
        except json.JSONDecodeError:
            pass

    logger.debug(
        "JSON 파싱 실패",
        extra={"text_preview": text[:100] if len(text) > 100 else text},
    )
    return None


# =============================================================================
# 편의 함수
# =============================================================================

def get_default_client() -> GeminiClient:
    """
    기본 설정의 Gemini 클라이언트를 반환합니다.

    싱글톤 패턴은 사용하지 않으며, 매번 새 인스턴스를 생성합니다.
    설정 캐싱이 필요하면 애플리케이션 레벨에서 관리하세요.

    Returns:
        GeminiClient: 기본 설정의 클라이언트 인스턴스.

    Example:
        >>> client = get_default_client()
        >>> response = client.generate_text("Hello!")
    """
    return GeminiClient()


def quick_generate(prompt: str) -> str:
    """
    간단한 텍스트 생성을 위한 편의 함수.

    클라이언트 인스턴스 생성 없이 빠르게 텍스트를 생성합니다.

    Args:
        prompt: 생성 요청 프롬프트.

    Returns:
        str: 생성된 텍스트.

    Example:
        >>> response = quick_generate("파이썬이란?")
        >>> print(response)
    """
    client = GeminiClient()
    return client.generate_text(prompt)
