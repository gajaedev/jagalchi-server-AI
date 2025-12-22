from django.urls import path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from jagalchi_ai.ai_core.controller.ai_views import (
    CommentDigestAPIView,
    CommentDuplicateAPIView,
    DemoAIAPIView,
    GraphRAGAPIView,
    LearningCoachAPIView,
    LearningPatternAPIView,
    RecordCoachAPIView,
    RelatedRoadmapsAPIView,
    ResourceRecommendationAPIView,
    RoadmapGeneratedAPIView,
    RoadmapRecommendationAPIView,
    TechCardAPIView,
    TechFingerprintAPIView,
)

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/ai/demo", DemoAIAPIView.as_view()),
    path("api/ai/record-coach", RecordCoachAPIView.as_view()),
    path("api/ai/related-roadmaps", RelatedRoadmapsAPIView.as_view()),
    path("api/ai/tech-cards", TechCardAPIView.as_view()),
    path("api/ai/tech-fingerprint", TechFingerprintAPIView.as_view()),
    path("api/ai/comment-digest", CommentDigestAPIView.as_view()),
    path("api/ai/comment-duplicates", CommentDuplicateAPIView.as_view()),
    path("api/ai/resource-recommendation", ResourceRecommendationAPIView.as_view()),
    path("api/ai/learning-pattern", LearningPatternAPIView.as_view()),
    path("api/ai/graph-rag", GraphRAGAPIView.as_view()),
    path("api/ai/roadmap-generated", RoadmapGeneratedAPIView.as_view()),
    path("api/ai/learning-coach", LearningCoachAPIView.as_view()),
    path("api/ai/roadmap-recommendation", RoadmapRecommendationAPIView.as_view()),
]
