from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from jagalchi_ai.ai_core.client import GeminiClient
from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary
from jagalchi_ai.ai_core.domain.comment import Comment
from jagalchi_ai.ai_core.repository.mock_data import COMMENTS
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore


class CommentIntelligenceService:
    """코멘트 중복/이슈 요약 서비스."""

    def __init__(
        self,
        comments: Optional[List[Comment]] = None,
        snapshot_store: Optional[SnapshotStore] = None,
        llm_client: Optional[GeminiClient] = None,
    ) -> None:
        """
        코멘트 인텔리전스 서비스를 초기화합니다.

        @param {Optional[List[Comment]]} comments - 분석할 코멘트 목록.
        @param {Optional[SnapshotStore]} snapshot_store - 스냅샷 저장소.
        @param {Optional[GeminiClient]} llm_client - LLM 클라이언트.
        @returns {None} 내부 인덱스를 구성합니다.
        """
        self._comments = comments or COMMENTS
        self._snapshot_store = snapshot_store or SnapshotStore()
        self._llm_client = llm_client or GeminiClient()
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

    def comment_digest(
        self,
        roadmap_id: str,
        period_days: int = 14,
        prompt_version: str = "comment_digest_v1",
    ) -> Dict[str, object]:
        """
        최근 코멘트를 요약하여 하이라이트와 병목을 반환합니다.

        @param {str} roadmap_id - 로드맵 식별자.
        @param {int} period_days - 집계 기간(일).
        @param {str} prompt_version - 프롬프트 버전.
        @returns {Dict[str, object]} 하이라이트와 병목 점수 페이로드.
        """
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        comments = [c for c in self._comments if c.roadmap_id == roadmap_id and c.created_at and c.created_at >= cutoff]
        cache_key = stable_hash_json(
            {
                "roadmap_id": roadmap_id,
                "period_days": period_days,
                "comments": _digest_signature(comments),
            }
        )
        snapshot = self._snapshot_store.get_or_create(
            cache_key,
            version=prompt_version,
            builder=lambda: self._build_digest_payload(roadmap_id, period_days, comments, prompt_version),
            metadata={"roadmap_id": roadmap_id},
        )
        return snapshot.payload

    def _build_digest_payload(
        self,
        roadmap_id: str,
        period_days: int,
        comments: List[Comment],
        prompt_version: str,
    ) -> Dict[str, object]:
        """
        코멘트 다이제스트 결과 페이로드를 구성합니다.

        @param {str} roadmap_id - 로드맵 식별자.
        @param {int} period_days - 집계 기간(일).
        @param {List[Comment]} comments - 필터된 코멘트 목록.
        @param {str} prompt_version - 프롬프트 버전.
        @returns {Dict[str, object]} 하이라이트/병목 페이로드.
        """
        clusters = _cluster_comments(comments)
        highlight_candidates = _extract_highlight_candidates(clusters, max_items=8)
        highlights, model_version = self._refine_highlights(
            roadmap_id,
            period_days,
            highlight_candidates,
            comments,
            prompt_version,
        )
        bottlenecks = _bottleneck_scores(comments)

        generated_by = {"model_version": model_version}
        if prompt_version:
            generated_by["prompt_version"] = prompt_version

        return {
            "roadmap_id": roadmap_id,
            "period": f"last_{period_days}d",
            "highlights": highlights,
            "bottlenecks": bottlenecks,
            "generated_by": generated_by,
        }

    def _refine_highlights(
        self,
        roadmap_id: str,
        period_days: int,
        highlight_candidates: List[str],
        comments: List[Comment],
        prompt_version: str,
    ) -> tuple[List[str], str]:
        """
        LLM을 사용해 하이라이트 문장을 정제합니다.

        @param {str} roadmap_id - 로드맵 식별자.
        @param {int} period_days - 집계 기간(일).
        @param {List[str]} highlight_candidates - 후보 하이라이트 문장.
        @param {List[Comment]} comments - 코멘트 목록.
        @param {str} prompt_version - 프롬프트 버전.
        @returns {tuple[List[str], str]} (하이라이트, 모델 버전).
        """
        if not highlight_candidates:
            return [], "digest_v1"
        if not self._llm_client.available():
            return highlight_candidates, "digest_v1"

        comment_summaries = [
            extractive_summary(comment.body, max_sentences=1)
            for comment in comments
        ]
        comment_summaries = [summary for summary in comment_summaries if summary][:12]
        prompt = _build_digest_prompt(
            roadmap_id,
            period_days,
            highlight_candidates,
            comment_summaries,
            prompt_version,
        )
        response = self._llm_client.generate_json(prompt)
        if response.data and _valid_highlight_payload(response.data):
            highlights = _normalize_highlights(response.data["highlights"], highlight_candidates)
            return highlights, self._llm_client.model_name
        return highlight_candidates, "digest_v1"

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


def _digest_signature(comments: List[Comment]) -> List[Dict[str, str]]:
    """
    코멘트 집계를 위한 해시 시그니처를 생성합니다.

    @param {List[Comment]} comments - 코멘트 목록.
    @returns {List[Dict[str, str]]} 해시 입력용 시그니처.
    """
    signature = []
    for comment in comments:
        signature.append(
            {
                "comment_id": comment.comment_id,
                "created_at": comment.created_at.isoformat() if comment.created_at else "",
                "body": comment.body,
            }
        )
    signature.sort(key=lambda item: item["comment_id"])
    return signature


def _extract_highlight_candidates(clusters: List[List[Comment]], max_items: int = 6) -> List[str]:
    """
    클러스터에서 대표 하이라이트 후보를 추출합니다.

    @param {List[List[Comment]]} clusters - 코멘트 클러스터 목록.
    @param {int} max_items - 최대 후보 개수.
    @returns {List[str]} 하이라이트 후보 목록.
    """
    highlights = []
    for cluster in clusters:
        if not cluster:
            continue
        summary = extractive_summary(cluster[0].body, max_sentences=1)
        if summary:
            highlights.append(summary)
    deduped = list(dict.fromkeys(highlights))
    return deduped[:max_items]


def _build_digest_prompt(
    roadmap_id: str,
    period_days: int,
    highlight_candidates: List[str],
    comment_summaries: List[str],
    prompt_version: str,
) -> str:
    """
    LLM에 전달할 코멘트 다이제스트 프롬프트를 구성합니다.

    @param {str} roadmap_id - 로드맵 식별자.
    @param {int} period_days - 집계 기간(일).
    @param {List[str]} highlight_candidates - 후보 하이라이트 문장.
    @param {List[str]} comment_summaries - 요약된 코멘트 문장.
    @param {str} prompt_version - 프롬프트 버전.
    @returns {str} 프롬프트 문자열.
    """
    return (
        "다음 코멘트 요약 후보를 중복 없이 2~5개의 하이라이트 문장으로 정리해. "
        "반드시 JSON만 반환하고 키는 highlights만 사용해.\n"
        f"roadmap_id: {roadmap_id}\n"
        f"period_days: {period_days}\n"
        f"후보 문장: {highlight_candidates}\n"
        f"코멘트 요약: {comment_summaries}\n"
        f"prompt_version: {prompt_version}\n"
    )


def _valid_highlight_payload(payload: Dict[str, object]) -> bool:
    """
    하이라이트 페이로드 스키마를 검증합니다.

    @param {Dict[str, object]} payload - LLM 응답 데이터.
    @returns {bool} 유효성 여부.
    """
    highlights = payload.get("highlights")
    if not isinstance(highlights, list) or not highlights:
        return False
    if not all(isinstance(item, str) and item.strip() for item in highlights):
        return False
    return True


def _normalize_highlights(highlights: List[str], fallback: List[str]) -> List[str]:
    """
    하이라이트 문장을 정규화합니다.

    @param {List[str]} highlights - LLM 응답 하이라이트.
    @param {List[str]} fallback - 기본 하이라이트 목록.
    @returns {List[str]} 정규화된 하이라이트 목록.
    """
    cleaned = [item.strip() for item in highlights if isinstance(item, str) and item.strip()]
    if not cleaned:
        return fallback
    deduped = list(dict.fromkeys(cleaned))
    return deduped
