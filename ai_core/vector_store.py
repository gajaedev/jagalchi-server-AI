from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .text_utils import cosine_similarity


@dataclass
class VectorItem:
    item_id: str
    vector: List[float]
    metadata: Dict[str, Any]


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, item_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def batch_upsert(self, items: List[VectorItem]) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(self, vector: List[float], top_k: int, filters: Optional[Dict[str, Any]] = None) -> List[VectorItem]:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._items: Dict[str, VectorItem] = {}

    def upsert(self, item_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        self._items[item_id] = VectorItem(item_id=item_id, vector=vector, metadata=metadata)

    def batch_upsert(self, items: List[VectorItem]) -> None:
        for item in items:
            self._items[item.item_id] = item

    def query(self, vector: List[float], top_k: int, filters: Optional[Dict[str, Any]] = None) -> List[VectorItem]:
        scored: List[tuple[float, VectorItem]] = []
        for item in self._items.values():
            if filters and not _match_filters(item.metadata, filters):
                continue
            score = cosine_similarity(vector, item.vector)
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:top_k]]


def _match_filters(metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    for key, value in filters.items():
        if metadata.get(key) != value:
            return False
    return True
