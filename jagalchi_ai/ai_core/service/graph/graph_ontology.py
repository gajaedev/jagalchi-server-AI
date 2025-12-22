from __future__ import annotations

from typing import Dict, List, Optional, Set

from jagalchi_ai.ai_core.domain.graph_edge import GraphEdge
from jagalchi_ai.ai_core.domain.roadmap import Roadmap
from jagalchi_ai.ai_core.repository.mock_data import ROLE_REQUIREMENTS


class GraphOntology:
    """역할/스킬 그래프 온톨로지."""

    def __init__(self) -> None:
        """
        그래프 온톨로지 구조를 초기화합니다.

        @returns {None} 노드/엣지 컨테이너를 준비합니다.
        """
        self.nodes: Dict[str, str] = {}
        self.node_tags: Dict[str, List[str]] = {}
        self.edges: List[GraphEdge] = []

    def add_node(self, node_id: str, node_type: str, tags: Optional[List[str]] = None) -> None:
        """
        노드를 온톨로지에 추가합니다.

        @param {str} node_id - 노드 식별자.
        @param {str} node_type - 노드 타입 (role/skill 등).
        @param {Optional[List[str]]} tags - 노드 태그 목록.
        @returns {None} 노드를 등록합니다.
        """
        self.nodes[node_id] = node_type
        self.node_tags[node_id] = tags or []

    def add_edge(self, edge: GraphEdge) -> None:
        """
        엣지를 온톨로지에 추가합니다.

        @param {GraphEdge} edge - 추가할 엣지 객체.
        @returns {None} 엣지를 등록합니다.
        """
        if self.nodes.get(edge.source) == "skill" and self.nodes.get(edge.target) == "skill":
            if self._introduces_cycle(edge.source, edge.target):
                raise ValueError("Cycle detected in skill graph")
        self.edges.append(edge)

    def extract_subgraph(self, target_role: str) -> Set[str]:
        """
        특정 역할에 필요한 스킬 서브그래프를 추출합니다.

        @param {str} target_role - 역할 식별자.
        @returns {Set[str]} 필요한 스킬 노드 집합.
        """
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
        """
        노드 집합을 위상 정렬합니다.

        @param {Set[str]} nodes - 정렬할 노드 집합.
        @param {Optional[List[str]]} preferred_tags - 우선순위 태그.
        @returns {List[str]} 정렬된 노드 리스트.
        """
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
        """
        엣지 추가 시 사이클이 생성되는지 검사합니다.

        @param {str} source - 엣지 시작 노드.
        @param {str} target - 엣지 대상 노드.
        @returns {bool} 사이클 발생 여부.
        """
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
    """
    로드맵 데이터를 기반으로 그래프 온톨로지를 생성합니다.

    @param {Dict[str, Roadmap]} roadmaps - 로드맵 데이터.
    @returns {GraphOntology} 구성된 온톨로지 객체.
    """
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
    """
    태그 선호도를 점수로 환산합니다.

    @param {List[str]} tags - 노드 태그 목록.
    @param {List[str]} preferred - 선호 태그 목록.
    @returns {float} 선호도 점수.
    """
    if not preferred:
        return 0.0
    return len(set(tags) & set(preferred)) / max(len(preferred), 1)
