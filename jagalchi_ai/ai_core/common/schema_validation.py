from typing import Any, Dict, List


class SchemaError(ValueError):
    """스키마 검증 실패."""

    pass


def validate_record_coach_output(payload: Dict[str, Any]) -> None:
    """
    @param payload Record Coach 결과 JSON.
    @returns None
    """
    _require_fields(payload, [
        "record_id",
        "model_version",
        "prompt_version",
        "created_at",
        "scores",
        "strengths",
        "gaps",
        "rewrite_suggestions",
        "next_actions",
        "followup_questions",
        "retrieval_evidence",
    ])
    _require_types(payload["scores"], dict, "scores")
    _require_types(payload["strengths"], list, "strengths")
    _require_types(payload["gaps"], list, "gaps")
    _require_types(payload["rewrite_suggestions"], dict, "rewrite_suggestions")
    _require_types(payload["next_actions"], list, "next_actions")
    _require_types(payload["followup_questions"], list, "followup_questions")
    _require_types(payload["retrieval_evidence"], list, "retrieval_evidence")


def validate_related_roadmaps_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 연관 로드맵 추천 결과 JSON.
    @returns None
    """
    _require_fields(payload, [
        "roadmap_id",
        "generated_at",
        "candidates",
        "model_version",
        "evidence_snapshot",
    ])
    _require_types(payload["candidates"], list, "candidates")


def validate_tech_card_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 기술 카드 결과 JSON.
    @returns None
    """
    _require_fields(payload, [
        "tech_slug",
        "version",
        "summary",
        "why_it_matters",
        "when_to_use",
        "alternatives",
        "pitfalls",
        "learning_path",
        "sources",
        "generated_by",
    ])
    _require_types(payload["why_it_matters"], list, "why_it_matters")
    _require_types(payload["when_to_use"], list, "when_to_use")
    _require_types(payload["alternatives"], list, "alternatives")
    _require_types(payload["pitfalls"], list, "pitfalls")
    _require_types(payload["learning_path"], list, "learning_path")
    _require_types(payload["sources"], list, "sources")


def validate_tech_fingerprint_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 기술 지문 결과 JSON.
    @returns None
    """
    _require_fields(payload, ["roadmap_id", "tags", "generated_at", "model_version"])
    _require_types(payload["tags"], list, "tags")


def validate_comment_digest_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 코멘트 다이제스트 결과 JSON.
    @returns None
    """
    _require_fields(payload, [
        "roadmap_id",
        "period",
        "highlights",
        "bottlenecks",
        "generated_by",
    ])
    _require_types(payload["highlights"], list, "highlights")
    _require_types(payload["bottlenecks"], list, "bottlenecks")


def validate_roadmap_generation_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 로드맵 생성 결과 JSON.
    @returns None
    """
    _require_fields(payload, [
        "roadmap_id",
        "title",
        "description",
        "nodes",
        "edges",
        "tags",
        "model_version",
        "prompt_version",
        "created_at",
        "retrieval_evidence",
    ])
    _require_types(payload["nodes"], list, "nodes")
    _require_types(payload["edges"], list, "edges")
    _require_types(payload["tags"], list, "tags")


def validate_resource_recommendation_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 자료 추천 결과 JSON.
    @returns None
    """
    _require_fields(payload, ["query", "generated_at", "items", "model_version", "retrieval_evidence"])
    _require_types(payload["items"], list, "items")
    _require_types(payload["retrieval_evidence"], list, "retrieval_evidence")


def validate_learning_pattern_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 학습 패턴 분석 결과 JSON.
    @returns None
    """
    _require_fields(payload, ["user_id", "period", "patterns", "recommendations", "model_version", "generated_at"])
    _require_types(payload["patterns"], dict, "patterns")
    _require_types(payload["recommendations"], list, "recommendations")


def validate_learning_coach_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 학습 코치 결과 JSON.
    @returns None
    """
    _require_fields(payload, [
        "user_id",
        "question",
        "intent",
        "toolchain",
        "plan",
        "answer",
        "retrieval_evidence",
        "behavior_summary",
        "model_version",
        "prompt_version",
        "created_at",
        "cache_hit",
    ])
    _require_types(payload["toolchain"], list, "toolchain")
    _require_types(payload["plan"], list, "plan")
    _require_types(payload["retrieval_evidence"], list, "retrieval_evidence")
    _require_types(payload["behavior_summary"], dict, "behavior_summary")


def validate_roadmap_recommendation_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 로드맵 추천 결과 JSON.
    @returns None
    """
    _require_fields(payload, [
        "roadmap_id",
        "target_role",
        "nodes",
        "edges",
        "gnn_predictions",
        "model_version",
        "created_at",
    ])
    _require_types(payload["nodes"], list, "nodes")
    _require_types(payload["edges"], list, "edges")
    _require_types(payload["gnn_predictions"], dict, "gnn_predictions")


def validate_insights_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 인사이트 결과 JSON.
    @returns None
    """
    _require_fields(payload, ["user_id", "target_role", "gap_set", "generated_at"])
    _require_types(payload["gap_set"], list, "gap_set")


def validate_reliability_output(payload: Dict[str, Any]) -> None:
    """
    @param payload 신뢰도 결과 JSON.
    @returns None
    """
    _require_fields(payload, ["user_scores", "generated_at", "model_version"])
    _require_types(payload["user_scores"], dict, "user_scores")


def _require_fields(payload: Dict[str, Any], fields: List[str]) -> None:
    """
    @param payload 점검 대상 JSON.
    @param fields 필수 필드 목록.
    @returns None
    """
    missing = [field for field in fields if field not in payload]
    if missing:
        raise SchemaError(f"Missing fields: {missing}")


def _require_types(value: Any, expected_type: type, field_name: str) -> None:
    """
    @param value 점검 대상 값.
    @param expected_type 기대 타입.
    @param field_name 필드 이름.
    @returns None
    """
    if not isinstance(value, expected_type):
        raise SchemaError(f"Field {field_name} should be {expected_type.__name__}")
