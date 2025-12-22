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
        self._roadmaps = roadmaps
        self._ontology = build_ontology(roadmaps)
        self._gnn = GraphSAGE()

    def recommend(
        self,
        target_role: str,
        user_id: str,
        adapt_failures: Optional[List[str]] = None,
    ) -> Dict[str, object]:
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
        node_text = {node_id: " ".join(self._ontology.node_tags.get(node_id, [])) for node_id in ordered}
        adjacency = _build_adjacency(self._ontology.edges)
        embeddings = self._gnn.embed(node_text, adjacency)
        predictions = {}
        for node_id in ordered[:3]:
            predictions[node_id] = self._gnn.predict_next(node_id, embeddings, adjacency, top_k=2)
        return predictions


def _filter_soft_nodes(nodes: List[str], ontology, preferred_tags: List[str]) -> List[str]:
    filtered = []
    for node_id in nodes:
        tags = ontology.node_tags.get(node_id, [])
        if preferred_tags and tags and not set(tags) & set(preferred_tags):
            filtered.append(node_id)
        else:
            filtered.append(node_id)
    return filtered


def _insert_review_nodes(nodes: List[str], failed_nodes: List[str]) -> List[str]:
    if not failed_nodes:
        return nodes
    adapted: List[str] = []
    for node_id in nodes:
        if node_id in failed_nodes:
            adapted.append(f"review:{node_id}")
        adapted.append(node_id)
    return adapted


def _extract_edges(ordered: List[str], edges: List[GraphEdge]) -> List[Dict[str, str]]:
    node_set = set(ordered)
    payload = []
    for edge in edges:
        if edge.edge_type not in {"hard", "soft"}:
            continue
        if edge.source in node_set and edge.target in node_set:
            payload.append({"source": edge.source, "target": edge.target, "type": edge.edge_type})
    return payload


def _build_adjacency(edges: List[GraphEdge]) -> Dict[str, List[str]]:
    adjacency: Dict[str, List[str]] = {}
    for edge in edges:
        if edge.edge_type not in {"hard", "soft"}:
            continue
        adjacency.setdefault(edge.source, []).append(edge.target)
    return adjacency
