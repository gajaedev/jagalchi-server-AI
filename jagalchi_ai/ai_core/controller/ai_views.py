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
from jagalchi_ai.ai_core.service.roadmap_management.init_data_service import InitDataService
from jagalchi_ai.ai_core.service.content_generation.node_content_service import NodeContentService
from jagalchi_ai.ai_core.controller.serializers import (
    CommentDigestSerializer,
    DemoResponseSerializer,
    DocumentRoadmapSerializer,
    DuplicateSuggestItemSerializer,
    GraphRAGContextSerializer,
    HealthCheckSerializer,
    InitDataCreateSerializer,
    InitDataSerializer,
    InitDataUpdateSerializer,
    LearningCoachSerializer,
    LearningPatternSerializer,
    NodeDescriptionSerializer,
    NodeResourceCreateSerializer,
    NodeResourceSerializer,
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
        summary="AI 데모 통합",
        description=(
            "Jaglachi AI 핵심 기능을 한 번에 호출하는 통합 데모 API입니다. "
            "학습기록 피드백, 연관 로드맵, 기술 카드/태그, 코멘트 인텔리전스, "
            "학습 패턴, GraphRAG, 로드맵 생성/추천, 학습 코치까지 묶어서 반환합니다.\n\n"
            "응답 필드 요약:\n"
            "- record_coach: 학습기록 루브릭/개선안\n"
            "- related_roadmaps: 연관 로드맵 후보\n"
            "- tech_card / tech_fingerprint: 기술 카드 + 태그 지문\n"
            "- comment_digest / duplicate_suggest: 코멘트 요약/중복 질문\n"
            "- resource_recommendation: 자료 추천\n"
            "- learning_pattern: 학습 패턴 분석\n"
            "- graph_rag_context: 그래프 근거\n"
            "- roadmap_generated / roadmap_recommendation: 생성/추천\n"
            "- learning_coach: 학습 코치 응답\n\n"
            "프론트 사용 팁:\n"
            "- 개발 중 대시보드/카드 UI의 샘플 데이터를 한 번에 얻고 싶을 때 사용하세요."
        ),
        parameters=[
            OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=False, description="로드맵 ID (기본: rm_frontend)"),
            OpenApiParameter("tech_slug", OpenApiTypes.STR, required=False, description="기술 카드 슬러그 (기본: react)"),
            OpenApiParameter("user_id", OpenApiTypes.STR, required=False, description="사용자 ID (기본: user_1)"),
            OpenApiParameter("question", OpenApiTypes.STR, required=False, description="질문/검색 문장 (기본 예시 포함)"),
            OpenApiParameter("goal", OpenApiTypes.STR, required=False, description="로드맵 생성 목표 문장"),
            OpenApiParameter("target_role", OpenApiTypes.STR, required=False, description="추천 대상 역할"),
            OpenApiParameter(
                "compose_level",
                OpenApiTypes.STR,
                required=False,
                description="답변 상세 수준 (quick: 캐시/로컬 중심, full: LLM 포함)",
                enum=["quick", "full"],
            ),
            OpenApiParameter(
                "include_rationale",
                OpenApiTypes.BOOL,
                required=False,
                description="태그 rationale 포함 여부 (true/false)",
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
        resource_recommendation = _resource_recommendation(
            question,
            top_k=3,
            recency_days=ResourceRecommendationService.DEFAULT_RECENCY_DAYS,
        )
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
        summary="학습 기록 피드백 (Record Coach)",
        description=(
            "학습 기록을 루브릭으로 점수화하고 개선 포인트/수정 제안을 제공합니다. "
            "compose_level=quick은 점수/질문 중심으로 빠르게 반환하며, "
            "compose_level=full은 LLM 문장화까지 포함합니다.\n\n"
            "응답 필드 요약:\n"
            "- scores: evidence/structure/specificity/reproducibility/quality\n"
            "- strengths/gaps: 장점/보완점 리스트\n"
            "- rewrite_suggestions: 포트폴리오용 문장/메모 개선안\n"
            "- followup_questions: 기록 보완 질문\n"
            "- retrieval_evidence: 근거 스니펫 목록"
        ),
        parameters=[
            OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=False, description="로드맵 ID"),
            OpenApiParameter("node_id", OpenApiTypes.STR, required=False, description="로드맵 노드 ID"),
            OpenApiParameter(
                "compose_level",
                OpenApiTypes.STR,
                required=False,
                description="quick(점수/질문 중심) 또는 full(문장 개선 포함)",
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
        summary="연관 로드맵 추천",
        description=(
            "행동/콘텐츠/그래프 유사도를 종합하여 연관 로드맵 후보를 반환합니다. "
            "LLM 없이 점수 기반으로 랭킹되며, reasons 필드로 추천 근거를 숫자화합니다.\n\n"
            "응답 필드 요약:\n"
            "- candidates: related_roadmap_id/score/reasons\n"
            "- evidence_snapshot: 랭킹 피처 스냅샷\n"
            "- model_version: 랭커 버전"
        ),
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
        summary="기술 카드",
        description=(
            "기술의 요약/사용 시점/대안/주의사항/학습 경로를 카드 형태로 제공합니다. "
            "카드는 소스 해시 기반 스냅샷으로 관리되어 동일 소스면 재생성되지 않습니다.\n\n"
            "응답 필드 요약:\n"
            "- summary/why_it_matters/when_to_use/pitfalls\n"
            "- alternatives: 대안 기술 목록\n"
            "- learning_path: 단계별 학습 제안\n"
            "- sources: 출처 목록 (title/url/fetched_at)"
        ),
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
        summary="기술 지문 자동 태깅",
        description=(
            "로드맵 텍스트에서 핵심 기술을 추출해 core/optional/alternative/deprecated "
            "타입으로 분류합니다. include_rationale=true일 때만 근거 문장을 포함합니다.\n\n"
            "응답 필드 요약:\n"
            "- tags: tech_slug/type/confidence/rationale(optional)\n"
            "- model_version/generated_at: 스냅샷 메타"
        ),
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
        summary="코멘트 다이제스트",
        description=(
            "최근 코멘트에서 이슈 하이라이트와 병목 노드를 요약합니다. "
            "기간(period_days) 기준으로 집계하고, 병목 점수는 질문 수/부정 반응/미해결 비율로 계산됩니다.\n\n"
            "응답 필드 요약:\n"
            "- highlights: 주요 이슈 문장\n"
            "- bottlenecks: node_id/score/top_topics"
        ),
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
        summary="중복 질문 후보",
        description=(
            "질문 작성 시 유사한 기존 질문을 추천합니다. "
            "LLM 없이 벡터 유사도 기반으로 빠르게 후보를 제시합니다.\n\n"
            "응답 필드 요약:\n"
            "- comment_id/snippet 목록"
        ),
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
        summary="학습 자료 추천",
        description=(
            "로컬 지식베이스(BM25/Vector)와 최신 웹 검색 결과를 합쳐 "
            "학습 자료를 추천합니다. 캐시는 쿼리/recency_days 기준으로 저장되며 "
            "응답은 items 배열과 retrieval_evidence를 포함합니다.\n\n"
            "응답 필드 요약:\n"
            "- items: title/url/source/score 목록\n"
            "- retrieval_evidence: 근거 스니펫 목록\n"
            "- model_version, generated_at: 스냅샷 메타데이터\n\n"
            "프론트 사용 팁:\n"
            "- 최신 자료 우선이 필요하면 recency_days를 줄여 호출하세요."
        ),
        parameters=[
            OpenApiParameter("query", OpenApiTypes.STR, required=False, description="검색 질의 (예: 'React hooks 상태 관리')"),
            OpenApiParameter("top_k", OpenApiTypes.INT, required=False, description="추천 개수 (기본 3)"),
            OpenApiParameter(
                "recency_days",
                OpenApiTypes.INT,
                required=False,
                description="최신 자료 기준 기간(일). 기본 30, 0/미지정은 제한 없음",
            ),
        ],
        responses=ResourceRecommendationSerializer,
    )
    def get(self, request) -> Response:
        """
        @param request DRF 요청 객체 (query/top_k/recency_days 사용).
        @returns 자료 추천 결과 JSON.
        """
        query = request.GET.get("query") or "React useEffect 에러 해결 방법"
        top_k = int(request.GET.get("top_k") or 3)
        recency_days_param = request.GET.get("recency_days")
        recency_days = (
            int(recency_days_param)
            if recency_days_param is not None
            else ResourceRecommendationService.DEFAULT_RECENCY_DAYS
        )
        payload = _resource_recommendation(query, top_k, recency_days)
        return _serialize(ResourceRecommendationSerializer, payload)


class LearningPatternAPIView(APIView):
    """학습 패턴 응답."""

    @extend_schema(
        summary="학습 패턴 분석",
        description=(
            "학습 이벤트 로그를 기반으로 활동 일수, 평균 세션 간격, 완료 속도 등을 요약합니다. "
            "캐시 스냅샷으로 동일 입력에 대해 빠르게 응답합니다.\n\n"
            "응답 필드 요약:\n"
            "- patterns: active_days/avg_session_gap_days/completion_velocity\n"
            "- recommendations: 학습 패턴 개선 제안"
        ),
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
        summary="GraphRAG 컨텍스트",
        description=(
            "그래프 기반 RAG 검색 결과를 반환합니다. "
            "근거 스니펫과 그래프 스냅샷(nodes/edges)을 함께 제공하여 "
            "추천/요약/설명 UI의 근거로 사용할 수 있습니다.\n\n"
            "응답 필드 요약:\n"
            "- retrieval_evidence: source/id/snippet\n"
            "- graph_snapshot: nodes/edges"
        ),
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
        summary="로드맵 생성",
        description=(
            "목표(goal)와 선호 태그를 기반으로 로드맵을 생성합니다. "
            "compose_level=quick은 규칙 기반으로, full은 LLM 문장화를 포함합니다.\n\n"
            "응답 필드 요약:\n"
            "- nodes/edges/tags: 생성된 로드맵 구성 요소\n"
            "- retrieval_evidence: 생성 근거 스니펫"
        ),
        parameters=[
            OpenApiParameter("goal", OpenApiTypes.STR, required=False, description="목표"),
            OpenApiParameter("preferred_tags", OpenApiTypes.STR, required=False, description="태그(콤마 구분)"),
            OpenApiParameter("max_nodes", OpenApiTypes.INT, required=False, description="노드 개수"),
            OpenApiParameter(
                "compose_level",
                OpenApiTypes.STR,
                required=False,
                description="quick(규칙 기반) 또는 full(LLM 문장화 포함)",
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
        summary="학습 코치 Q&A",
        description=(
            "질문 의도 분류 → 도구 실행 → 답변 구성의 멀티스테이지 학습 코치 응답입니다. "
            "compose_level=quick은 캐시/로컬 요약 중심, full은 LLM 정제까지 포함합니다.\n\n"
            "응답 필드 요약:\n"
            "- intent/toolchain/plan: 의도와 실행 계획\n"
            "- answer: 최종 답변\n"
            "- retrieval_evidence: 근거 스니펫\n"
            "- behavior_summary: 동기/능력/이탈 위험도"
        ),
        parameters=[
            OpenApiParameter("user_id", OpenApiTypes.STR, required=False, description="사용자 ID"),
            OpenApiParameter("question", OpenApiTypes.STR, required=False, description="질문"),
            OpenApiParameter(
                "compose_level",
                OpenApiTypes.STR,
                required=False,
                description="quick(캐시/로컬 중심) 또는 full(LLM 정제 포함)",
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
        summary="그래프 기반 로드맵 추천",
        description=(
            "목표 역할과 강조 태그를 기준으로 그래프 온톨로지에서 "
            "학습 순서를 추천합니다. GNN 예측 결과도 함께 제공합니다.\n\n"
            "응답 필드 요약:\n"
            "- nodes: node_id/status\n"
            "- edges: 그래프 엣지\n"
            "- gnn_predictions: 다음 학습 후보"
        ),
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


def _resource_recommendation(query: str, top_k: int, recency_days: int | None):
    """
    @param query 검색 질의.
    @param top_k 추천 개수.
    @param recency_days 최신 자료 필터 기간(일).
    @returns 자료 추천 JSON.
    """
    return ResourceRecommendationService().recommend(query, top_k=top_k, recency_days=recency_days)


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
        description=(
            "Tavily(웹 검색) + Exa(시맨틱 검색)을 조합해 최신 학습 자료를 수집합니다. "
            "기본적으로 최근 N일(기본 30일) 내 문서를 우선하며, 엔진 선택과 기간 필터를 "
            "파라미터로 제어할 수 있습니다.\n\n"
            "응답 필드 요약:\n"
            "- results: title/url/content/score/source/fetched_at\n"
            "- engines_used: 실제 사용된 엔진 목록\n"
            "- generated_at: 스냅샷 생성 시각\n\n"
            "프론트 사용 팁:\n"
            "- 최신성 강조: recency_days를 7~30으로 설정\n"
            "- 출처 다양성: engine=all 권장"
        ),
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
            OpenApiParameter(
                "recency_days",
                OpenApiTypes.INT,
                required=False,
                description="최신 자료 기준 기간(일). 기본 30, 0/미지정은 제한 없음",
            ),
        ],
        responses={200: WebSearchSerializer},
    )
    def get(self, request) -> Response:
        """
        웹 검색 요청을 처리하고 구조화된 검색 결과를 반환합니다.

        @param {Request} request - DRF 요청 객체 (query/top_k/engine/recency_days 파라미터 포함).
        @returns {Response} 검색 결과를 담은 직렬화된 응답.
        """
        from jagalchi_ai.ai_core.service.retrieval.web_search_service import (
            WebSearchService,
            SearchEngine,
        )

        query = request.GET.get("query", "Python 학습 자료")
        top_k = min(int(request.GET.get("top_k") or 5), 20)
        engine_param = request.GET.get("engine", "all")
        recency_days_param = request.GET.get("recency_days")

        # 검색 엔진 선택
        engine_map = {
            "tavily": SearchEngine.TAVILY,
            "exa": SearchEngine.EXA,
            "all": SearchEngine.ALL,
        }
        engine = engine_map.get(engine_param, SearchEngine.ALL)

        # 검색 수행
        service = WebSearchService()
        search_kwargs = {"query": query, "top_k": top_k, "engine": engine}
        if recency_days_param is not None:
            search_kwargs["recency_days"] = int(recency_days_param)
        result = service.search_with_metadata(**search_kwargs)

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
        description=(
            "이력서/학습계획서 등 문서를 분석해 키워드와 관련 로드맵을 추천합니다. "
            "문서 요약, 추출 키워드, 추천 근거를 함께 반환합니다.\n\n"
            "응답 필드 요약:\n"
            "- document_summary: 문서 요약\n"
            "- extracted_keywords: 핵심 키워드\n"
            "- recommended_roadmaps: 추천 로드맵 목록\n"
            "- suggested_topics: 후속 학습 주제"
        ),
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
        description=(
            "문서를 JSON body로 제출해 분석합니다. GET과 동일한 스키마를 반환하며, "
            "길이가 긴 문서는 POST를 권장합니다."
        ),
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
        description=(
            "서버 상태 및 외부 AI 서비스 연결 가능 여부를 반환합니다. "
            "모니터링/배포 시 서비스 가용성 체크에 사용하세요.\n\n"
            "응답 필드 요약:\n"
            "- services: gemini/tavily/exa/graph_rag/semantic_cache 사용 가능 여부\n"
            "- timestamp: 체크 시각"
        ),
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


# =============================================================================
# Init Data 관리 API
# =============================================================================

class InitDataListCreateAPIView(APIView):
    """Init Data 목록 조회 및 생성 API."""

    @extend_schema(
        summary="Init Data 목록 조회",
        parameters=[OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=True, description="로드맵 ID")],
        responses={200: InitDataSerializer(many=True)},
    )
    def get(self, request) -> Response:
        roadmap_id = request.GET.get("roadmap_id")
        if not roadmap_id:
            return Response({"error": "roadmap_id required"}, status=400)
        
        service = InitDataService()
        data = service.get_list_by_roadmap(roadmap_id)
        return _serialize(InitDataSerializer, data, many=True)

    @extend_schema(
        summary="Init Data 생성 (업로드/입력)",
        request=InitDataCreateSerializer,
        responses={201: InitDataSerializer},
    )
    def post(self, request) -> Response:
        serializer = InitDataCreateSerializer(data=request.data)
        if serializer.is_valid():
            service = InitDataService()
            result = service.create_init_data(**serializer.validated_data)
            return _serialize(InitDataSerializer, result)
        return Response(serializer.errors, status=400)


class InitDataDetailAPIView(APIView):
    """Init Data 상세 조회, 수정, 삭제 API."""

    @extend_schema(summary="Init Data 상세 조회", responses={200: InitDataSerializer})
    def get(self, request, init_data_id) -> Response:
        service = InitDataService()
        data = service.get_init_data(init_data_id)
        if not data:
            return Response({"error": "Not found"}, status=404)
        return _serialize(InitDataSerializer, data)

    @extend_schema(summary="Init Data 수정", request=InitDataUpdateSerializer, responses={200: InitDataSerializer})
    def put(self, request, init_data_id) -> Response:
        serializer = InitDataUpdateSerializer(data=request.data)
        if serializer.is_valid():
            service = InitDataService()
            result = service.update_init_data(init_data_id, serializer.validated_data["content"])
            if not result:
                return Response({"error": "Not found"}, status=404)
            return _serialize(InitDataSerializer, result)
        return Response(serializer.errors, status=400)

    @extend_schema(summary="Init Data 삭제", responses={204: None})
    def delete(self, request, init_data_id) -> Response:
        service = InitDataService()
        if service.delete_init_data(init_data_id):
            return Response(status=204)
        return Response({"error": "Not found"}, status=404)


# =============================================================================
# 노드 콘텐츠 생성 및 리소스 API
# =============================================================================

class NodeGenerationFromInitAPIView(APIView):
    """Init 데이터 기반 노드 생성 API."""

    @extend_schema(
        summary="Init 데이터 기반 노드 생성",
        parameters=[OpenApiParameter("init_data_id", OpenApiTypes.STR, required=True)],
        responses={200: RoadmapGeneratedSerializer},
    )
    def get(self, request) -> Response:
        init_data_id = request.GET.get("init_data_id")
        if not init_data_id:
            return Response({"error": "init_data_id required"}, status=400)
        
        service = NodeContentService()
        try:
            result = service.generate_nodes_from_init(init_data_id)
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=404)


class NodeDescriptionAPIView(APIView):
    """노드 설명 생성 API."""

    @extend_schema(
        summary="AI 노드 설명 생성",
        parameters=[
            OpenApiParameter("node_title", OpenApiTypes.STR, required=True),
            OpenApiParameter("context", OpenApiTypes.STR, required=False),
        ],
        responses={200: NodeDescriptionSerializer},
    )
    def get(self, request) -> Response:
        node_title = request.GET.get("node_title")
        context = request.GET.get("context")
        
        service = NodeContentService()
        description = service.generate_node_description(node_title, context)
        
        return Response({
            "node_title": node_title,
            "description": description,
            "generated_at": datetime.utcnow()
        })


class NodeResourceRecommendationAPIView(APIView):
    """노드 기반 자료 추천 API."""

    @extend_schema(
        summary="노드 주제 기반 자료 추천",
        parameters=[
            OpenApiParameter("node_id", OpenApiTypes.STR, required=True),
            OpenApiParameter("roadmap_id", OpenApiTypes.STR, required=True),
        ],
        responses={200: ResourceRecommendationSerializer},
    )
    def get(self, request) -> Response:
        node_id = request.GET.get("node_id")
        roadmap_id = request.GET.get("roadmap_id")
        
        service = NodeContentService()
        result = service.recommend_resources_for_node(node_id, roadmap_id)
        return _serialize(ResourceRecommendationSerializer, result)


class NodeResourceSaveAPIView(APIView):
    """추천 자료 노드 저장 API."""

    @extend_schema(
        summary="추천 자료 노드에 저장",
        request=NodeResourceCreateSerializer,
        responses={201: NodeResourceSerializer},
    )
    def post(self, request) -> Response:
        serializer = NodeResourceCreateSerializer(data=request.data)
        if serializer.is_valid():
            service = NodeContentService()
            result = service.save_resource_to_node(**serializer.validated_data)
            return Response(_serialize(NodeResourceSerializer, result).data, status=201)
        return Response(serializer.errors, status=400)

