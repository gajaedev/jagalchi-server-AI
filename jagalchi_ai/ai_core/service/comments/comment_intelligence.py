from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from jagalchi_ai.ai_core.domain.comment import Comment
from jagalchi_ai.ai_core.repository.mock_data import COMMENTS


class CommentIntelligenceService:
    """코멘트 중복/이슈 요약 서비스."""

    def __init__(self, comments: Optional[List[Comment]] = None) -> None:
        """
        코멘트 인텔리전스 서비스를 초기화합니다.

        @param {Optional[List[Comment]]} comments - 분석할 코멘트 목록.
        @returns {None} 내부 인덱스를 구성합니다.
        """
        self._comments = comments or COMMENTS
        self._vectorizer = TfidfVectorizer()
        self._matrix = None
        self._index_comments()

    def duplicate_suggest(self, roadmap_id: str, query: str, top_k: int = 3) -> List[Dict[str, object]]:
        """
        특정 로드맵에서 유사한 질문을 추천합니다.

        @param {str} roadmap_id - 로드맵 식별자.
        @param {str} query - 사용자 입력 질문.
        @param {int} top_k - 반환할 최대 결과 수.
        @returns {List[Dict[str, object]]} 유사 질문 요약 목록.
        """
        roadmap_indices = [idx for idx, c in enumerate(self._comments) if c.roadmap_id == roadmap_id]
        if not roadmap_indices or self._matrix is None:
            return []
        query_vec = self._vectorizer.transform([query])
        subset = self._matrix[roadmap_indices]
        scores = cosine_similarity(query_vec, subset).flatten()
        ranked = sorted(zip(roadmap_indices, scores), key=lambda pair: pair[1], reverse=True)[:top_k]
        return [
            {"comment_id": self._comments[idx].comment_id, "snippet": self._comments[idx].body}
            for idx, _score in ranked
        ]

    def comment_digest(self, roadmap_id: str, period_days: int = 14) -> Dict[str, object]:
        """
        최근 코멘트를 요약하여 하이라이트와 병목을 반환합니다.

        @param {str} roadmap_id - 로드맵 식별자.
        @param {int} period_days - 집계 기간(일).
        @returns {Dict[str, object]} 하이라이트와 병목 점수 페이로드.
        """
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
        """
        TF-IDF 기반으로 코멘트 인덱스를 구성합니다.

        @returns {None} 인덱싱만 수행합니다.
        """
        if not self._comments:
            self._matrix = None
            return
        corpus = [comment.body for comment in self._comments]
        self._matrix = self._vectorizer.fit_transform(corpus)


def _cluster_comments(comments: List[Comment]) -> List[List[Comment]]:
    """
    코멘트를 의미 기반으로 군집화합니다.

    @param {List[Comment]} comments - 코멘트 목록.
    @returns {List[List[Comment]]} 코멘트 클러스터 목록.
    """
    if len(comments) <= 1:
        return [comments] if comments else []
    corpus = [comment.body for comment in comments]
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(corpus).toarray()
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=0.8,
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(vectors)
    grouped: Dict[int, List[Comment]] = defaultdict(list)
    for label, comment in zip(labels, comments):
        grouped[int(label)].append(comment)
    clusters = list(grouped.values())
    clusters.sort(key=lambda group: len(group), reverse=True)
    return clusters


def _bottleneck_scores(comments: List[Comment]) -> List[Dict[str, object]]:
    """
    코멘트 데이터를 기반으로 노드 병목 점수를 계산합니다.

    @param {List[Comment]} comments - 코멘트 목록.
    @returns {List[Dict[str, object]]} 병목 점수 목록.
    """
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
