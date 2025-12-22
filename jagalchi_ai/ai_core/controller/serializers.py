from __future__ import annotations

from rest_framework import serializers


class RetrievalEvidenceSerializer(serializers.Serializer):
    source = serializers.CharField()
    id = serializers.CharField()
    snippet = serializers.CharField()


class RecordCoachScoreSerializer(serializers.Serializer):
    evidence_level = serializers.IntegerField()
    structure_score = serializers.IntegerField()
    specificity_score = serializers.IntegerField()
    reproducibility_score = serializers.IntegerField()
    quality_score = serializers.IntegerField()


class RecordCoachRewriteSerializer(serializers.Serializer):
    portfolio_bullets = serializers.ListField(child=serializers.CharField())
    improved_memo = serializers.CharField(allow_blank=True)


class NextActionSerializer(serializers.Serializer):
    effort = serializers.CharField()
    task = serializers.CharField()


class RecordCoachSerializer(serializers.Serializer):
    record_id = serializers.CharField()
    model_version = serializers.CharField()
    prompt_version = serializers.CharField()
    created_at = serializers.CharField()
    scores = RecordCoachScoreSerializer()
    strengths = serializers.ListField(child=serializers.CharField())
    gaps = serializers.ListField(child=serializers.CharField())
    rewrite_suggestions = RecordCoachRewriteSerializer()
    code_feedback = serializers.JSONField()
    next_actions = NextActionSerializer(many=True)
    followup_questions = serializers.ListField(child=serializers.CharField())
    retrieval_evidence = RetrievalEvidenceSerializer(many=True)


class RelatedRoadmapReasonSerializer(serializers.Serializer):
    type = serializers.CharField()
    value = serializers.JSONField()


class RelatedRoadmapCandidateSerializer(serializers.Serializer):
    related_roadmap_id = serializers.CharField()
    score = serializers.FloatField()
    reasons = RelatedRoadmapReasonSerializer(many=True)


class RelatedRoadmapsSerializer(serializers.Serializer):
    roadmap_id = serializers.CharField()
    generated_at = serializers.CharField()
    candidates = RelatedRoadmapCandidateSerializer(many=True)
    model_version = serializers.CharField()
    evidence_snapshot = serializers.JSONField()


class AlternativeSerializer(serializers.Serializer):
    slug = serializers.CharField()
    why = serializers.CharField()


class LearningPathStageSerializer(serializers.Serializer):
    stage = serializers.CharField()
    items = serializers.ListField(child=serializers.CharField())


class TechCardMetadataSerializer(serializers.Serializer):
    language = serializers.CharField()
    license = serializers.CharField()
    latest_version = serializers.CharField()
    last_updated = serializers.CharField()


class ReliabilityMetricsSerializer(serializers.Serializer):
    community_score = serializers.IntegerField()
    doc_freshness = serializers.IntegerField()
    source_count = serializers.IntegerField()


class LatestChangesSerializer(serializers.Serializer):
    changed = serializers.BooleanField()
    change_ratio = serializers.FloatField()
    summary = serializers.CharField(allow_blank=True)


class ReelEvidenceSerializer(serializers.Serializer):
    query = serializers.CharField()
    snippet = serializers.CharField()


class TechCardSourceSerializer(serializers.Serializer):
    title = serializers.CharField()
    url = serializers.CharField()
    fetched_at = serializers.CharField()


class GeneratedBySerializer(serializers.Serializer):
    model_version = serializers.CharField()
    prompt_version = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class TechCardSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    category = serializers.CharField()
    tech_slug = serializers.CharField()
    version = serializers.CharField()
    summary = serializers.CharField()
    summary_vector = serializers.ListField(child=serializers.FloatField())
    why_it_matters = serializers.ListField(child=serializers.CharField())
    when_to_use = serializers.ListField(child=serializers.CharField())
    alternatives = AlternativeSerializer(many=True)
    pitfalls = serializers.ListField(child=serializers.CharField())
    learning_path = LearningPathStageSerializer(many=True)
    metadata = TechCardMetadataSerializer()
    relationships = serializers.JSONField()
    reliability_metrics = ReliabilityMetricsSerializer()
    latest_changes = LatestChangesSerializer()
    reel_evidence = ReelEvidenceSerializer(many=True)
    sources = TechCardSourceSerializer(many=True)
    generated_by = GeneratedBySerializer()


class TechFingerprintTagSerializer(serializers.Serializer):
    tech_slug = serializers.CharField()
    type = serializers.CharField()
    confidence = serializers.FloatField()
    rationale = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class TechFingerprintSerializer(serializers.Serializer):
    roadmap_id = serializers.CharField()
    tags = TechFingerprintTagSerializer(many=True)
    generated_at = serializers.CharField()
    model_version = serializers.CharField()


class CommentDigestBottleneckSerializer(serializers.Serializer):
    node_id = serializers.CharField()
    score = serializers.FloatField()
    top_topics = serializers.ListField(child=serializers.CharField())


class CommentDigestSerializer(serializers.Serializer):
    roadmap_id = serializers.CharField()
    period = serializers.CharField()
    highlights = serializers.ListField(child=serializers.CharField())
    bottlenecks = CommentDigestBottleneckSerializer(many=True)
    generated_by = GeneratedBySerializer()


class DuplicateSuggestItemSerializer(serializers.Serializer):
    comment_id = serializers.CharField()
    snippet = serializers.CharField()


class ResourceItemSerializer(serializers.Serializer):
    title = serializers.CharField()
    url = serializers.CharField()
    source = serializers.CharField()
    score = serializers.FloatField()


class ResourceRecommendationSerializer(serializers.Serializer):
    query = serializers.CharField()
    generated_at = serializers.CharField()
    items = ResourceItemSerializer(many=True)
    model_version = serializers.CharField()
    retrieval_evidence = RetrievalEvidenceSerializer(many=True)


class LearningPatternSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    period = serializers.CharField()
    patterns = serializers.JSONField()
    recommendations = serializers.ListField(child=serializers.CharField())
    model_version = serializers.CharField()
    generated_at = serializers.CharField()


class GraphNodeSerializer(serializers.Serializer):
    node_id = serializers.CharField()
    text = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())


class GraphEdgeSerializer(serializers.Serializer):
    source = serializers.CharField()
    target = serializers.CharField()
    type = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class GraphSnapshotSerializer(serializers.Serializer):
    nodes = GraphNodeSerializer(many=True)
    edges = GraphEdgeSerializer(many=True)


class GraphRAGContextSerializer(serializers.Serializer):
    retrieval_evidence = RetrievalEvidenceSerializer(many=True)
    graph_snapshot = GraphSnapshotSerializer()


class RoadmapNodeSerializer(serializers.Serializer):
    node_id = serializers.CharField()
    title = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())


class RoadmapEdgeSerializer(serializers.Serializer):
    source = serializers.CharField()
    target = serializers.CharField()
    type = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class RoadmapGeneratedSerializer(serializers.Serializer):
    roadmap_id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    nodes = RoadmapNodeSerializer(many=True)
    edges = RoadmapEdgeSerializer(many=True)
    tags = serializers.ListField(child=serializers.CharField())
    model_version = serializers.CharField()
    prompt_version = serializers.CharField()
    created_at = serializers.CharField()
    retrieval_evidence = RetrievalEvidenceSerializer(many=True)


class LearningCoachSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    question = serializers.CharField()
    intent = serializers.CharField()
    toolchain = serializers.ListField(child=serializers.CharField())
    plan = serializers.ListField(child=serializers.CharField())
    answer = serializers.CharField()
    retrieval_evidence = RetrievalEvidenceSerializer(many=True)
    behavior_summary = serializers.JSONField()
    model_version = serializers.CharField()
    prompt_version = serializers.CharField()
    created_at = serializers.CharField()
    cache_hit = serializers.BooleanField()


class RoadmapRecommendationNodeSerializer(serializers.Serializer):
    node_id = serializers.CharField()
    status = serializers.CharField()


class RoadmapRecommendationSerializer(serializers.Serializer):
    roadmap_id = serializers.CharField()
    target_role = serializers.CharField()
    nodes = RoadmapRecommendationNodeSerializer(many=True)
    edges = RoadmapEdgeSerializer(many=True)
    gnn_predictions = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))
    model_version = serializers.CharField()
    created_at = serializers.CharField()


class DemoMetaSerializer(serializers.Serializer):
    generated_at = serializers.CharField()
    roadmap_id = serializers.CharField()
    tech_slug = serializers.CharField()
    user_id = serializers.CharField()
    compose_level = serializers.CharField()


class DemoResponseSerializer(serializers.Serializer):
    meta = DemoMetaSerializer()
    record_coach = RecordCoachSerializer()
    related_roadmaps = RelatedRoadmapsSerializer()
    tech_card = TechCardSerializer()
    tech_fingerprint = TechFingerprintSerializer()
    comment_digest = CommentDigestSerializer()
    duplicate_suggest = DuplicateSuggestItemSerializer(many=True)
    resource_recommendation = ResourceRecommendationSerializer()
    learning_pattern = LearningPatternSerializer()
    graph_rag_context = GraphRAGContextSerializer()
    roadmap_generated = RoadmapGeneratedSerializer()
    learning_coach = LearningCoachSerializer()
    roadmap_recommendation = RoadmapRecommendationSerializer()
