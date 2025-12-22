from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.domain.graph_edge import GraphEdge
from jagalchi_ai.ai_core.domain.roadmap import Roadmap
from jagalchi_ai.ai_core.repository.mock_data import USER_MASTERED_SKILLS, USER_PREFERENCES
from jagalchi_ai.ai_core.service.graph.graph_ontology import build_ontology
from jagalchi_ai.ai_core.service.graph.graph_sage import GraphSAGE


class RoadmapRecommendationService:
    """그래프 기반 로드맵 추천 서비스."""

    def __init__(self, roadmaps: Dict[str, Roadmap]) -> None:
        """
        추천 대상 로드맵과 그래프 모델을 초기화합니다.

        @param {Dict[str, Roadmap]} roadmaps - 로드맵 데이터.
        @returns {None} 온톨로지와 GNN을 구성합니다.
        """
        self._roadmaps = roadmaps
        self._ontology = build_ontology(roadmaps)
        self._gnn = GraphSAGE()

    def recommend(
        self,
        target_role: str,
        user_id: str,
        adapt_failures: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        """
        목표 역할과 사용자 선호를 반영해 로드맵을 추천합니다.

        @param {str} target_role - 목표 역할.
        @param {str} user_id - 사용자 ID.
        @param {Optional[List[str]]} adapt_failures - 재학습 대상 노드 목록.
        @returns {Dict[str, object]} 추천 로드맵 페이로드.
        """
        preferred_tags = USER_PREFERENCES.get(user_id, {}).get("preferred_tags", [])
        mastered = USER_MASTERED_SKILLS.get(user_id, set())

        nodes = self._ontology.extract_subgraph(target_role)
        ordered = self._ontology.topological_sort(nodes, preferred_tags=preferred_tags)
        ordered = _filter_soft_nodes(ordered, self._ontology, preferred_tags)

        ordered = _insert_review_nodes(ordered, adapt_failures or [])
        gnn_predictions = self._predict_with_gnn(ordered)

        node_payload = []
        for node_id in ordered:
            status = "COMPLETED" if node_id in mastered else "AVAILABLE"
            node_payload.append({"node_id": node_id, "status": status})

        return {
            "roadmap_id": f"roadmap:{target_role}",
            "target_role": target_role,
            "nodes": node_payload,
            "edges": _extract_edges(ordered, self._ontology.edges),
            "gnn_predictions": gnn_predictions,
            "model_version": "roadmap_graph_v1",
            "created_at": datetime.utcnow().isoformat(),
        }

    def _predict_with_gnn(self, ordered: List[str]) -> Dict[str, List[str]]:
        """
        GNN 임베딩을 사용해 다음 학습 후보를 예측합니다.

        @param {List[str]} ordered - 정렬된 노드 목록.
        @returns {Dict[str, List[str]]} 노드별 추천 목록.
        """
        node_text = {node_id: " ".join(self._ontology.node_tags.get(node_id, [])) for node_id in ordered}
        adjacency = _build_adjacency(self._ontology.edges)
        embeddings = self._gnn.embed(node_text, adjacency)
        predictions = {}
        for node_id in ordered[:3]:
            predictions[node_id] = self._gnn.predict_next(node_id, embeddings, adjacency, top_k=2)
        return predictions


def _filter_soft_nodes(nodes: List[str], ontology, preferred_tags: List[str]) -> List[str]:
    """
    선호 태그 기준으로 소프트 노드를 필터링합니다.

    @param {List[str]} nodes - 노드 목록.
    @param {object} ontology - 온톨로지 객체.
    @param {List[str]} preferred_tags - 선호 태그 목록.
    @returns {List[str]} 필터링된 노드 목록.
    """
    filtered = []
    for node_id in nodes:
        tags = ontology.node_tags.get(node_id, [])
        if preferred_tags and tags and not set(tags) & set(preferred_tags):
            filtered.append(node_id)
        else:
            filtered.append(node_id)
    return filtered


def _insert_review_nodes(nodes: List[str], failed_nodes: List[str]) -> List[str]:
    """
    실패 노드 앞에 리뷰 노드를 삽입합니다.

    @param {List[str]} nodes - 노드 목록.
    @param {List[str]} failed_nodes - 실패 노드 목록.
    @returns {List[str]} 리뷰 노드가 포함된 목록.
    """
    if not failed_nodes:
        return nodes
    adapted: List[str] = []
    for node_id in nodes:
        if node_id in failed_nodes:
            adapted.append(f"review:{node_id}")
        adapted.append(node_id)
    return adapted


def _extract_edges(ordered: List[str], edges: List[GraphEdge]) -> List[Dict[str, str]]:
    """
    정렬된 노드 기준으로 유효 엣지를 추출합니다.

    @param {List[str]} ordered - 정렬된 노드 목록.
    @param {List[GraphEdge]} edges - 전체 엣지 목록.
    @returns {List[Dict[str, str]]} 엣지 페이로드 목록.
    """
    node_set = set(ordered)
    payload = []
    for edge in edges:
        if edge.edge_type not in {"hard", "soft"}:
            continue
        if edge.source in node_set and edge.target in node_set:
            payload.append({"source": edge.source, "target": edge.target, "type": edge.edge_type})
    return payload


def _build_adjacency(edges: List[GraphEdge]) -> Dict[str, List[str]]:
    """
    엣지 목록을 인접 리스트로 변환합니다.

    @param {List[GraphEdge]} edges - 엣지 목록.
    @returns {Dict[str, List[str]]} 인접 리스트.
    """
    adjacency: Dict[str, List[str]] = {}
    for edge in edges:
        if edge.edge_type not in {"hard", "soft"}:
            continue
        adjacency.setdefault(edge.source, []).append(edge.target)
    return adjacency
