from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from .hashing import stable_hash_json
from dataclasses import dataclass

from .snapshot import SnapshotStore
from .text_utils import cheap_embed, extractive_summary
from .mock_data import COMMON_PITFALLS, TECH_SOURCES
from .vector_store import InMemoryVectorStore, VectorItem


_ALTERNATIVE_MAP = {
    "react": [
        {"slug": "vue", "why": "학습 난이도가 낮고 템플릿 기반 개발을 선호할 때"},
    ],
    "django": [
        {"slug": "fastapi", "why": "가볍고 빠른 API 서버가 필요할 때"},
    ],
}


@dataclass
class SourceChunk:
    chunk_id: str
    text: str
    metadata: Dict[str, str]


class TechCardService:
    def __init__(self, snapshot_store: Optional[SnapshotStore] = None) -> None:
        self.snapshot_store = snapshot_store or SnapshotStore()

    def get_or_create(self, tech_slug: str, prompt_version: str = "tech_card_v1") -> Dict[str, object]:
        sources = TECH_SOURCES.get(tech_slug, [])
        source_hash = stable_hash_json({"slug": tech_slug, "sources": sources})
        snapshot = self.snapshot_store.get_or_create(
            source_hash,
            version=prompt_version,
            builder=lambda: self._compose_card(tech_slug, sources, prompt_version),
            metadata={"tech_slug": tech_slug},
        )
        return snapshot.payload

    def _compose_card(self, tech_slug: str, sources: List[Dict[str, str]], prompt_version: str) -> Dict[str, object]:
        merged = " ".join(source["content"] for source in sources)
        chunks = self._chunk_sources(tech_slug, sources)
        _ = self._index_chunks(chunks)
        summary = extractive_summary(merged, max_sentences=2)
        pitfalls = COMMON_PITFALLS.get(tech_slug, [])

        payload = {
            "tech_slug": tech_slug,
            "version": datetime.utcnow().date().isoformat(),
            "summary": summary,
            "why_it_matters": [
                "업계 표준에 가까운 사용 사례를 확보할 수 있다",
                "팀 협업과 유지보수에 필요한 패턴을 제공한다",
            ],
            "when_to_use": [
                "UI/서비스의 구조를 빠르게 확장해야 할 때",
                "문서와 커뮤니티 리소스가 풍부한 기술을 원할 때",
            ],
            "alternatives": _ALTERNATIVE_MAP.get(tech_slug, []),
            "pitfalls": pitfalls,
            "learning_path": [
                {"stage": "basic", "items": ["핵심 개념 이해", "기본 예제 구현"]},
                {"stage": "practice", "items": ["작은 기능 단위 프로젝트", "성능/품질 개선"]},
            ],
            "sources": [
                {"title": source["title"], "url": source["url"], "fetched_at": source["fetched_at"]}
                for source in sources
            ],
            "generated_by": {
                "model_version": "compose_v1",
                "prompt_version": prompt_version,
            },
        }
        return payload

    def _chunk_sources(self, tech_slug: str, sources: List[Dict[str, str]], chunk_size: int = 120) -> List[SourceChunk]:
        chunks: List[SourceChunk] = []
        for idx, source in enumerate(sources):
            words = source["content"].split()
            for chunk_idx in range(0, len(words), chunk_size):
                text = " ".join(words[chunk_idx : chunk_idx + chunk_size])
                chunk_id = f"{tech_slug}:{idx}:{chunk_idx}"
                chunks.append(
                    SourceChunk(
                        chunk_id=chunk_id,
                        text=text,
                        metadata={"source": "tech_card", "tech_slug": tech_slug, "snippet": extractive_summary(text)},
                    )
                )
        return chunks

    def _index_chunks(self, chunks: List[SourceChunk]) -> InMemoryVectorStore:
        store = InMemoryVectorStore()
        items = [
            VectorItem(item_id=chunk.chunk_id, vector=cheap_embed(chunk.text), metadata=chunk.metadata)
            for chunk in chunks
        ]
        store.batch_upsert(items)
        return store
