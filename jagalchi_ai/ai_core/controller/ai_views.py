from __future__ import annotations

from datetime import datetime
from typing import Dict

from django.http import JsonResponse
from django.views.decorators.http import require_GET

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


@require_GET
def demo_ai(request) -> JsonResponse:
    """전체 AI 기능을 한 번에 확인하는 데모 엔드포인트."""
    roadmap_id = request.GET.get("roadmap_id") or "rm_frontend"
    tech_slug = request.GET.get("tech_slug") or "react"
    user_id = request.GET.get("user_id") or "user_1"
    question = request.GET.get("question") or "React useEffect 에러 해결 방법"
    goal = request.GET.get("goal") or "프론트엔드 심화"
    target_role = request.GET.get("target_role") or "frontend_dev"
    compose_level = request.GET.get("compose_level") or "quick"
    include_rationale = request.GET.get("include_rationale") == "true"

    roadmap = _resolve_roadmap(roadmap_id)
    node = roadmap.nodes[0]
    base_record = mock_data.LEARNING_RECORDS[0]
    record = LearningRecord(
        record_id=base_record.record_id,
        memo=base_record.memo,
        links=base_record.links,
        node_id=node.node_id,
        roadmap_id=roadmap.roadmap_id,
    )

    record_coach = RecordCoachService()
    record_feedback = record_coach.get_feedback(record, node, roadmap.tags, compose_level=compose_level)

    related_service = RelatedRoadmapsService(mock_data.ROADMAPS)
    related_roadmaps = related_service.generate_snapshot(roadmap.roadmap_id)

    tech_card = TechCardService().get_or_create(tech_slug)
    tech_fingerprint = TechFingerprintService().generate(roadmap, include_rationale=include_rationale)

    comment_service = CommentIntelligenceService()
    comment_digest = comment_service.comment_digest(roadmap.roadmap_id)
    duplicate_suggest = comment_service.duplicate_suggest(roadmap.roadmap_id, question, top_k=3)

    resource_recommender = ResourceRecommendationService()
    resource_recommendation = resource_recommender.recommend(question, top_k=3)

    learning_pattern = LearningPatternService().analyze(user_id)

    graph_rag = GraphRAGService(mock_data.ROADMAPS)
    graph_context = graph_rag.build_context(question, top_k=3)

    roadmap_generator = RoadmapGeneratorService(graph_rag=graph_rag)
    roadmap_generated = roadmap_generator.generate(
        goal,
        preferred_tags=roadmap.tags[:2],
        compose_level=compose_level,
    )

    learning_coach = LearningCoachService(graph_rag=graph_rag, resource_recommender=resource_recommender)
    learning_coach_answer = learning_coach.answer(user_id, question, compose_level=compose_level)

    roadmap_recommender = RoadmapRecommendationService(mock_data.ROADMAPS)
    roadmap_recommendation = roadmap_recommender.recommend(target_role, user_id)

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
    return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})


def _resolve_roadmap(roadmap_id: str):
    if roadmap_id in mock_data.ROADMAPS:
        return mock_data.ROADMAPS[roadmap_id]
    return next(iter(mock_data.ROADMAPS.values()))
