from django.urls import path

from drf_spectacular.views import SpectacularAPIView

from jagalchi_ai.ai_core.controller.docs_views import RedocUIView, SwaggerUIView

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
    InitDataDetailAPIView,
    InitDataListCreateAPIView,
    NodeDescriptionAPIView,
    NodeGenerationFromInitAPIView,
    NodeResourceRecommendationAPIView,
    NodeResourceSaveAPIView,
)

urlpatterns = [
    # OpenAPI 스키마 및 문서
    path("ai/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("ai/docs/", SwaggerUIView.as_view(), name="swagger-ui"),
    path("ai/redoc/", RedocUIView.as_view(), name="redoc"),

    # 헬스체크 API
    path("ai/health/", HealthCheckAPIView.as_view(), name="health-check"),

    # AI 데모 API
    path("ai/demo", DemoAIAPIView.as_view()),

    # 학습 코치 관련 API
    path("ai/record-coach", RecordCoachAPIView.as_view()),
    path("ai/learning-coach", LearningCoachAPIView.as_view()),
    path("ai/learning-pattern", LearningPatternAPIView.as_view()),

    # 로드맵 관련 API
    path("ai/related-roadmaps", RelatedRoadmapsAPIView.as_view()),
    path("ai/roadmap-generated", RoadmapGeneratedAPIView.as_view()),
    path("ai/roadmap-recommendation", RoadmapRecommendationAPIView.as_view()),
    path("ai/document-roadmap", DocumentRoadmapAPIView.as_view()),

    # 기술 카드 API
    path("ai/tech-cards", TechCardAPIView.as_view()),
    path("ai/tech-fingerprint", TechFingerprintAPIView.as_view()),

    # 코멘트 관련 API
    path("ai/comment-digest", CommentDigestAPIView.as_view()),
    path("ai/comment-duplicates", CommentDuplicateAPIView.as_view()),

    # 검색 및 추천 API
    path("ai/resource-recommendation", ResourceRecommendationAPIView.as_view()),
    path("ai/web-search", WebSearchAPIView.as_view()),

    # GraphRAG API
    path("ai/graph-rag", GraphRAGAPIView.as_view()),

    # Init Data API
    path("ai/init-data", InitDataListCreateAPIView.as_view()),
    path("ai/init-data/<str:init_data_id>", InitDataDetailAPIView.as_view()),

    # Node Content API
    path("ai/node-generation", NodeGenerationFromInitAPIView.as_view()),
    path("ai/node-description", NodeDescriptionAPIView.as_view()),
    path("ai/node-resource-recommendation", NodeResourceRecommendationAPIView.as_view()),
    path("ai/node-resource-save", NodeResourceSaveAPIView.as_view()),
]
