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
    DocumentRoadmapSerializer,
    DuplicateSuggestItemSerializer,
    GraphRAGContextSerializer,
    HealthCheckSerializer,
    LearningCoachSerializer,
    LearningPatternSerializer,
    RecordCoachSerializer,
    RelatedRoadmapsSerializer,
    ResourceRecommendationSerializer,
    RoadmapGeneratedSerializer,
    RoadmapRecommendationSerializer,
    TechCardSerializer,
    TechFingerprintSerializer,
    WebSearchSerializer,
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
        """
        @param request DRF 요청 객체 (쿼리 파라미터로 데모 입력을 받는다).
        @returns 모든 AI 기능 결과를 합친 데모 응답 JSON.
        """
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
        """
        @param request DRF 요청 객체 (roadmap_id/node_id/compose_level 사용).
        @returns Record Coach 결과 JSON.
        """
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
        """
        @param request DRF 요청 객체 (roadmap_id 사용).
        @returns 연관 로드맵 추천 JSON.
        """
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
        """
        @param request DRF 요청 객체 (tech_slug 사용).
        @returns 기술 카드 JSON.
        """
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
        """
        @param request DRF 요청 객체 (roadmap_id/include_rationale 사용).
        @returns 로드맵 기술 지문 JSON.
        """
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
        """
        @param request DRF 요청 객체 (roadmap_id/period_days 사용).
        @returns 코멘트 다이제스트 JSON.
        """
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
        """
        @param request DRF 요청 객체 (roadmap_id/query/top_k 사용).
        @returns 중복 질문 후보 배열 JSON.
        """
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
        """
        @param request DRF 요청 객체 (query/top_k 사용).
        @returns 자료 추천 결과 JSON.
        """
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
        """
        @param request DRF 요청 객체 (user_id/days 사용).
        @returns 학습 패턴 분석 JSON.
        """
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
        """
        @param request DRF 요청 객체 (query/top_k 사용).
        @returns GraphRAG 컨텍스트 JSON.
        """
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
        """
        @param request DRF 요청 객체 (goal/preferred_tags/max_nodes/compose_level 사용).
        @returns 생성된 로드맵 JSON.
        """
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
        """
        @param request DRF 요청 객체 (user_id/question/compose_level 사용).
        @returns 학습 코치 응답 JSON.
        """
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
        """
        @param request DRF 요청 객체 (target_role/user_id 사용).
        @returns 그래프 기반 로드맵 추천 JSON.
        """
        target_role = request.GET.get("target_role") or "frontend_dev"
        user_id = request.GET.get("user_id") or "user_1"
        payload = _roadmap_recommendation(target_role, user_id)
        return _serialize(RoadmapRecommendationSerializer, payload)


def _resolve_roadmap(roadmap_id: str):
    """
    @param roadmap_id 조회할 로드맵 ID.
    @returns 로드맵 객체 (없으면 기본 로드맵).
    """
    if roadmap_id in mock_data.ROADMAPS:
        return mock_data.ROADMAPS[roadmap_id]
    return next(iter(mock_data.ROADMAPS.values()))


def _resolve_node(roadmap, node_id: str | None):
    """
    @param roadmap 로드맵 객체.
    @param node_id 선택된 노드 ID (없으면 첫 노드 사용).
    @returns 로드맵 노드 객체.
    """
    if node_id:
        for node in roadmap.nodes:
            if node.node_id == node_id:
                return node
    return roadmap.nodes[0]


def _build_record(node, roadmap):
    """
    @param node 대상 로드맵 노드.
    @param roadmap 로드맵 객체.
    @returns 기본 학습 기록 객체(데모용).
    """
    base_record = mock_data.LEARNING_RECORDS[0]
    return LearningRecord(
        record_id=base_record.record_id,
        memo=base_record.memo,
        links=base_record.links,
        node_id=node.node_id,
        roadmap_id=roadmap.roadmap_id,
    )


def _record_feedback(record, node, tags, compose_level: str):
    """
    @param record 학습 기록 객체.
    @param node 로드맵 노드 객체.
    @param tags 로드맵 태그 목록.
    @param compose_level quick/full 출력 단계.
    @returns Record Coach 피드백 JSON.
    """
    return RecordCoachService().get_feedback(record, node, tags, compose_level=compose_level)


def _related_roadmaps(roadmap_id: str):
    """
    @param roadmap_id 기준 로드맵 ID.
    @returns 연관 로드맵 추천 JSON.
    """
    return RelatedRoadmapsService(mock_data.ROADMAPS).generate_snapshot(roadmap_id)


def _tech_card(tech_slug: str):
    """
    @param tech_slug 기술 카드 슬러그.
    @returns 기술 카드 JSON.
    """
    return TechCardService().get_or_create(tech_slug)


def _tech_fingerprint(roadmap, include_rationale: bool):
    """
    @param roadmap 로드맵 객체.
    @param include_rationale rationale 포함 여부.
    @returns 기술 지문 태그 JSON.
    """
    return TechFingerprintService().generate(roadmap, include_rationale=include_rationale)


def _comment_insights(roadmap_id: str, question: str):
    """
    @param roadmap_id 로드맵 ID.
    @param question 사용자 질문.
    @returns (다이제스트, 중복 후보) 튜플.
    """
    service = CommentIntelligenceService()
    digest = service.comment_digest(roadmap_id)
    duplicates = service.duplicate_suggest(roadmap_id, question, top_k=3)
    return digest, duplicates


def _resource_recommendation(query: str, top_k: int):
    """
    @param query 검색 질의.
    @param top_k 추천 개수.
    @returns 자료 추천 JSON.
    """
    return ResourceRecommendationService().recommend(query, top_k=top_k)


def _learning_pattern(user_id: str):
    """
    @param user_id 사용자 ID.
    @returns 학습 패턴 분석 JSON.
    """
    return LearningPatternService().analyze(user_id)


def _roadmap_generated(graph_rag, goal: str, preferred_tags, compose_level: str):
    """
    @param graph_rag GraphRAG 서비스 인스턴스.
    @param goal 생성 목표.
    @param preferred_tags 선호 태그 목록.
    @param compose_level quick/full 출력 단계.
    @returns 생성된 로드맵 JSON.
    """
    return RoadmapGeneratorService(graph_rag=graph_rag).generate(
        goal,
        preferred_tags=preferred_tags,
        compose_level=compose_level,
    )


def _learning_coach(graph_rag, question: str, user_id: str, compose_level: str):
    """
    @param graph_rag GraphRAG 서비스 인스턴스.
    @param question 사용자 질문.
    @param user_id 사용자 ID.
    @param compose_level quick/full 출력 단계.
    @returns 학습 코치 응답 JSON.
    """
    resource_recommender = ResourceRecommendationService()
    return LearningCoachService(graph_rag=graph_rag, resource_recommender=resource_recommender).answer(
        user_id,
        question,
        compose_level=compose_level,
    )


def _roadmap_recommendation(target_role: str, user_id: str):
    """
    @param target_role 목표 역할.
    @param user_id 사용자 ID.
    @returns 그래프 기반 로드맵 추천 JSON.
    """
    return RoadmapRecommendationService(mock_data.ROADMAPS).recommend(target_role, user_id)


def _serialize(serializer_class, payload, many: bool = False) -> Response:
    """
    @param serializer_class 사용할 DRF Serializer 클래스.
    @param payload 응답 데이터.
    @param many 리스트 여부.
    @returns 직렬화된 DRF Response.
    """
    serializer = serializer_class(payload, many=many)
    return Response(serializer.data)


# =============================================================================
# 웹 검색 API (Tavily/Exa)
# =============================================================================

class WebSearchAPIView(APIView):
    """
    웹 검색 API 엔드포인트.

    Tavily와 Exa 검색 엔진을 활용하여 학습 자료를 검색합니다.
    검색 결과는 관련성 점수로 정렬되어 반환됩니다.

    사용 예시:
        GET /api/ai/web-search?query=React%20useEffect%20설명&top_k=5
    """

    @extend_schema(
        summary="웹 검색 (Tavily/Exa)",
        description="Tavily와 Exa 검색 엔진을 사용하여 웹에서 학습 자료를 검색합니다.",
        parameters=[
            OpenApiParameter(
                "query",
                OpenApiTypes.STR,
                required=True,
                description="검색 쿼리 (예: 'Python 비동기 프로그래밍')"
            ),
            OpenApiParameter(
                "top_k",
                OpenApiTypes.INT,
                required=False,
                description="반환할 최대 결과 수 (기본: 5, 최대: 20)"
            ),
            OpenApiParameter(
                "engine",
                OpenApiTypes.STR,
                required=False,
                description="사용할 검색 엔진 (tavily/exa/all, 기본: all)",
                enum=["tavily", "exa", "all"],
            ),
        ],
        responses={200: WebSearchSerializer},
    )
    def get(self, request) -> Response:
        """
        웹 검색 요청을 처리하고 구조화된 검색 결과를 반환합니다.

        @param {Request} request - DRF 요청 객체 (query/top_k/engine 파라미터 포함).
        @returns {Response} 검색 결과를 담은 직렬화된 응답.
        """
        from jagalchi_ai.ai_core.service.retrieval.web_search_service import (
            WebSearchService,
            SearchEngine,
        )

        query = request.GET.get("query", "Python 학습 자료")
        top_k = min(int(request.GET.get("top_k") or 5), 20)
        engine_param = request.GET.get("engine", "all")

        # 검색 엔진 선택
        engine_map = {
            "tavily": SearchEngine.TAVILY,
            "exa": SearchEngine.EXA,
            "all": SearchEngine.ALL,
        }
        engine = engine_map.get(engine_param, SearchEngine.ALL)

        # 검색 수행
        service = WebSearchService()
        result = service.search_with_metadata(query, top_k=top_k)

        payload = {
            "query": result.get("query", query),
            "results": result.get("results", []),
            "generated_at": result.get("generated_at", datetime.utcnow().isoformat()),
            "engines_used": result.get("engines_used", []),
            "total_results": len(result.get("results", [])),
        }

        return _serialize(WebSearchSerializer, payload)


# =============================================================================
# 문서 기반 로드맵 추천 API
# =============================================================================

class DocumentRoadmapAPIView(APIView):
    """
    문서 기반 로드맵 추천 API 엔드포인트.

    사용자가 제공한 문서(이력서, 학습 계획서 등)를 분석하여
    적합한 학습 로드맵을 추천합니다.

    사용 예시:
        POST /api/ai/document-roadmap
        Body: {"document": "저는 Python을 1년간 공부했고..."}
    """

    @extend_schema(
        summary="문서 기반 로드맵 추천",
        description="사용자가 제공한 문서를 AI가 분석하여 맞춤형 학습 로드맵을 추천합니다.",
        parameters=[
            OpenApiParameter(
                "document",
                OpenApiTypes.STR,
                required=False,
                description="분석할 문서 내용 (이력서, 학습 계획 등)"
            ),
            OpenApiParameter(
                "goal",
                OpenApiTypes.STR,
                required=False,
                description="목표 직군/분야 (예: 'Backend Developer')"
            ),
        ],
        responses={200: DocumentRoadmapSerializer},
    )
    def get(self, request) -> Response:
        """
        문서 기반 로드맵 추천을 수행합니다.

        @param {Request} request - DRF 요청 객체 (document/goal 쿼리 파라미터).
        @returns {Response} 추천 결과를 담은 직렬화된 응답.
        """
        document = request.GET.get("document", "")
        goal = request.GET.get("goal", "")

        # 문서 분석 및 키워드 추출
        extracted_keywords = _extract_keywords(document)

        # 관련 로드맵 추천
        graph_rag = GraphRAGService(mock_data.ROADMAPS)
        context = graph_rag.build_context(document or goal or "프로그래밍", top_k=5)

        # 추천 로드맵 생성
        recommended = []
        for i, node in enumerate(context["graph_snapshot"]["nodes"][:3]):
            recommended.append({
                "related_roadmap_id": node["node_id"],
                "score": round(0.95 - (i * 0.1), 2),
                "reasons": [{"type": "keyword_match", "value": node["tags"][:2]}],
            })

        payload = {
            "document_summary": _summarize_document(document) if document else "문서가 제공되지 않았습니다.",
            "extracted_keywords": extracted_keywords,
            "recommended_roadmaps": recommended,
            "suggested_topics": [tag for node in context["graph_snapshot"]["nodes"][:3] for tag in node.get("tags", [])[:2]],
            "model_version": "document_analyzer_v1",
            "created_at": datetime.utcnow().isoformat(),
        }

        return _serialize(DocumentRoadmapSerializer, payload)

    @extend_schema(
        summary="문서 기반 로드맵 추천 (POST)",
        description="문서를 POST body로 제출하여 분석합니다.",
        request={"application/json": {"type": "object", "properties": {"document": {"type": "string"}, "goal": {"type": "string"}}}},
        responses={200: DocumentRoadmapSerializer},
    )
    def post(self, request) -> Response:
        """
        문서 기반 로드맵 추천을 POST Body로 처리합니다.

        @param {Request} request - DRF 요청 객체 (document/goal JSON).
        @returns {Response} 추천 결과를 담은 직렬화된 응답.
        """
        document = request.data.get("document", "")
        goal = request.data.get("goal", "")

        # 문서 분석 및 키워드 추출
        extracted_keywords = _extract_keywords(document)

        # 관련 로드맵 추천
        graph_rag = GraphRAGService(mock_data.ROADMAPS)
        query_text = document[:500] if document else goal if goal else "프로그래밍"
        context = graph_rag.build_context(query_text, top_k=5)

        # 추천 로드맵 생성
        recommended = []
        for i, node in enumerate(context["graph_snapshot"]["nodes"][:3]):
            recommended.append({
                "related_roadmap_id": node["node_id"],
                "score": round(0.95 - (i * 0.1), 2),
                "reasons": [{"type": "keyword_match", "value": node["tags"][:2]}],
            })

        payload = {
            "document_summary": _summarize_document(document) if document else "문서가 제공되지 않았습니다.",
            "extracted_keywords": extracted_keywords,
            "recommended_roadmaps": recommended,
            "suggested_topics": [tag for node in context["graph_snapshot"]["nodes"][:3] for tag in node.get("tags", [])[:2]],
            "model_version": "document_analyzer_v1",
            "created_at": datetime.utcnow().isoformat(),
        }

        return _serialize(DocumentRoadmapSerializer, payload)


# =============================================================================
# 헬스체크 API
# =============================================================================

class HealthCheckAPIView(APIView):
    """
    API 헬스체크 엔드포인트.

    서버 상태 및 각 AI 서비스의 사용 가능 여부를 확인합니다.
    Docker 헬스체크 및 모니터링에 사용됩니다.
    """

    @extend_schema(
        summary="헬스체크",
        description="서버 상태 및 각 AI 서비스의 사용 가능 여부를 확인합니다.",
        responses={200: HealthCheckSerializer},
    )
    def get(self, request) -> Response:
        """
        헬스체크 정보를 반환합니다.

        @param {Request} request - DRF 요청 객체.
        @returns {Response} 서비스 상태를 담은 직렬화된 응답.
        """
        from jagalchi_ai.ai_core.client import GeminiClient, TavilySearchClient, ExaSearchClient

        # 각 서비스 상태 확인
        gemini_available = GeminiClient().available()
        tavily_available = TavilySearchClient().available
        exa_available = ExaSearchClient().available()

        payload = {
            "status": "ok",
            "version": "1.0.0",
            "services": {
                "gemini": gemini_available,
                "tavily": tavily_available,
                "exa": exa_available,
                "graph_rag": True,
                "semantic_cache": True,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        return _serialize(HealthCheckSerializer, payload)


# =============================================================================
# 유틸리티 함수
# =============================================================================

def _extract_keywords(document: str) -> list:
    """
    문서에서 핵심 키워드를 간단 규칙으로 추출합니다.

    @param {str} document - 분석할 문서 텍스트.
    @returns {list} 발견된 키워드 목록.
    """
    if not document:
        return []

    # 간단한 키워드 추출 (실제로는 NLP 모델 활용)
    tech_keywords = [
        "python", "javascript", "java", "react", "django", "flask",
        "machine learning", "deep learning", "ai", "데이터", "백엔드",
        "프론트엔드", "api", "database", "sql", "nosql", "docker",
        "kubernetes", "aws", "cloud", "typescript", "node.js",
    ]

    document_lower = document.lower()
    found = [kw for kw in tech_keywords if kw in document_lower]

    return found[:10] if found else ["general", "programming"]


def _summarize_document(document: str) -> str:
    """
    문서의 앞부분을 기반으로 간단 요약을 생성합니다.

    @param {str} document - 요약 대상 문서.
    @returns {str} 요약 문자열.
    """
    if not document:
        return ""

    # 간단한 요약 (처음 200자)
    summary = document[:200].strip()
    if len(document) > 200:
        summary += "..."

    return f"문서 분석 결과: {summary}"
