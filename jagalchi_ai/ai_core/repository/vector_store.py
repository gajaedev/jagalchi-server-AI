from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from jagalchi_ai.ai_core.domain.vector_item import VectorItem


class VectorStore(ABC):
    """벡터 스토어 인터페이스."""

    @abstractmethod
    def upsert(self, item_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        """
        @param item_id 벡터 아이템 ID.
        @param vector 벡터 값.
        @param metadata 부가 메타데이터.
        @returns None
        """
        raise NotImplementedError

    @abstractmethod
    def batch_upsert(self, items: List[VectorItem]) -> None:
        """
        @param items 벡터 아이템 리스트.
        @returns None
        """
        raise NotImplementedError

    @abstractmethod
    def query(self, vector: List[float], top_k: int, filters: Optional[Dict[str, Any]] = None) -> List[VectorItem]:
        """
        @param vector 검색 벡터.
        @param top_k 상위 결과 수.
        @param filters 메타데이터 필터 조건.
        @returns 상위 벡터 아이템 리스트.
        """
        raise NotImplementedError
