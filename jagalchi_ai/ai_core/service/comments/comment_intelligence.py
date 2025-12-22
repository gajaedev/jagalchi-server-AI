from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed, jaccard_similarity, tokenize
from jagalchi_ai.ai_core.domain.comment import Comment
from jagalchi_ai.ai_core.repository.in_memory_vector_store import InMemoryVectorStore
from jagalchi_ai.ai_core.repository.mock_data import COMMENTS


class CommentIntelligenceService:
    """코멘트 중복/이슈 요약 서비스."""

    def __init__(self, comments: Optional[List[Comment]] = None) -> None:
        self._comments = comments or COMMENTS
        self._vector_store = InMemoryVectorStore()
        self._index_comments()

    def duplicate_suggest(self, roadmap_id: str, query: str, top_k: int = 3) -> List[Dict[str, object]]:
        vector = cheap_embed(query)
        items = self._vector_store.query(vector, top_k=top_k, filters={"roadmap_id": roadmap_id})
        return [
            {"comment_id": item.item_id, "snippet": item.metadata.get("snippet", "")}
            for item in items
        ]

    def comment_digest(self, roadmap_id: str, period_days: int = 14) -> Dict[str, object]:
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        comments = [c for c in self._comments if c.roadmap_id == roadmap_id and c.created_at and c.created_at >= cutoff]
        clusters = _cluster_comments(comments)
        highlights = [cluster[0].body for cluster in clusters if cluster]
        bottlenecks = _bottleneck_scores(comments)

        return {
            "roadmap_id": roadmap_id,
            "period": f"last_{period_days}d",
            "highlights": highlights,
            "bottlenecks": bottlenecks,
            "generated_by": {"model_version": "digest_v1"},
        }

    def _index_comments(self) -> None:
        for comment in self._comments:
            vector = cheap_embed(comment.body)
            self._vector_store.upsert(
                comment.comment_id,
                vector=vector,
                metadata={"roadmap_id": comment.roadmap_id, "snippet": comment.body},
            )


def _cluster_comments(comments: List[Comment], threshold: float = 0.4) -> List[List[Comment]]:
    clusters: List[List[Comment]] = []
    for comment in comments:
        tokens = tokenize(comment.body)
        placed = False
        for cluster in clusters:
            rep = cluster[0]
            # 대표 문장과의 유사도로 간단히 클러스터링한다.
            similarity = jaccard_similarity(tokens, tokenize(rep.body))
            if similarity >= threshold:
                cluster.append(comment)
                placed = True
                break
        if not placed:
            clusters.append([comment])
    clusters.sort(key=lambda c: len(c), reverse=True)
    return clusters


def _bottleneck_scores(comments: List[Comment]) -> List[Dict[str, object]]:
    node_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "negative": 0, "unresolved": 0})
    for comment in comments:
        if not comment.node_id:
            continue
        stats = node_stats[comment.node_id]
        stats["count"] += 1
        stats["negative"] += comment.reactions_negative
        stats["unresolved"] += 0 if comment.resolved else 1

    results = []
    for node_id, stats in node_stats.items():
        count = stats["count"]
        negative_ratio = stats["negative"] / max(count, 1)
        unresolved_ratio = stats["unresolved"] / max(count, 1)
        score = round(min(1.0, (count * 0.3 + negative_ratio * 0.4 + unresolved_ratio * 0.3)), 2)
        results.append({"node_id": node_id, "score": score, "top_topics": ["질문 빈도 증가"]})

    results.sort(key=lambda item: item["score"], reverse=True)
    return results
