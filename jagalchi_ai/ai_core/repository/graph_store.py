from __future__ import annotations

from typing import Dict, List

import networkx as nx

from jagalchi_ai.ai_core.domain.graph_node import GraphNode


class GraphStore:
    """그래프 RAG용 인메모리 저장소."""

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    @property
    def nodes(self) -> Dict[str, GraphNode]:
        return {node_id: data["node"] for node_id, data in self._graph.nodes(data=True)}

    @property
    def adjacency(self) -> Dict[str, List[str]]:
        return {node_id: list(self._graph.successors(node_id)) for node_id in self._graph.nodes}

    def add_node(self, node: GraphNode) -> None:
        self._graph.add_node(node.node_id, node=node)

    def add_edge(self, source: str, target: str) -> None:
        self._graph.add_edge(source, target)

    def neighbors(self, node_id: str) -> List[str]:
        return list(self._graph.successors(node_id))
