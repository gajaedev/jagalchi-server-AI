from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.common.nlp.text_utils import tokenize
from jagalchi_ai.ai_core.domain.roadmap import Roadmap
from jagalchi_ai.ai_core.repository.mock_data import TECH_STACKS
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore


class TechFingerprintService:
    """로드맵 기술 지문 자동 태깅 서비스."""

    def __init__(self, snapshot_store: Optional[SnapshotStore] = None) -> None:
        """
        기술 지문 서비스 초기화를 수행합니다.

        @param {Optional[SnapshotStore]} snapshot_store - 스냅샷 저장소.
        @returns {None} 저장소를 설정합니다.
        """
        self.snapshot_store = snapshot_store or SnapshotStore()

    def generate(self, roadmap: Roadmap, include_rationale: bool = False) -> Dict[str, object]:
        """
        로드맵 텍스트에서 태그 지문을 생성합니다.

        @param {Roadmap} roadmap - 로드맵 객체.
        @param {bool} include_rationale - 태그 근거 포함 여부.
        @returns {Dict[str, object]} 태그 지문 페이로드.
        """
        text_payload = self._roadmap_text(roadmap)
        cache_key = stable_hash_json({"roadmap": roadmap.roadmap_id, "text": text_payload})

        snapshot = self.snapshot_store.get_or_create(
            cache_key,
            version="tagger_v1",
            builder=lambda: self._build_payload(roadmap, text_payload, include_rationale),
            metadata={"roadmap_id": roadmap.roadmap_id},
        )
        return snapshot.payload

    def _build_payload(self, roadmap: Roadmap, text_payload: str, include_rationale: bool) -> Dict[str, object]:
        """
        태그 지문 페이로드를 구성합니다.

        @param {Roadmap} roadmap - 로드맵 객체.
        @param {str} text_payload - 로드맵 텍스트.
        @param {bool} include_rationale - 근거 포함 여부.
        @returns {Dict[str, object]} 태그 지문 페이로드.
        """
        tokens = tokenize(text_payload)
        tags = []
        for tech in TECH_STACKS.values():
            count = sum(tokens.count(alias.lower()) for alias in tech.aliases)
            if count == 0:
                continue
            tag_type = _infer_tag_type(text_payload, tech.aliases)
            confidence = min(0.5 + (count / max(len(tokens), 1)), 1.0)
            tag_payload = {
                "tech_slug": tech.slug,
                "type": tag_type,
                "confidence": round(confidence, 2),
            }
            if include_rationale:
                tag_payload["rationale"] = f"로드맵 본문에서 {tech.display_name} 관련 표현이 반복된다"
            tags.append(tag_payload)

        payload = {
            "roadmap_id": roadmap.roadmap_id,
            "tags": tags,
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": "tagger_v1",
        }
        return payload

    def _roadmap_text(self, roadmap: Roadmap) -> str:
        """
        로드맵의 핵심 텍스트를 조합합니다.

        @param {Roadmap} roadmap - 로드맵 객체.
        @returns {str} 결합된 텍스트.
        """
        node_text = " ".join([node.title + " " + node.description for node in roadmap.nodes])
        return " ".join([roadmap.title, roadmap.description, node_text, " ".join(roadmap.tags)])


def _infer_tag_type(text: str, aliases: List[str]) -> str:
    """
    텍스트에서 태그 타입을 추론합니다.

    @param {str} text - 입력 텍스트.
    @param {List[str]} aliases - 기술 별칭 목록.
    @returns {str} 태그 타입.
    """
    lowered = text.lower()
    for alias in aliases:
        if f"{alias} deprecated" in lowered or "deprecated" in lowered or "legacy" in lowered:
            return "deprecated"
        if f"{alias} 대안" in lowered or "alternative" in lowered:
            return "alternative"
    if any(alias in lowered for alias in aliases):
        if len(aliases) > 1 and aliases[0] in lowered:
            return "core"
    return "optional"
