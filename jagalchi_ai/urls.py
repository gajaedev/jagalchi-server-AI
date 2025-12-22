from django.urls import path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from jagalchi_ai.ai_core.controller.ai_views import (
    CommentDigestAPIView,
    CommentDuplicateAPIView,
    DemoAIAPIView,
    DocumentRoadmapAPIView,
    GraphRAGAPIView,
    HealthCheckAPIView,
    LearningCoachAPIView,
    LearningPatternAPIView,
    RecordCoachAPIView,
    RelatedRoadmapsAPIView,
    ResourceRecommendationAPIView,
    RoadmapGeneratedAPIView,
    RoadmapRecommendationAPIView,
    TechCardAPIView,
    TechFingerprintAPIView,
    WebSearchAPIView,
)

urlpatterns = [
    # OpenAPI 스키마 및 문서
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # 헬스체크 API
    path("api/health/", HealthCheckAPIView.as_view(), name="health-check"),

    # AI 데모 API
    path("api/ai/demo", DemoAIAPIView.as_view()),

    # 학습 코치 관련 API
    path("api/ai/record-coach", RecordCoachAPIView.as_view()),
    path("api/ai/learning-coach", LearningCoachAPIView.as_view()),
    path("api/ai/learning-pattern", LearningPatternAPIView.as_view()),

    # 로드맵 관련 API
    path("api/ai/related-roadmaps", RelatedRoadmapsAPIView.as_view()),
    path("api/ai/roadmap-generated", RoadmapGeneratedAPIView.as_view()),
    path("api/ai/roadmap-recommendation", RoadmapRecommendationAPIView.as_view()),
    path("api/ai/document-roadmap", DocumentRoadmapAPIView.as_view()),

    # 기술 카드 API
    path("api/ai/tech-cards", TechCardAPIView.as_view()),
    path("api/ai/tech-fingerprint", TechFingerprintAPIView.as_view()),

    # 코멘트 관련 API
    path("api/ai/comment-digest", CommentDigestAPIView.as_view()),
    path("api/ai/comment-duplicates", CommentDuplicateAPIView.as_view()),

    # 검색 및 추천 API
    path("api/ai/resource-recommendation", ResourceRecommendationAPIView.as_view()),
    path("api/ai/web-search", WebSearchAPIView.as_view()),

    # GraphRAG API
    path("api/ai/graph-rag", GraphRAGAPIView.as_view()),
]

