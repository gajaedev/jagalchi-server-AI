# =============================================================================
# Gemini 응답 데이터 모델
# =============================================================================
# Google Gemini API 응답을 구조화하여 관리하는 데이터 클래스입니다.
# JSON 파싱 결과와 원본 텍스트를 함께 보관하여 디버깅과 후처리를 용이하게 합니다.
#
# 주요 기능:
#   - 파싱된 JSON 데이터 저장
#   - 원본 응답 텍스트 보관
#   - 응답 유효성 검사 유틸리티
#   - 안전한 데이터 접근 메서드
#
# 사용 예시:
#   response = gemini_client.generate_json(prompt)
#   if response.is_valid:
#       data = response.get("key", default_value)
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


@dataclass
class GeminiResponse:
    """
    Google Gemini API 응답 래퍼 클래스.

    Gemini API의 응답을 구조화하여 관리합니다.
    JSON 파싱 결과와 원본 텍스트를 함께 보관하여 디버깅과 후처리를 용이하게 합니다.

    Attributes:
        data (Optional[Dict[str, Any]]):
            파싱된 JSON 데이터. 파싱 실패 시 None.
        raw_text (str):
            Gemini API로부터 받은 원본 텍스트 응답.
        created_at (datetime):
            응답 생성 시각 (자동 설정).
        model (Optional[str]):
            응답을 생성한 모델 이름.
        metadata (Dict[str, Any]):
            추가 메타데이터 (토큰 수, 처리 시간 등).

    Example:
        >>> response = GeminiResponse(data={"answer": "Hello"}, raw_text='{"answer": "Hello"}')
        >>> response.is_valid
        True
        >>> response.get("answer")
        'Hello'
        >>> response.get("missing", "default")
        'default'
    """

    # -------------------------------------------------------------------------
    # 핵심 필드
    # -------------------------------------------------------------------------

    data: Optional[Dict[str, Any]]
    """파싱된 JSON 데이터. 파싱 실패 시 None."""

    raw_text: str
    """Gemini API로부터 받은 원본 텍스트 응답."""

    # -------------------------------------------------------------------------
    # 메타데이터 필드
    # -------------------------------------------------------------------------

    created_at: datetime = field(default_factory=datetime.now)
    """응답 생성 시각."""

    model: Optional[str] = None
    """응답을 생성한 모델 이름 (예: 'gemini-2.5-flash')."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """추가 메타데이터 (토큰 수, 처리 시간 등)."""

    # -------------------------------------------------------------------------
    # 프로퍼티
    # -------------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        """
        응답이 유효한지 확인합니다.

        data가 None이 아니고, 비어있지 않은 딕셔너리인 경우 유효합니다.

        Returns:
            bool: 응답이 유효하면 True, 그렇지 않으면 False.

        Example:
            >>> response = GeminiResponse(data={"key": "value"}, raw_text="...")
            >>> response.is_valid
            True
            >>> response = GeminiResponse(data=None, raw_text="")
            >>> response.is_valid
            False
        """
        return self.data is not None and len(self.data) > 0

    @property
    def is_empty(self) -> bool:
        """
        응답이 비어있는지 확인합니다.

        Returns:
            bool: data가 None이거나 raw_text가 비어있으면 True.
        """
        return self.data is None or not self.raw_text.strip()

    @property
    def text_length(self) -> int:
        """
        원본 텍스트의 길이를 반환합니다.

        Returns:
            int: raw_text의 문자 수.
        """
        return len(self.raw_text)

    # -------------------------------------------------------------------------
    # 데이터 접근 메서드
    # -------------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """
        딕셔너리에서 안전하게 값을 가져옵니다.

        data가 None이거나 키가 없는 경우 기본값을 반환합니다.

        Args:
            key: 가져올 키.
            default: 키가 없을 때 반환할 기본값.

        Returns:
            Any: 해당 키의 값 또는 기본값.

        Example:
            >>> response.get("answer", "No answer found")
            'Hello World'
        """
        if self.data is None:
            return default
        return self.data.get(key, default)

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """
        중첩된 딕셔너리에서 안전하게 값을 가져옵니다.

        여러 단계의 키를 순차적으로 탐색하여 값을 반환합니다.

        Args:
            *keys: 탐색할 키들 (순서대로).
            default: 값이 없을 때 반환할 기본값.

        Returns:
            Any: 중첩된 키의 값 또는 기본값.

        Example:
            >>> # data = {"user": {"profile": {"name": "Alice"}}}
            >>> response.get_nested("user", "profile", "name")
            'Alice'
        """
        if self.data is None:
            return default

        current = self.data
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default

        return current

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """
        딕셔너리에서 리스트 값을 안전하게 가져옵니다.

        값이 리스트가 아닌 경우 빈 리스트를 반환합니다.

        Args:
            key: 가져올 키.
            default: 기본값 (기본: 빈 리스트).

        Returns:
            List[Any]: 해당 키의 리스트 값 또는 기본값.
        """
        if default is None:
            default = []

        value = self.get(key, default)
        if isinstance(value, list):
            return value
        return default

    def get_string(self, key: str, default: str = "") -> str:
        """
        딕셔너리에서 문자열 값을 안전하게 가져옵니다.

        값이 문자열이 아닌 경우 str()로 변환합니다.

        Args:
            key: 가져올 키.
            default: 기본값 (기본: 빈 문자열).

        Returns:
            str: 해당 키의 문자열 값 또는 기본값.
        """
        value = self.get(key, default)
        if value is None:
            return default
        return str(value) if not isinstance(value, str) else value

    def get_int(self, key: str, default: int = 0) -> int:
        """
        딕셔너리에서 정수 값을 안전하게 가져옵니다.

        Args:
            key: 가져올 키.
            default: 기본값 (기본: 0).

        Returns:
            int: 해당 키의 정수 값 또는 기본값.
        """
        value = self.get(key, default)
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        딕셔너리에서 실수 값을 안전하게 가져옵니다.

        Args:
            key: 가져올 키.
            default: 기본값 (기본: 0.0).

        Returns:
            float: 해당 키의 실수 값 또는 기본값.
        """
        value = self.get(key, default)
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        딕셔너리에서 불리언 값을 안전하게 가져옵니다.

        Args:
            key: 가져올 키.
            default: 기본값 (기본: False).

        Returns:
            bool: 해당 키의 불리언 값 또는 기본값.
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "on")
        return bool(value) if value is not None else default

    # -------------------------------------------------------------------------
    # 유틸리티 메서드
    # -------------------------------------------------------------------------

    def keys(self) -> List[str]:
        """
        데이터의 모든 키를 반환합니다.

        Returns:
            List[str]: 데이터의 키 리스트 (data가 None이면 빈 리스트).
        """
        if self.data is None:
            return []
        return list(self.data.keys())

    def has_key(self, key: str) -> bool:
        """
        특정 키가 데이터에 존재하는지 확인합니다.

        Args:
            key: 확인할 키.

        Returns:
            bool: 키가 존재하면 True.
        """
        if self.data is None:
            return False
        return key in self.data

    def to_dict(self) -> Dict[str, Any]:
        """
        응답 객체를 딕셔너리로 변환합니다.

        직렬화나 로깅에 유용합니다.

        Returns:
            Dict[str, Any]: 응답 데이터를 담은 딕셔너리.
        """
        return {
            "data": self.data,
            "raw_text": self.raw_text,
            "created_at": self.created_at.isoformat(),
            "model": self.model,
            "is_valid": self.is_valid,
            "text_length": self.text_length,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        """디버깅용 문자열 표현."""
        data_preview = str(self.data)[:50] + "..." if self.data and len(str(self.data)) > 50 else str(self.data)
        return (
            f"GeminiResponse("
            f"is_valid={self.is_valid}, "
            f"model={self.model}, "
            f"data_preview={data_preview})"
        )


# =============================================================================
# 팩토리 함수
# =============================================================================

def create_empty_response(model: Optional[str] = None) -> GeminiResponse:
    """
    빈 응답 객체를 생성합니다.

    API 호출 실패나 타임아웃 시 기본 응답으로 사용합니다.

    Args:
        model: 모델 이름 (선택적).

    Returns:
        GeminiResponse: 빈 데이터를 가진 응답 객체.
    """
    return GeminiResponse(
        data=None,
        raw_text="",
        model=model,
        metadata={"error": "empty_response"},
    )


def create_error_response(
    error_message: str,
    model: Optional[str] = None,
) -> GeminiResponse:
    """
    에러 응답 객체를 생성합니다.

    예외 발생 시 에러 정보를 포함한 응답으로 사용합니다.

    Args:
        error_message: 에러 메시지.
        model: 모델 이름 (선택적).

    Returns:
        GeminiResponse: 에러 정보를 담은 응답 객체.
    """
    return GeminiResponse(
        data={"error": error_message},
        raw_text="",
        model=model,
        metadata={
            "error": True,
            "error_message": error_message,
        },
    )
