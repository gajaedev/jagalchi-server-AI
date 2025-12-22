from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set

from ai_core.graph.gnn import GraphSAGE
from ai_core.core.mock_data import ROLE_REQUIREMENTS, USER_MASTERED_SKILLS, USER_PREFERENCES
from ai_core.core.types import Roadmap


@dataclass
class GraphEdge:
    source: str
    target: str
    weight: float = 1.0
    edge_type: str = "hard"  # hard | soft | role


class GraphOntology:
    def __init__(self) -> None:
        self.nodes: Dict[str, str] = {}
        self.node_tags: Dict[str, List[str]] = {}
        self.edges: List[GraphEdge] = []

    def add_node(self, node_id: str, node_type: str, tags: Optional[List[str]] = None) -> None:
        self.nodes[node_id] = node_type
        self.node_tags[node_id] = tags or []

    def add_edge(self, edge: GraphEdge) -> None:
        if self.nodes.get(edge.source) == "skill" and self.nodes.get(edge.target) == "skill":
            if self._introduces_cycle(edge.source, edge.target):
                raise ValueError("Cycle detected in skill graph")
        self.edges.append(edge)

    def extract_subgraph(self, target_role: str) -> Set[str]:
        required = set(ROLE_REQUIREMENTS.get(target_role, []))
        expanded = set(required)
        added = True
        while added:
            added = False
            for edge in self.edges:
                if edge.edge_type in {"hard", "soft"} and edge.target in expanded:
                    if edge.source not in expanded:
                        expanded.add(edge.source)
                        added = True
        return expanded

    def topological_sort(self, nodes: Set[str], preferred_tags: Optional[List[str]] = None) -> List[str]:
        preferred_tags = preferred_tags or []
        indegree: Dict[str, int] = {node: 0 for node in nodes}
        adjacency: Dict[str, List[str]] = {node: [] for node in nodes}
        for edge in self.edges:
            if edge.edge_type not in {"hard", "soft"}:
                continue
            if edge.source in nodes and edge.target in nodes:
                adjacency[edge.source].append(edge.target)
                indegree[edge.target] += 1

        ordered: List[str] = []
        queue = [node for node, degree in indegree.items() if degree == 0]
        queue.sort(key=lambda node: _preference_score(self.node_tags.get(node, []), preferred_tags), reverse=True)

        while queue:
            current = queue.pop(0)
            ordered.append(current)
            for neighbor in adjacency[current]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)
                    queue.sort(
                        key=lambda node: _preference_score(self.node_tags.get(node, []), preferred_tags),
                        reverse=True,
                    )

        if len(ordered) != len(nodes):
            raise ValueError("Topological sort failed")
        return ordered

    def _introduces_cycle(self, source: str, target: str) -> bool:
        visited = set()
        stack = [target]
        while stack:
            node = stack.pop()
            if node == source:
                return True
            if node in visited:
                continue
            visited.add(node)
            for edge in self.edges:
                if edge.edge_type in {"hard", "soft"} and edge.source == node:
                    stack.append(edge.target)
        return False


class RoadmapRecommendationService:
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


def build_ontology(roadmaps: Dict[str, Roadmap]) -> GraphOntology:
    ontology = GraphOntology()
    for roadmap in roadmaps.values():
        for node in roadmap.nodes:
            ontology.add_node(node.node_id, "skill", tags=node.tags)
        for source, target in roadmap.edges:
            ontology.add_edge(GraphEdge(source=source, target=target, weight=1.0, edge_type="hard"))

    for role, skills in ROLE_REQUIREMENTS.items():
        ontology.add_node(role, "role")
        for skill in skills:
            ontology.add_edge(GraphEdge(source=role, target=skill, weight=1.0, edge_type="role"))
    return ontology


def _filter_soft_nodes(nodes: List[str], ontology: GraphOntology, preferred_tags: List[str]) -> List[str]:
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


def _preference_score(tags: List[str], preferred: List[str]) -> float:
    if not preferred:
        return 0.0
    return len(set(tags) & set(preferred)) / max(len(preferred), 1)
