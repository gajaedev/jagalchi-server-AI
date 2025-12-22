from __future__ import annotations

from typing import Dict, List

from jagalchi_ai.ai_core.domain.graph_node import GraphNode


class GraphStore:
    """그래프 RAG용 인메모리 저장소."""

    def __init__(self) -> None:
        self.nodes: Dict[str, GraphNode] = {}
        self.adjacency: Dict[str, List[str]] = {}

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, source: str, target: str) -> None:
        self.adjacency.setdefault(source, []).append(target)
