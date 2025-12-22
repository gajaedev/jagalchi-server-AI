from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.client import GeminiClient
from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary, tokenize
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore
from jagalchi_ai.ai_core.service.graph.graph_rag import GraphRAGService


class RoadmapGeneratorService:
    """GraphRAG 기반 로드맵 생성 서비스."""
    def __init__(
        self,
        graph_rag: Optional[GraphRAGService] = None,
        snapshot_store: Optional[SnapshotStore] = None,
        llm_client: Optional[GeminiClient] = None,
    ) -> None:
        """
        로드맵 생성에 필요한 의존성을 초기화합니다.

        @param {Optional[GraphRAGService]} graph_rag - 그래프 RAG 서비스.
        @param {Optional[SnapshotStore]} snapshot_store - 스냅샷 저장소.
        @param {Optional[GeminiClient]} llm_client - LLM 클라이언트.
        @returns {None} 내부 상태를 구성합니다.
        """
        self._graph_rag = graph_rag or GraphRAGService()
        self._snapshot_store = snapshot_store or SnapshotStore()
        self._llm_client = llm_client or GeminiClient()

    def generate(
        self,
        goal: str,
        preferred_tags: Optional[List[str]] = None,
        max_nodes: int = 6,
        compose_level: str = "quick",
        prompt_version: str = "roadmap_gen_v1",
    ) -> Dict[str, object]:
        """
        목표와 태그를 기반으로 로드맵 생성 결과를 반환합니다.

        @param {str} goal - 로드맵 목표.
        @param {Optional[List[str]]} preferred_tags - 선호 태그 목록.
        @param {int} max_nodes - 최대 노드 수.
        @param {str} compose_level - 답변 상세 수준.
        @param {str} prompt_version - 프롬프트 버전.
        @returns {Dict[str, object]} 생성된 로드맵 페이로드.
        """
        preferred_tags = preferred_tags or []
        cache_key = stable_hash_json({
            "goal": goal,
            "tags": preferred_tags,
            "max_nodes": max_nodes,
            "compose_level": compose_level,
        })

        snapshot = self._snapshot_store.get_or_create(
            cache_key,
            version=prompt_version,
            builder=lambda: self._build_payload(goal, preferred_tags, max_nodes, compose_level, prompt_version),
        )
        return snapshot.payload

    def _build_payload(
        self,
        goal: str,
        preferred_tags: List[str],
        max_nodes: int,
        compose_level: str,
        prompt_version: str,
    ) -> Dict[str, object]:
        """
        로드맵 생성 페이로드를 구성합니다.

        @param {str} goal - 로드맵 목표.
        @param {List[str]} preferred_tags - 선호 태그 목록.
        @param {int} max_nodes - 최대 노드 수.
        @param {str} compose_level - 답변 상세 수준.
        @param {str} prompt_version - 프롬프트 버전.
        @returns {Dict[str, object]} 로드맵 페이로드.
        """
        context = self._graph_rag.build_context(goal, top_k=max_nodes)
        candidates = self._graph_rag.score_nodes(goal, top_k=max_nodes)

        nodes = [
            {
                "node_id": node.node_id,
                "title": extractive_summary(node.text, max_sentences=1),
                "tags": node.tags,
            }
            for node in candidates
        ]
        edges = _sequential_edges(nodes)

        if compose_level == "full" and self._llm_client.available():
            prompt = _build_roadmap_prompt(goal, nodes, preferred_tags)
            response = self._llm_client.generate_json(prompt)
            if response.data and _valid_roadmap_payload(response.data):
                return {
                    **response.data,
                    "model_version": self._llm_client.model_name,
                    "prompt_version": prompt_version,
                    "created_at": datetime.utcnow().isoformat(),
                    "retrieval_evidence": context["retrieval_evidence"],
                }

        return {
            "roadmap_id": "generated",
            "title": f"{goal} 로드맵",
            "description": f"{goal}을 위한 기본 학습 순서",
            "nodes": nodes,
            "edges": edges,
            "tags": _merge_tags(nodes, preferred_tags),
            "model_version": "rule-based",
            "prompt_version": prompt_version,
            "created_at": datetime.utcnow().isoformat(),
            "retrieval_evidence": context["retrieval_evidence"],
        }


def _sequential_edges(nodes: List[Dict[str, object]]) -> List[Dict[str, str]]:
    """
    노드 리스트를 순차 엣지로 연결합니다.

    @param {List[Dict[str, object]]} nodes - 노드 목록.
    @returns {List[Dict[str, str]]} 순차 엣지 목록.
    """
    edges = []
    for idx in range(len(nodes) - 1):
        edges.append({"source": nodes[idx]["node_id"], "target": nodes[idx + 1]["node_id"]})
    return edges


def _merge_tags(nodes: List[Dict[str, object]], preferred: List[str]) -> List[str]:
    """
    노드 태그와 선호 태그를 합쳐 정렬합니다.

    @param {List[Dict[str, object]]} nodes - 노드 목록.
    @param {List[str]} preferred - 선호 태그 목록.
    @returns {List[str]} 병합된 태그 목록.
    """
    tags = set(preferred)
    for node in nodes:
        for tag in node.get("tags", []):
            tags.add(tag)
    return sorted(tags)


def _build_roadmap_prompt(goal: str, nodes: List[Dict[str, object]], tags: List[str]) -> str:
    """
    LLM에 전달할 로드맵 생성 프롬프트를 구성합니다.

    @param {str} goal - 로드맵 목표.
    @param {List[Dict[str, object]]} nodes - 후보 노드 목록.
    @param {List[str]} tags - 선호 태그 목록.
    @returns {str} 프롬프트 문자열.
    """
    return (
        "아래 정보를 참고해 로드맵 JSON만 반환해줘. "
        "키는 roadmap_id, title, description, nodes, edges, tags만 사용해. "
        f"목표: {goal} "
        f"후보 노드: {nodes} "
        f"선호 태그: {tags}"
    )


def _valid_roadmap_payload(payload: Dict[str, object]) -> bool:
    """
    로드맵 페이로드 스키마를 검증합니다.

    @param {Dict[str, object]} payload - 검증 대상 페이로드.
    @returns {bool} 유효성 여부.
    """
    required = {"roadmap_id", "title", "description", "nodes", "edges", "tags"}
    if not required.issubset(payload.keys()):
        return False
    if not isinstance(payload.get("nodes"), list) or not isinstance(payload.get("edges"), list):
        return False
    return True
