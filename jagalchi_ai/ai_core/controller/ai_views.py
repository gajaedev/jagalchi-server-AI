from __future__ import annotations

from datetime import datetime
from typing import Dict

from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema

from jagalchi_ai.ai_core.domain.learning_record import LearningRecord
from jagalchi_ai.ai_core.repository import mock_data
from jagalchi_ai.ai_core.service.analytics.learning_analytics import LearningPatternService
from jagalchi_ai.ai_core.service.comments.comment_intelligence import CommentIntelligenceService
from jagalchi_ai.ai_core.service.coach.learning_coach import LearningCoachService
from jagalchi_ai.ai_core.service.graph.graph_rag import GraphRAGService
from jagalchi_ai.ai_core.service.graph.roadmap_generator import RoadmapGeneratorService
from jagalchi_ai.ai_core.service.graph.roadmap_recommendation_service import RoadmapRecommendationService
from jagalchi_ai.ai_core.service.record.record_coach import RecordCoachService
from jagalchi_ai.ai_core.service.recommendation.related_roadmaps import RelatedRoadmapsService
from jagalchi_ai.ai_core.service.recommendation.resource_recommender import ResourceRecommendationService
from jagalchi_ai.ai_core.service.tech.tech_cards import TechCardService
from jagalchi_ai.ai_core.service.tech.tech_fingerprint import TechFingerprintService
from jagalchi_ai.ai_core.controller.serializers import (
    CommentDigestSerializer,
    DemoResponseSerializer,
    DuplicateSuggestItemSerializer,
    GraphRAGContextSerializer,
    LearningCoachSerializer,
    LearningPatternSerializer,
    RecordCoachSerializer,
    RelatedRoadmapsSerializer,
    ResourceRecommendationSerializer,
    RoadmapGeneratedSerializer,
    RoadmapRecommendationSerializer,
    TechCardSerializer,
    TechFingerprintSerializer,
)


class DemoAIAPIView(APIView):
    """전체 AI 기능을 한 번에 확인하는 데모 엔드포인트."""

    @extend_schema(
        parameters=[
            OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=False, description="로드맵 ID"),
            OpenApiParameter("tech_slug", OpenApiTypes.STR, required=False, description="기술 카드 슬러그"),
            OpenApiParameter("user_id", OpenApiTypes.STR, required=False, description="사용자 ID"),
            OpenApiParameter("question", OpenApiTypes.STR, required=False, description="질문/검색 문장"),
            OpenApiParameter("goal", OpenApiTypes.STR, required=False, description="로드맵 생성 목표"),
            OpenApiParameter("target_role", OpenApiTypes.STR, required=False, description="추천 대상 역할"),
            OpenApiParameter(
                "compose_level",
                OpenApiTypes.STR,
                required=False,
                description="quick/full",
                enum=["quick", "full"],
            ),
            OpenApiParameter(
                "include_rationale",
                OpenApiTypes.BOOL,
                required=False,
                description="태그 rationale 포함 여부",
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                "demo",
                value={
                    "meta": {
                        "generated_at": "2025-01-01T00:00:00Z",
                        "roadmap_id": "rm_frontend",
                        "tech_slug": "react",
                        "user_id": "user_1",
                        "compose_level": "quick",
                    },
                    "record_coach": {"record_id": "rec1", "scores": {"quality_score": 62}},
                    "related_roadmaps": {"roadmap_id": "rm_frontend", "candidates": []},
                },
                response_only=True,
            )
        ],
    )
    def get(self, request) -> Response:
        roadmap_id = request.GET.get("roadmap_id") or "rm_frontend"
        tech_slug = request.GET.get("tech_slug") or "react"
        user_id = request.GET.get("user_id") or "user_1"
        question = request.GET.get("question") or "React useEffect 에러 해결 방법"
        goal = request.GET.get("goal") or "프론트엔드 심화"
        target_role = request.GET.get("target_role") or "frontend_dev"
        compose_level = request.GET.get("compose_level") or "quick"
        include_rationale = request.GET.get("include_rationale") == "true"

        roadmap = _resolve_roadmap(roadmap_id)
        node = _resolve_node(roadmap, request.GET.get("node_id"))
        record = _build_record(node, roadmap)

        record_feedback = _record_feedback(record, node, roadmap.tags, compose_level)
        related_roadmaps = _related_roadmaps(roadmap.roadmap_id)
        tech_card = _tech_card(tech_slug)
        tech_fingerprint = _tech_fingerprint(roadmap, include_rationale)
        comment_digest, duplicate_suggest = _comment_insights(roadmap.roadmap_id, question)
        resource_recommendation = _resource_recommendation(question, top_k=3)
        learning_pattern = _learning_pattern(user_id)
        graph_rag = GraphRAGService(mock_data.ROADMAPS)
        graph_context = graph_rag.build_context(question, top_k=3)
        roadmap_generated = _roadmap_generated(graph_rag, goal, roadmap.tags[:2], compose_level)
        learning_coach_answer = _learning_coach(graph_rag, question, user_id, compose_level)
        roadmap_recommendation = _roadmap_recommendation(target_role, user_id)

        payload: Dict[str, object] = {
            "meta": {
                "generated_at": datetime.utcnow().isoformat(),
                "roadmap_id": roadmap.roadmap_id,
                "tech_slug": tech_slug,
                "user_id": user_id,
                "compose_level": compose_level,
            },
            "record_coach": record_feedback,
            "related_roadmaps": related_roadmaps,
            "tech_card": tech_card,
            "tech_fingerprint": tech_fingerprint,
            "comment_digest": comment_digest,
            "duplicate_suggest": duplicate_suggest,
            "resource_recommendation": resource_recommendation,
            "learning_pattern": learning_pattern,
            "graph_rag_context": graph_context,
            "roadmap_generated": roadmap_generated,
            "learning_coach": learning_coach_answer,
            "roadmap_recommendation": roadmap_recommendation,
        }
        return _serialize(DemoResponseSerializer, payload)


class RecordCoachAPIView(APIView):
    """Record Coach 단일 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=False, description="로드맵 ID"),
            OpenApiParameter("node_id", OpenApiTypes.STR, required=False, description="로드맵 노드 ID"),
            OpenApiParameter(
                "compose_level",
                OpenApiTypes.STR,
                required=False,
                description="quick/full",
                enum=["quick", "full"],
            ),
        ],
        responses=RecordCoachSerializer,
    )
    def get(self, request) -> Response:
        roadmap = _resolve_roadmap(request.GET.get("roadmap_id") or "rm_frontend")
        node = _resolve_node(roadmap, request.GET.get("node_id"))
        compose_level = request.GET.get("compose_level") or "quick"
        record = _build_record(node, roadmap)
        payload = _record_feedback(record, node, roadmap.tags, compose_level)
        return _serialize(RecordCoachSerializer, payload)


class RelatedRoadmapsAPIView(APIView):
    """연관 로드맵 추천 응답."""

    @extend_schema(
        parameters=[OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=False, description="로드맵 ID")],
        responses=RelatedRoadmapsSerializer,
    )
    def get(self, request) -> Response:
        roadmap_id = request.GET.get("roadmap_id") or "rm_frontend"
        payload = _related_roadmaps(roadmap_id)
        return _serialize(RelatedRoadmapsSerializer, payload)


class TechCardAPIView(APIView):
    """기술 카드 응답."""

    @extend_schema(
        parameters=[OpenApiParameter("tech_slug", OpenApiTypes.STR, required=False, description="기술 슬러그")],
        responses=TechCardSerializer,
    )
    def get(self, request) -> Response:
        tech_slug = request.GET.get("tech_slug") or "react"
        payload = _tech_card(tech_slug)
        return _serialize(TechCardSerializer, payload)


class TechFingerprintAPIView(APIView):
    """기술 지문 태그 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=False, description="로드맵 ID"),
            OpenApiParameter(
                "include_rationale",
                OpenApiTypes.BOOL,
                required=False,
                description="rationale 포함 여부",
            ),
        ],
        responses=TechFingerprintSerializer,
    )
    def get(self, request) -> Response:
        roadmap = _resolve_roadmap(request.GET.get("roadmap_id") or "rm_frontend")
        include_rationale = request.GET.get("include_rationale") == "true"
        payload = _tech_fingerprint(roadmap, include_rationale)
        return _serialize(TechFingerprintSerializer, payload)


class CommentDigestAPIView(APIView):
    """코멘트 다이제스트 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=False, description="로드맵 ID"),
            OpenApiParameter("period_days", OpenApiTypes.INT, required=False, description="기간(일)"),
        ],
        responses=CommentDigestSerializer,
    )
    def get(self, request) -> Response:
        roadmap_id = request.GET.get("roadmap_id") or "rm_frontend"
        period_days = int(request.GET.get("period_days") or 14)
        service = CommentIntelligenceService()
        payload = service.comment_digest(roadmap_id, period_days=period_days)
        return _serialize(CommentDigestSerializer, payload)


class CommentDuplicateAPIView(APIView):
    """중복 질문 후보 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=False, description="로드맵 ID"),
            OpenApiParameter("query", OpenApiTypes.STR, required=False, description="질문"),
            OpenApiParameter("top_k", OpenApiTypes.INT, required=False, description="추천 개수"),
        ],
        responses=DuplicateSuggestItemSerializer(many=True),
    )
    def get(self, request) -> Response:
        roadmap_id = request.GET.get("roadmap_id") or "rm_frontend"
        query = request.GET.get("query") or "React useEffect 에러 해결 방법"
        top_k = int(request.GET.get("top_k") or 3)
        service = CommentIntelligenceService()
        payload = service.duplicate_suggest(roadmap_id, query, top_k=top_k)
        return _serialize(DuplicateSuggestItemSerializer, payload, many=True)


class ResourceRecommendationAPIView(APIView):
    """자료 추천 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("query", OpenApiTypes.STR, required=False, description="검색 질의"),
            OpenApiParameter("top_k", OpenApiTypes.INT, required=False, description="추천 개수"),
        ],
        responses=ResourceRecommendationSerializer,
    )
    def get(self, request) -> Response:
        query = request.GET.get("query") or "React useEffect 에러 해결 방법"
        top_k = int(request.GET.get("top_k") or 3)
        payload = _resource_recommendation(query, top_k)
        return _serialize(ResourceRecommendationSerializer, payload)


class LearningPatternAPIView(APIView):
    """학습 패턴 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("user_id", OpenApiTypes.STR, required=False, description="사용자 ID"),
            OpenApiParameter("days", OpenApiTypes.INT, required=False, description="기간(일)"),
        ],
        responses=LearningPatternSerializer,
    )
    def get(self, request) -> Response:
        user_id = request.GET.get("user_id") or "user_1"
        days = int(request.GET.get("days") or 30)
        payload = LearningPatternService().analyze(user_id, days=days)
        return _serialize(LearningPatternSerializer, payload)


class GraphRAGAPIView(APIView):
    """GraphRAG 컨텍스트 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("query", OpenApiTypes.STR, required=False, description="검색 질의"),
            OpenApiParameter("top_k", OpenApiTypes.INT, required=False, description="근거 개수"),
        ],
        responses=GraphRAGContextSerializer,
    )
    def get(self, request) -> Response:
        query = request.GET.get("query") or "React useEffect 에러 해결 방법"
        top_k = int(request.GET.get("top_k") or 3)
        graph_rag = GraphRAGService(mock_data.ROADMAPS)
        payload = graph_rag.build_context(query, top_k=top_k)
        return _serialize(GraphRAGContextSerializer, payload)


class RoadmapGeneratedAPIView(APIView):
    """GraphRAG 기반 로드맵 생성 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("goal", OpenApiTypes.STR, required=False, description="목표"),
            OpenApiParameter("preferred_tags", OpenApiTypes.STR, required=False, description="태그(콤마 구분)"),
            OpenApiParameter("max_nodes", OpenApiTypes.INT, required=False, description="노드 개수"),
            OpenApiParameter(
                "compose_level",
                OpenApiTypes.STR,
                required=False,
                description="quick/full",
                enum=["quick", "full"],
            ),
        ],
        responses=RoadmapGeneratedSerializer,
    )
    def get(self, request) -> Response:
        goal = request.GET.get("goal") or "프론트엔드 심화"
        preferred_tags = request.GET.get("preferred_tags") or "frontend"
        tags = [tag.strip() for tag in preferred_tags.split(",") if tag.strip()]
        max_nodes = int(request.GET.get("max_nodes") or 6)
        compose_level = request.GET.get("compose_level") or "quick"
        graph_rag = GraphRAGService(mock_data.ROADMAPS)
        payload = RoadmapGeneratorService(graph_rag=graph_rag).generate(
            goal,
            preferred_tags=tags,
            max_nodes=max_nodes,
            compose_level=compose_level,
        )
        return _serialize(RoadmapGeneratedSerializer, payload)


class LearningCoachAPIView(APIView):
    """학습 코치 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("user_id", OpenApiTypes.STR, required=False, description="사용자 ID"),
            OpenApiParameter("question", OpenApiTypes.STR, required=False, description="질문"),
            OpenApiParameter(
                "compose_level",
                OpenApiTypes.STR,
                required=False,
                description="quick/full",
                enum=["quick", "full"],
            ),
        ],
        responses=LearningCoachSerializer,
    )
    def get(self, request) -> Response:
        user_id = request.GET.get("user_id") or "user_1"
        question = request.GET.get("question") or "React useEffect 에러 해결 방법"
        compose_level = request.GET.get("compose_level") or "quick"
        graph_rag = GraphRAGService(mock_data.ROADMAPS)
        payload = _learning_coach(graph_rag, question, user_id, compose_level)
        return _serialize(LearningCoachSerializer, payload)


class RoadmapRecommendationAPIView(APIView):
    """그래프 기반 로드맵 추천 응답."""

    @extend_schema(
        parameters=[
            OpenApiParameter("target_role", OpenApiTypes.STR, required=False, description="목표 역할"),
            OpenApiParameter("user_id", OpenApiTypes.STR, required=False, description="사용자 ID"),
        ],
        responses=RoadmapRecommendationSerializer,
    )
    def get(self, request) -> Response:
        target_role = request.GET.get("target_role") or "frontend_dev"
        user_id = request.GET.get("user_id") or "user_1"
        payload = _roadmap_recommendation(target_role, user_id)
        return _serialize(RoadmapRecommendationSerializer, payload)


def _resolve_roadmap(roadmap_id: str):
    if roadmap_id in mock_data.ROADMAPS:
        return mock_data.ROADMAPS[roadmap_id]
    return next(iter(mock_data.ROADMAPS.values()))


def _resolve_node(roadmap, node_id: str | None):
    if node_id:
        for node in roadmap.nodes:
            if node.node_id == node_id:
                return node
    return roadmap.nodes[0]


def _build_record(node, roadmap):
    base_record = mock_data.LEARNING_RECORDS[0]
    return LearningRecord(
        record_id=base_record.record_id,
        memo=base_record.memo,
        links=base_record.links,
        node_id=node.node_id,
        roadmap_id=roadmap.roadmap_id,
    )


def _record_feedback(record, node, tags, compose_level: str):
    return RecordCoachService().get_feedback(record, node, tags, compose_level=compose_level)


def _related_roadmaps(roadmap_id: str):
    return RelatedRoadmapsService(mock_data.ROADMAPS).generate_snapshot(roadmap_id)


def _tech_card(tech_slug: str):
    return TechCardService().get_or_create(tech_slug)


def _tech_fingerprint(roadmap, include_rationale: bool):
    return TechFingerprintService().generate(roadmap, include_rationale=include_rationale)


def _comment_insights(roadmap_id: str, question: str):
    service = CommentIntelligenceService()
    digest = service.comment_digest(roadmap_id)
    duplicates = service.duplicate_suggest(roadmap_id, question, top_k=3)
    return digest, duplicates


def _resource_recommendation(query: str, top_k: int):
    return ResourceRecommendationService().recommend(query, top_k=top_k)


def _learning_pattern(user_id: str):
    return LearningPatternService().analyze(user_id)


def _roadmap_generated(graph_rag, goal: str, preferred_tags, compose_level: str):
    return RoadmapGeneratorService(graph_rag=graph_rag).generate(
        goal,
        preferred_tags=preferred_tags,
        compose_level=compose_level,
    )


def _learning_coach(graph_rag, question: str, user_id: str, compose_level: str):
    resource_recommender = ResourceRecommendationService()
    return LearningCoachService(graph_rag=graph_rag, resource_recommender=resource_recommender).answer(
        user_id,
        question,
        compose_level=compose_level,
    )


def _roadmap_recommendation(target_role: str, user_id: str):
    return RoadmapRecommendationService(mock_data.ROADMAPS).recommend(target_role, user_id)


def _serialize(serializer_class, payload, many: bool = False) -> Response:
    serializer = serializer_class(payload, many=many)
    return Response(serializer.data)
