from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.client import GeminiClient
from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary, tokenize
from jagalchi_ai.ai_core.domain.roadmap import Roadmap
from jagalchi_ai.ai_core.repository.mock_data import TECH_STACKS
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore


class TechFingerprintService:
    """로드맵 기술 지문 자동 태깅 서비스."""

    def __init__(
        self,
        snapshot_store: Optional[SnapshotStore] = None,
        llm_client: Optional[GeminiClient] = None,
    ) -> None:
        """
        기술 지문 서비스 초기화를 수행합니다.

        @param {Optional[SnapshotStore]} snapshot_store - 스냅샷 저장소.
        @param {Optional[GeminiClient]} llm_client - LLM 클라이언트.
        @returns {None} 저장소를 설정합니다.
        """
        self.snapshot_store = snapshot_store or SnapshotStore()
        self._llm_client = llm_client or GeminiClient()

    def generate(self, roadmap: Roadmap, include_rationale: bool = False) -> Dict[str, object]:
        """
        로드맵 텍스트에서 태그 지문을 생성합니다.

        @param {Roadmap} roadmap - 로드맵 객체.
        @param {bool} include_rationale - 태그 근거 포함 여부.
        @returns {Dict[str, object]} 태그 지문 페이로드.
        """
        text_payload = self._roadmap_text(roadmap)
        cache_key = stable_hash_json(
            {
                "roadmap": roadmap.roadmap_id,
                "text": text_payload,
                "include_rationale": include_rationale,
            }
        )

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

        model_version = "tagger_v1"
        if include_rationale and tags:
            tags, model_version = self._apply_llm_rationales(roadmap, tags, text_payload)

        payload = {
            "roadmap_id": roadmap.roadmap_id,
            "tags": tags,
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": model_version,
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

    def _apply_llm_rationales(
        self,
        roadmap: Roadmap,
        tags: List[Dict[str, object]],
        text_payload: str,
    ) -> tuple[List[Dict[str, object]], str]:
        """
        LLM을 사용해 태그 근거를 보강합니다.

        @param {Roadmap} roadmap - 로드맵 객체.
        @param {List[Dict[str, object]]} tags - 태그 목록.
        @param {str} text_payload - 로드맵 텍스트.
        @returns {tuple[List[Dict[str, object]], str]} (태그, 모델 버전).
        """
        if not self._llm_client.available():
            return tags, "tagger_v1"

        tech_map = {tech.slug: tech.display_name for tech in TECH_STACKS.values()}
        tag_context = [
            {
                "tech_slug": tag["tech_slug"],
                "display_name": tech_map.get(tag["tech_slug"], ""),
                "type": tag.get("type", ""),
                "confidence": tag.get("confidence", 0.0),
            }
            for tag in tags
        ]
        summary = extractive_summary(text_payload, max_sentences=3)
        prompt = _build_rationale_prompt(roadmap, summary, tag_context)
        response = self._llm_client.generate_json(prompt)
        if response.data and _valid_rationale_payload(response.data):
            rationale_map = _normalize_rationale_map(response.data["rationales"])
            if rationale_map:
                for tag in tags:
                    rationale = rationale_map.get(tag["tech_slug"])
                    if rationale:
                        tag["rationale"] = rationale
                return tags, self._llm_client.model_name

        return tags, "tagger_v1"


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


def _build_rationale_prompt(roadmap: Roadmap, summary: str, tag_context: List[Dict[str, object]]) -> str:
    """
    LLM에 전달할 태그 근거 프롬프트를 생성합니다.

    @param {Roadmap} roadmap - 로드맵 객체.
    @param {str} summary - 로드맵 요약.
    @param {List[Dict[str, object]]} tag_context - 태그 후보 컨텍스트.
    @returns {str} 프롬프트 문자열.
    """
    return (
        "아래 정보를 참고해서 태그별 근거를 한 문장으로 작성해줘. "
        "반드시 JSON만 반환하고 형식은 {\"rationales\": {\"tech_slug\": \"근거\"}}로 맞춰줘.\n"
        f"roadmap_title: {roadmap.title}\n"
        f"roadmap_summary: {summary}\n"
        f"tag_candidates: {tag_context}\n"
    )


def _valid_rationale_payload(payload: Dict[str, object]) -> bool:
    """
    태그 근거 응답의 스키마를 검증합니다.

    @param {Dict[str, object]} payload - LLM 응답 데이터.
    @returns {bool} 유효성 여부.
    """
    rationales = payload.get("rationales")
    if not isinstance(rationales, dict) or not rationales:
        return False
    for key, value in rationales.items():
        if not isinstance(key, str) or not isinstance(value, str):
            return False
    return True


def _normalize_rationale_map(rationales: Dict[str, object]) -> Dict[str, str]:
    """
    태그 근거 맵을 정규화합니다.

    @param {Dict[str, object]} rationales - LLM 응답 근거 맵.
    @returns {Dict[str, str]} 정규화된 근거 맵.
    """
    cleaned: Dict[str, str] = {}
    for key, value in rationales.items():
        if isinstance(key, str) and isinstance(value, str) and value.strip():
            cleaned[key] = value.strip()
    return cleaned
