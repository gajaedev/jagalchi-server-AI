from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from jagalchi_ai.ai_core.domain.vector_item import VectorItem


class VectorStore(ABC):
    """벡터 스토어 인터페이스."""

    @abstractmethod
    def upsert(self, item_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def batch_upsert(self, items: List[VectorItem]) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(self, vector: List[float], top_k: int, filters: Optional[Dict[str, Any]] = None) -> List[VectorItem]:
        raise NotImplementedError
