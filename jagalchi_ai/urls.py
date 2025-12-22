from django.urls import path

from jagalchi_ai.ai_core.controller.ai_views import demo_ai

urlpatterns = [
    path("api/ai/demo", demo_ai),
]
