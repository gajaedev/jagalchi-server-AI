from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from jagalchi_ai.ai_core.repository.snapshot import Snapshot


class SnapshotStore:
    """스냅샷 캐시 저장소."""

    def __init__(self) -> None:
        """
        @returns None
        """
        self._store: Dict[str, Snapshot] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Snapshot]:
        """
        @param key 스냅샷 키.
        @returns 캐시된 스냅샷 또는 None.
        """
        snapshot = self._store.get(key)
        if snapshot:
            self.hits += 1
        else:
            self.misses += 1
        return snapshot

    def put(self, key: str, payload: Dict[str, Any], version: str, metadata: Optional[Dict[str, Any]] = None) -> Snapshot:
        """
        @param key 스냅샷 키.
        @param payload 저장할 결과 JSON.
        @param version 결과 버전.
        @param metadata 부가 메타데이터.
        @returns 저장된 Snapshot 객체.
        """
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
        """
        @param key 스냅샷 키.
        @param version 결과 버전.
        @param builder 캐시 미스 시 호출되는 생성 함수.
        @param metadata 부가 메타데이터.
        @returns 캐시된 또는 새로 생성된 Snapshot 객체.
        """
        cached = self.get(key)
        if cached:
            return cached
        payload = builder()
        return self.put(key, payload, version, metadata=metadata)

    def size(self) -> int:
        """
        @returns 저장된 스냅샷 개수.
        """
        return len(self._store)
