from __future__ import annotations

from typing import Dict, List, Optional

from jagalchi_ai.ai_core.client import GeminiClient
from jagalchi_ai.ai_core.models import InitData, NodeResource
from jagalchi_ai.ai_core.repository.mock_data import ROADMAPS
from jagalchi_ai.ai_core.service.recommendation.resource_recommender import ResourceRecommendationService


class NodeContentService:
    """노드 콘텐츠 생성 및 관리 서비스."""

    def __init__(self):
        self._llm_client = GeminiClient()
        self._resource_recommender = ResourceRecommendationService()

    def generate_nodes_from_init(self, init_data_id: str) -> Dict[str, object]:
        """
        Init 데이터를 기반으로 노드 구조를 생성합니다.
        """
        try:
            init_data = InitData.objects.get(init_data_id=init_data_id)
        except InitData.DoesNotExist:
            raise ValueError(f"Init Data not found: {init_data_id}")

        content = init_data.content
        prompt = (
            "다음 교육 과정(커리큘럼) 내용을 분석하여 로드맵 노드 구조를 JSON으로 생성해줘. "
            "노드 목록(nodes)과 연결(edges)을 포함해야 해. "
            f"내용: {content[:1000]}"
        )
        
        # LLM 호출 (실제로는 여기서 JSON 파싱 등 처리 필요)
        if self._llm_client.available():
            response = self._llm_client.generate_json(prompt)
            if response.data:
                return response.data

        # Fallback (규칙 기반 또는 더미)
        return {
            "nodes": [
                {"node_id": "gen_1", "title": "기초 개념", "tags": ["basic"]},
                {"node_id": "gen_2", "title": "심화 응용", "tags": ["advanced"]},
            ],
            "edges": [{"source": "gen_1", "target": "gen_2"}],
        }

    def generate_node_description(self, node_title: str, context: Optional[str] = None) -> str:
        """
        노드 제목과 컨텍스트를 기반으로 설명을 생성합니다.
        """
        prompt = f"로드맵 노드 '{node_title}'에 대한 간략한 학습 가이드/설명을 2문장으로 작성해줘."
        if context:
            prompt += f" 컨텍스트: {context}"

        if self._llm_client.available():
            desc = self._llm_client.generate_text(prompt)
            if desc:
                return desc
        
        return f"{node_title}에 대한 학습이 필요합니다. 기초 개념을 확실히 다지세요."

    def recommend_resources_for_node(self, node_id: str, roadmap_id: str) -> Dict[str, object]:
        """
        노드 주제를 기반으로 자료를 추천합니다.
        """
        roadmap = ROADMAPS.get(roadmap_id)
        node = None
        if roadmap:
            for n in roadmap.nodes:
                if n.node_id == node_id:
                    node = n
                    break
        
        query = node.title if node else "프로그래밍 기초"
        if node and node.tags:
            query += f" {node.tags[0]}"

        # 기존 리소스 추천 서비스 활용
        return self._resource_recommender.recommend(query, top_k=3)

    def save_resource_to_node(
        self,
        node_id: str,
        title: str,
        url: str,
        source: str = "web",
        description: Optional[str] = None
    ) -> NodeResource:
        """
        추천된 자료를 노드에 저장합니다.
        """
        return NodeResource.objects.create(
            node_id=node_id,
            title=title,
            url=url,
            source=source,
            description=description,
        )

    def get_node_resources(self, node_id: str) -> List[NodeResource]:
        """
        노드에 저장된 자료 목록을 조회합니다.
        """
        return list(NodeResource.objects.filter(node_id=node_id))