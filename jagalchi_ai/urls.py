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

API_PREFIXES = ("ai", "api")

urlpatterns = []
for prefix in API_PREFIXES:
    # OpenAPI 스키마 및 문서
    urlpatterns.extend(
        [
            path(f"{prefix}/schema/", SpectacularAPIView.as_view(), name=f"schema-{prefix}"),
            path(
                f"{prefix}/docs/",
                SpectacularSwaggerView.as_view(url_name=f"schema-{prefix}"),
                name=f"swagger-ui-{prefix}",
            ),
            path(
                f"{prefix}/redoc/",
                SpectacularRedocView.as_view(url_name=f"schema-{prefix}"),
                name=f"redoc-{prefix}",
            ),
        ]
    )

    # 헬스체크 API
    urlpatterns.append(path(f"{prefix}/health/", HealthCheckAPIView.as_view(), name=f"health-check-{prefix}"))

    # AI 데모 API
    urlpatterns.append(path(f"{prefix}/ai/demo", DemoAIAPIView.as_view()))

    # 학습 코치 관련 API
    urlpatterns.append(path(f"{prefix}/record-coach", RecordCoachAPIView.as_view()))
    urlpatterns.append(path(f"{prefix}/learning-coach", LearningCoachAPIView.as_view()))
    urlpatterns.append(path(f"{prefix}/learning-pattern", LearningPatternAPIView.as_view()))

    # 로드맵 관련 API
    urlpatterns.append(path(f"{prefix}/related-roadmaps", RelatedRoadmapsAPIView.as_view()))
    urlpatterns.append(path(f"{prefix}/roadmap-generated", RoadmapGeneratedAPIView.as_view()))
    urlpatterns.append(path(f"{prefix}/roadmap-recommendation", RoadmapRecommendationAPIView.as_view()))
    urlpatterns.append(path(f"{prefix}/document-roadmap", DocumentRoadmapAPIView.as_view()))

    # 기술 카드 API
    urlpatterns.append(path(f"{prefix}/tech-cards", TechCardAPIView.as_view()))
    urlpatterns.append(path(f"{prefix}/tech-fingerprint", TechFingerprintAPIView.as_view()))

    # 코멘트 관련 API
    urlpatterns.append(path(f"{prefix}/comment-digest", CommentDigestAPIView.as_view()))
    urlpatterns.append(path(f"{prefix}/comment-duplicates", CommentDuplicateAPIView.as_view()))

    # 검색 및 추천 API
    urlpatterns.append(path(f"{prefix}/resource-recommendation", ResourceRecommendationAPIView.as_view()))
    urlpatterns.append(path(f"{prefix}/web-search", WebSearchAPIView.as_view()))

    # GraphRAG API
    urlpatterns.append(path(f"{prefix}/graph-rag", GraphRAGAPIView.as_view()))
