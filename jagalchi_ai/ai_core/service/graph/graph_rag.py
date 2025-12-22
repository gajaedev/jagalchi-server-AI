from __future__ import annotations

from typing import Dict, List, Optional

from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed, extractive_summary, jaccard_similarity, tokenize
from jagalchi_ai.ai_core.domain.graph_node import GraphNode
from jagalchi_ai.ai_core.domain.retrieval_item import RetrievalItem
from jagalchi_ai.ai_core.domain.roadmap import Roadmap
from jagalchi_ai.ai_core.repository.graph_store import GraphStore
from jagalchi_ai.ai_core.repository.in_memory_vector_store import InMemoryVectorStore
from jagalchi_ai.ai_core.repository.mock_data import ROADMAPS
from jagalchi_ai.ai_core.service.retrieval.vector_retriever import VectorRetriever


class GraphRAGService:
    """그래프 기반 RAG 검색 서비스."""

    def __init__(self, roadmaps: Optional[Dict[str, Roadmap]] = None) -> None:
        """
        로드맵 기반 그래프와 벡터 인덱스를 초기화합니다.

        @param {Optional[Dict[str, Roadmap]]} roadmaps - 로드맵 데이터.
        @returns {None} 그래프/벡터 스토어를 구축합니다.
        """
        self._roadmaps = roadmaps or ROADMAPS
        self._graph = GraphStore()
        self._vector_store = InMemoryVectorStore()
        self._build_graph()

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalItem]:
        """
        그래프 기반 컨텍스트 후보를 검색합니다.

        @param {str} query - 검색 질의.
        @param {int} top_k - 반환할 상위 결과 수.
        @returns {List[RetrievalItem]} 검색된 증거 목록.
        """
        vector_retriever = VectorRetriever(self._vector_store, namespace="graph")
        vector_hits = vector_retriever.search(query, top_k=top_k)

        expanded: List[RetrievalItem] = []
        for hit in vector_hits:
            for neighbor in self._graph.neighbors(hit.item_id)[:2]:
                text = self._node_text_map().get(neighbor, "")
                expanded.append(
                    RetrievalItem(
                        source="graph",
                        item_id=neighbor,
                        score=1.0,
                        snippet=extractive_summary(text),
                        metadata={"source": "graph"},
                    )
                )

        combined = vector_hits + expanded
        combined.sort(key=lambda item: item.score, reverse=True)
        return combined[:top_k]

    def build_context(self, query: str, top_k: int = 5) -> Dict[str, object]:
        """
        그래프 스냅샷과 근거를 포함한 컨텍스트를 생성합니다.

        @param {str} query - 검색 질의.
        @param {int} top_k - 반환할 상위 결과 수.
        @returns {Dict[str, object]} 근거/그래프 스냅샷 페이로드.
        """
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
        """
        노드 텍스트와 질의의 유사도를 계산해 상위 노드를 반환합니다.

        @param {str} query - 검색 질의.
        @param {int} top_k - 반환할 상위 노드 수.
        @returns {List[GraphNode]} 상위 노드 목록.
        """
        tokens = tokenize(query)
        scored = []
        for node in self._graph.nodes.values():
            score = jaccard_similarity(tokens, tokenize(node.text))
            scored.append((score, node))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [node for _, node in scored[:top_k]]

    def _build_graph(self) -> None:
        """
        로드맵 데이터를 그래프/벡터 스토어에 적재합니다.

        @returns {None} 내부 그래프 상태를 구성합니다.
        """
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
                    metadata={
                        "source": "graph",
                        "namespace": "graph",
                        "snippet": extractive_summary(text),
                        "text": text,
                    },
                )

            for source, target in roadmap.edges:
                if source in node_map and target in node_map:
                    self._graph.add_edge(f"{roadmap.roadmap_id}:{source}", f"{roadmap.roadmap_id}:{target}")

    def _node_text_map(self) -> Dict[str, str]:
        """
        노드 ID -> 텍스트 매핑을 반환합니다.

        @returns {Dict[str, str]} 노드 텍스트 매핑.
        """
        return {node_id: node.text for node_id, node in self._graph.nodes.items()}
