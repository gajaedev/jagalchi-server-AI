from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from jagalchi_ai.ai_core.repository.snapshot import Snapshot


class SnapshotStore:
    """스냅샷 캐시 저장소."""

    def __init__(self) -> None:
        self._store: Dict[str, Snapshot] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Snapshot]:
        snapshot = self._store.get(key)
        if snapshot:
            self.hits += 1
        else:
            self.misses += 1
        return snapshot

    def put(self, key: str, payload: Dict[str, Any], version: str, metadata: Optional[Dict[str, Any]] = None) -> Snapshot:
        snapshot = Snapshot(
            key=key,
            payload=payload,
            version=version,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )
        self._store[key] = snapshot
        return snapshot

    def get_or_create(
        self,
        key: str,
        version: str,
        builder: Callable[[], Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Snapshot:
        cached = self.get(key)
        if cached:
            return cached
        payload = builder()
        return self.put(key, payload, version, metadata=metadata)

    def size(self) -> int:
        return len(self._store)
