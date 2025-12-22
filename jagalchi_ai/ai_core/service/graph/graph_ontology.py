from __future__ import annotations

from typing import Dict, List, Optional, Set

from jagalchi_ai.ai_core.domain.graph_edge import GraphEdge
from jagalchi_ai.ai_core.domain.roadmap import Roadmap
from jagalchi_ai.ai_core.repository.mock_data import ROLE_REQUIREMENTS


class GraphOntology:
    """역할/스킬 그래프 온톨로지."""

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


def _preference_score(tags: List[str], preferred: List[str]) -> float:
    if not preferred:
        return 0.0
    return len(set(tags) & set(preferred)) / max(len(preferred), 1)
