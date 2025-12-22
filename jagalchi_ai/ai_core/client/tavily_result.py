"""
=============================================================================
Tavily 검색 결과 모델
=============================================================================

이 모듈은 Tavily API의 검색 결과를 구조화된 형태로 정의합니다.
Pydantic을 사용하여 데이터 유효성을 검사하고 타입 안정성을 보장합니다.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class TavilyResult(BaseModel):
    """
    Tavily 검색 결과를 나타내는 데이터 모델.

    검색 결과의 핵심 정보(제목, URL, 내용 등)를 캡슐화합니다.
    Pydantic을 사용하여 데이터 타입을 검증합니다.

    Attributes:
        title (str): 웹 페이지 제목. 없을 경우 URL로 대체될 수 있음.
        url (str): 웹 페이지 URL.
        content (str): 웹 페이지 내용 요약 또는 스니펫.
        score (float): 검색 결과의 관련성 점수 (0.0 ~ 1.0).
        published_date (Optional[str]): 기사 발행일 (뉴스 검색 시 주로 제공됨).
    """

    title: str = Field(..., description="웹 페이지 제목")
    url: str = Field(..., description="웹 페이지 URL")
    content: str = Field(..., description="웹 페이지 내용 요약")
    score: float = Field(..., ge=0.0, le=1.0, description="관련성 점수 (0.0-1.0)")
    published_date: Optional[str] = Field(None, description="발행일")

    class Config:
        """Pydantic 설정."""
        frozen = True  # 불변 객체로 설정 (해시 가능)
        extra = "ignore"  # 정의되지 않은 필드는 무시