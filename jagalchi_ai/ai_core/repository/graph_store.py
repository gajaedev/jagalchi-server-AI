from __future__ import annotations

from typing import Dict, List

import networkx as nx

from jagalchi_ai.ai_core.domain.graph_node import GraphNode


class GraphStore:
    """그래프 RAG용 인메모리 저장소."""

    def __init__(self) -> None:
        """
        @returns None
        """
        self._graph = nx.DiGraph()

    @property
    def nodes(self) -> Dict[str, GraphNode]:
        """
        @returns 노드 ID → GraphNode 매핑.
        """
        return {node_id: data["node"] for node_id, data in self._graph.nodes(data=True)}

    @property
    def adjacency(self) -> Dict[str, List[str]]:
        """
        @returns 노드 ID → 후속 노드 리스트 매핑.
        """
        return {node_id: list(self._graph.successors(node_id)) for node_id in self._graph.nodes}

    def add_node(self, node: GraphNode) -> None:
        """
        @param node 추가할 그래프 노드.
        @returns None
        """
        self._graph.add_node(node.node_id, node=node)

    def add_edge(self, source: str, target: str) -> None:
        """
        @param source 출발 노드 ID.
        @param target 도착 노드 ID.
        @returns None
        """
        self._graph.add_edge(source, target)

    def neighbors(self, node_id: str) -> List[str]:
        """
        @param node_id 기준 노드 ID.
        @returns 후속 노드 ID 리스트.
        """
        return list(self._graph.successors(node_id))
