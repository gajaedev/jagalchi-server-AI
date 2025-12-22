# =============================================================================
# Exa 검색 결과 데이터 모델
# =============================================================================
# Exa API 검색 결과를 구조화하여 관리하는 데이터 클래스입니다.
# 검색 결과의 메타데이터, 콘텐츠, 관련성 점수를 포함합니다.
#
# 주요 기능:
#   - 검색 결과 메타데이터 저장 (제목, URL, 날짜)
#   - 콘텐츠 및 관련성 점수 관리
#   - 결과 유효성 검사 유틸리티
#   - 다양한 출력 형식 지원 (딕셔너리, RAG 컨텍스트)
#
# 사용 예시:
#   results = exa_client.search("Python tutorial")
#   for result in results:
#       if result.is_relevant:
#           print(result.title, result.score)
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class ExaResult:
    """
    Exa 검색 결과 데이터 클래스.

    Exa API로부터 반환된 단일 검색 결과를 나타냅니다.
    제목, URL, 콘텐츠, 관련성 점수 등의 정보를 포함합니다.

    Attributes:
        title (str):
            검색 결과의 제목.
        url (str):
            검색 결과 페이지의 URL.
        content (str):
            검색 결과의 주요 텍스트 콘텐츠 (요약, 본문, 하이라이트).
        score (float):
            검색 쿼리와의 관련성 점수 (0.0 ~ 1.0, 높을수록 관련성 높음).
        published_date (Optional[str]):
            콘텐츠 발행일 (ISO 8601 형식).
        author (Optional[str]):
            콘텐츠 작성자.
        highlights (List[str]):
            검색어가 포함된 주요 문장들.
        metadata (Dict[str, Any]):
            추가 메타데이터.

    Example:
        >>> result = ExaResult(
        ...     title="Python Tutorial",
        ...     url="https://example.com/python",
        ...     content="Learn Python programming...",
        ...     score=0.95
        ... )
        >>> result.is_relevant
        True
        >>> result.domain
        'example.com'
    """

    # -------------------------------------------------------------------------
    # 핵심 필드
    # -------------------------------------------------------------------------

    title: str
    """검색 결과의 제목."""

    url: str
    """검색 결과 페이지의 URL."""

    content: str
    """검색 결과의 주요 텍스트 콘텐츠."""

    score: float
    """검색 쿼리와의 관련성 점수 (0.0 ~ 1.0)."""

    # -------------------------------------------------------------------------
    # 선택적 필드
    # -------------------------------------------------------------------------

    published_date: Optional[str] = None
    """콘텐츠 발행일 (ISO 8601 형식, 예: '2024-01-15')."""

    author: Optional[str] = None
    """콘텐츠 작성자."""

    highlights: List[str] = field(default_factory=list)
    """검색어가 포함된 주요 문장들."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """추가 메타데이터 (소스 유형, 카테고리 등)."""

    # -------------------------------------------------------------------------
    # 관련성 임계값 설정
    # -------------------------------------------------------------------------

    # 관련성 점수 임계값
    RELEVANCE_THRESHOLD_HIGH: float = 0.8
    """높은 관련성 임계값."""

    RELEVANCE_THRESHOLD_MEDIUM: float = 0.5
    """중간 관련성 임계값."""

    RELEVANCE_THRESHOLD_LOW: float = 0.3
    """낮은 관련성 임계값."""

    # -------------------------------------------------------------------------
    # 프로퍼티
    # -------------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        """
        검색 결과가 유효한지 확인합니다.

        URL과 제목이 모두 존재하는 경우 유효합니다.

        Returns:
            bool: 유효한 결과면 True.
        """
        return bool(self.url and self.title)

    @property
    def is_relevant(self) -> bool:
        """
        검색 결과가 관련성이 있는지 확인합니다.

        관련성 점수가 낮은 임계값(0.3) 이상인 경우 관련성 있음.

        Returns:
            bool: 관련성이 있으면 True.
        """
        return self.score >= self.RELEVANCE_THRESHOLD_LOW

    @property
    def is_highly_relevant(self) -> bool:
        """
        검색 결과가 높은 관련성을 가지는지 확인합니다.

        관련성 점수가 높은 임계값(0.8) 이상인 경우.

        Returns:
            bool: 높은 관련성이면 True.
        """
        return self.score >= self.RELEVANCE_THRESHOLD_HIGH

    @property
    def relevance_level(self) -> str:
        """
        관련성 수준을 문자열로 반환합니다.

        Returns:
            str: 'high', 'medium', 'low', 또는 'irrelevant'.
        """
        if self.score >= self.RELEVANCE_THRESHOLD_HIGH:
            return "high"
        elif self.score >= self.RELEVANCE_THRESHOLD_MEDIUM:
            return "medium"
        elif self.score >= self.RELEVANCE_THRESHOLD_LOW:
            return "low"
        else:
            return "irrelevant"

    @property
    def domain(self) -> str:
        """
        URL에서 도메인을 추출합니다.

        Returns:
            str: 도메인 이름 (예: 'example.com').
        """
        try:
            parsed = urlparse(self.url)
            return parsed.netloc or ""
        except Exception:
            return ""

    @property
    def has_content(self) -> bool:
        """
        콘텐츠가 존재하는지 확인합니다.

        Returns:
            bool: 콘텐츠가 비어있지 않으면 True.
        """
        return bool(self.content and self.content.strip())

    @property
    def content_length(self) -> int:
        """
        콘텐츠의 문자 수를 반환합니다.

        Returns:
            int: 콘텐츠 길이.
        """
        return len(self.content) if self.content else 0

    @property
    def content_preview(self) -> str:
        """
        콘텐츠의 미리보기 (첫 200자)를 반환합니다.

        Returns:
            str: 콘텐츠 미리보기.
        """
        if not self.content:
            return ""
        if len(self.content) <= 200:
            return self.content
        return self.content[:200] + "..."

    @property
    def has_date(self) -> bool:
        """
        발행일이 존재하는지 확인합니다.

        Returns:
            bool: 발행일이 있으면 True.
        """
        return bool(self.published_date)

    @property
    def parsed_date(self) -> Optional[datetime]:
        """
        발행일을 datetime 객체로 파싱합니다.

        Returns:
            Optional[datetime]: 파싱된 datetime 또는 None.
        """
        if not self.published_date:
            return None
        try:
            # ISO 8601 형식 파싱 시도
            return datetime.fromisoformat(self.published_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    # -------------------------------------------------------------------------
    # 변환 메서드
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        검색 결과를 딕셔너리로 변환합니다.

        직렬화나 API 응답에 사용합니다.

        Returns:
            Dict[str, Any]: 검색 결과 딕셔너리.
        """
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
            "published_date": self.published_date,
            "author": self.author,
            "highlights": self.highlights,
            "domain": self.domain,
            "relevance_level": self.relevance_level,
            "is_valid": self.is_valid,
            "content_length": self.content_length,
            "metadata": self.metadata,
        }

    def to_rag_context(self, include_metadata: bool = True) -> str:
        """
        RAG (Retrieval-Augmented Generation) 파이프라인용 컨텍스트를 생성합니다.

        LLM이 사용하기 좋은 형식으로 검색 결과를 포맷팅합니다.

        Args:
            include_metadata: 메타데이터 (URL, 날짜) 포함 여부.

        Returns:
            str: RAG용 포맷팅된 컨텍스트.

        Example:
            >>> context = result.to_rag_context()
            >>> # [제목]
            >>> # URL: https://...
            >>> # 발행일: 2024-01-15
            >>> # 내용: ...
        """
        lines = [f"[{self.title}]"]

        if include_metadata:
            lines.append(f"URL: {self.url}")
            if self.published_date:
                lines.append(f"발행일: {self.published_date}")
            if self.author:
                lines.append(f"작성자: {self.author}")
            lines.append(f"관련성: {self.score:.2f}")

        if self.content:
            lines.append(f"내용: {self.content}")

        if self.highlights:
            lines.append("주요 문장:")
            for highlight in self.highlights[:3]:  # 최대 3개
                lines.append(f"  - {highlight}")

        return "\n".join(lines)

    def to_markdown(self) -> str:
        """
        검색 결과를 Markdown 형식으로 변환합니다.

        Returns:
            str: Markdown 형식의 검색 결과.
        """
        lines = [f"### [{self.title}]({self.url})"]

        meta_parts = []
        if self.published_date:
            meta_parts.append(f"📅 {self.published_date}")
        if self.author:
            meta_parts.append(f"✍️ {self.author}")
        meta_parts.append(f"⭐ {self.score:.2f}")

        if meta_parts:
            lines.append(" | ".join(meta_parts))

        if self.content:
            lines.append("")
            lines.append(self.content_preview)

        return "\n".join(lines)

    def to_citation(self) -> str:
        """
        인용 형식으로 변환합니다.

        Returns:
            str: 인용 형식 문자열.
        """
        parts = [self.title]
        if self.author:
            parts.insert(0, self.author)
        if self.published_date:
            parts.append(f"({self.published_date})")
        parts.append(self.url)
        return ". ".join(parts)

    # -------------------------------------------------------------------------
    # 비교 및 정렬 메서드
    # -------------------------------------------------------------------------

    def __lt__(self, other: ExaResult) -> bool:
        """점수 기반 비교 (내림차순 정렬용)."""
        return self.score > other.score  # 높은 점수가 먼저 오도록

    def __eq__(self, other: object) -> bool:
        """URL 기반 동등성 비교."""
        if not isinstance(other, ExaResult):
            return NotImplemented
        return self.url == other.url

    def __hash__(self) -> int:
        """URL 기반 해시."""
        return hash(self.url)

    def __repr__(self) -> str:
        """디버깅용 문자열 표현."""
        return (
            f"ExaResult("
            f"title='{self.title[:30]}...', "
            f"score={self.score:.2f}, "
            f"domain='{self.domain}')"
        )


# =============================================================================
# 유틸리티 함수
# =============================================================================

def filter_results_by_score(
    results: List[ExaResult],
    min_score: float = 0.3,
) -> List[ExaResult]:
    """
    관련성 점수로 검색 결과를 필터링합니다.

    Args:
        results: 필터링할 검색 결과 리스트.
        min_score: 최소 관련성 점수.

    Returns:
        List[ExaResult]: 필터링된 검색 결과 리스트.
    """
    return [r for r in results if r.score >= min_score]


def filter_results_by_domain(
    results: List[ExaResult],
    allowed_domains: Optional[List[str]] = None,
    blocked_domains: Optional[List[str]] = None,
) -> List[ExaResult]:
    """
    도메인으로 검색 결과를 필터링합니다.

    Args:
        results: 필터링할 검색 결과 리스트.
        allowed_domains: 허용할 도메인 리스트 (설정 시 해당 도메인만 포함).
        blocked_domains: 차단할 도메인 리스트.

    Returns:
        List[ExaResult]: 필터링된 검색 결과 리스트.
    """
    filtered = results

    if allowed_domains:
        filtered = [
            r for r in filtered
            if any(d.lower() in r.domain.lower() for d in allowed_domains)
        ]

    if blocked_domains:
        filtered = [
            r for r in filtered
            if not any(d.lower() in r.domain.lower() for d in blocked_domains)
        ]

    return filtered


def deduplicate_results(results: List[ExaResult]) -> List[ExaResult]:
    """
    중복 검색 결과를 제거합니다.

    URL을 기준으로 중복을 제거하며, 점수가 높은 결과를 유지합니다.

    Args:
        results: 중복 제거할 검색 결과 리스트.

    Returns:
        List[ExaResult]: 중복이 제거된 검색 결과 리스트.
    """
    seen: Dict[str, ExaResult] = {}

    for result in results:
        url = result.url.lower().rstrip("/")
        if url not in seen or result.score > seen[url].score:
            seen[url] = result

    return list(seen.values())


def sort_results(
    results: List[ExaResult],
    by: str = "score",
    descending: bool = True,
) -> List[ExaResult]:
    """
    검색 결과를 정렬합니다.

    Args:
        results: 정렬할 검색 결과 리스트.
        by: 정렬 기준 ('score', 'date', 'title').
        descending: 내림차순 여부.

    Returns:
        List[ExaResult]: 정렬된 검색 결과 리스트.
    """
    if by == "score":
        key_func = lambda r: r.score
    elif by == "date":
        key_func = lambda r: r.published_date or ""
    elif by == "title":
        key_func = lambda r: r.title.lower()
    else:
        key_func = lambda r: r.score

    return sorted(results, key=key_func, reverse=descending)


def results_to_context(
    results: List[ExaResult],
    max_results: int = 5,
    max_tokens: int = 4000,
) -> str:
    """
    검색 결과들을 RAG 컨텍스트로 변환합니다.

    Args:
        results: 변환할 검색 결과 리스트.
        max_results: 포함할 최대 결과 수.
        max_tokens: 대략적인 최대 토큰 수 (문자 수 / 4로 추정).

    Returns:
        str: RAG용 통합 컨텍스트.
    """
    contexts = []
    total_chars = 0
    max_chars = max_tokens * 4  # 대략적인 토큰-문자 비율

    for result in results[:max_results]:
        context = result.to_rag_context()
        if total_chars + len(context) > max_chars:
            break
        contexts.append(context)
        total_chars += len(context)

    return "\n\n---\n\n".join(contexts)
