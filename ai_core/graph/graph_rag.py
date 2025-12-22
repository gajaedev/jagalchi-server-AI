from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ai_core.core.mock_data import ROADMAPS
from ai_core.retrieval.retrieval import GraphRetriever, VectorRetriever
from ai_core.nlp.text_utils import cheap_embed, extractive_summary, jaccard_similarity, tokenize
from ai_core.core.types import RetrievalItem, Roadmap
from ai_core.retrieval.vector_store import InMemoryVectorStore


@dataclass
class GraphNode:
    node_id: str
    text: str
    roadmap_id: str
    tags: List[str]


class GraphStore:
    def __init__(self) -> None:
        self.nodes: Dict[str, GraphNode] = {}
        self.adjacency: Dict[str, List[str]] = {}

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, source: str, target: str) -> None:
        self.adjacency.setdefault(source, []).append(target)


class GraphRAGService:
    def __init__(self, roadmaps: Optional[Dict[str, Roadmap]] = None) -> None:
        self._roadmaps = roadmaps or ROADMAPS
        self._graph = GraphStore()
        self._vector_store = InMemoryVectorStore()
        self._build_graph()

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalItem]:
        vector_retriever = VectorRetriever(self._vector_store, namespace="graph")
        vector_hits = vector_retriever.search(query, top_k=top_k)

        graph_retriever = GraphRetriever(self._graph.adjacency, self._node_text_map())
        expanded: List[RetrievalItem] = []
        for hit in vector_hits:
            expanded.extend(graph_retriever.search(hit.item_id, top_k=2))

        combined = vector_hits + expanded
        combined.sort(key=lambda item: item.score, reverse=True)
        return combined[:top_k]

    def build_context(self, query: str, top_k: int = 5) -> Dict[str, object]:
        evidence = self.retrieve(query, top_k=top_k)
        nodes = []
        for item in evidence:
            node = self._graph.nodes.get(item.item_id)
            if node:
                nodes.append({"node_id": node.node_id, "text": extractive_summary(node.text), "tags": node.tags})
        edges = [
            {"source": src, "target": dst}
            for src, dsts in self._graph.adjacency.items()
            for dst in dsts
            if src in self._graph.nodes and dst in self._graph.nodes
        ]

        return {
            "retrieval_evidence": [
                {"source": item.source, "id": item.item_id, "snippet": item.snippet} for item in evidence
            ],
            "graph_snapshot": {"nodes": nodes, "edges": edges},
        }

    def score_nodes(self, query: str, top_k: int = 5) -> List[GraphNode]:
        tokens = tokenize(query)
        scored = []
        for node in self._graph.nodes.values():
            score = jaccard_similarity(tokens, tokenize(node.text))
            scored.append((score, node))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [node for _, node in scored[:top_k]]

    def _build_graph(self) -> None:
        for roadmap in self._roadmaps.values():
            node_map = {node.node_id: node for node in roadmap.nodes}
            for node in roadmap.nodes:
                node_id = f"{roadmap.roadmap_id}:{node.node_id}"
                text = " ".join([node.title, node.description, " ".join(node.tags)])
                graph_node = GraphNode(node_id=node_id, text=text, roadmap_id=roadmap.roadmap_id, tags=node.tags)
                self._graph.add_node(graph_node)
                self._vector_store.upsert(
                    node_id,
                    vector=cheap_embed(text),
                    metadata={"source": "graph", "namespace": "graph", "snippet": extractive_summary(text)},
                )

            for source, target in roadmap.edges:
                if source in node_map and target in node_map:
                    self._graph.add_edge(f"{roadmap.roadmap_id}:{source}", f"{roadmap.roadmap_id}:{target}")

    def _node_text_map(self) -> Dict[str, str]:
        return {node_id: node.text for node_id, node in self._graph.nodes.items()}
