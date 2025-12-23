from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from jagalchi_ai.ai_core.client import GeminiClient
from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.common.nlp.summarization import map_reduce_summary
from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed, extractive_summary
from jagalchi_ai.ai_core.domain.source_chunk import SourceChunk
from jagalchi_ai.ai_core.domain.vector_item import VectorItem
from jagalchi_ai.ai_core.repository.in_memory_vector_store import InMemoryVectorStore
from jagalchi_ai.ai_core.repository.mock_data import COMMON_PITFALLS, TECH_SOURCES
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore
from jagalchi_ai.ai_core.service.retrieval.web_search_service import WebSearchService
from jagalchi_ai.ai_core.service.tech.doc_watcher import DocWatcher
from jagalchi_ai.ai_core.service.tech.reel_pipeline import ReelPipeline


_ALTERNATIVE_MAP = {
    "react": [
        {"slug": "vue", "why": "학습 난이도가 낮고 템플릿 기반 개발을 선호할 때"},
    ],
    "django": [
        {"slug": "fastapi", "why": "가볍고 빠른 API 서버가 필요할 때"},
    ],
}
_DEFAULT_SOURCE_SCORE = 0.45


class TechCardService:
    """기술 카드 생성/캐시 서비스."""

    def __init__(
        self,
        snapshot_store: Optional[SnapshotStore] = None,
        web_search: Optional[WebSearchService] = None,
        llm_client: Optional[GeminiClient] = None,
    ) -> None:
        """
        기술 카드 생성에 필요한 의존성을 초기화합니다.

        @param {Optional[SnapshotStore]} snapshot_store - 스냅샷 저장소.
        @param {Optional[WebSearchService]} web_search - 웹 검색 서비스.
        @param {Optional[GeminiClient]} llm_client - LLM 클라이언트.
        @returns {None} 내부 서비스 구성을 완료합니다.
        """
        self.snapshot_store = snapshot_store or SnapshotStore()
        self._reel = ReelPipeline()
        self._doc_watcher = DocWatcher()
        self._web_search = web_search or WebSearchService()
        self._llm_client = llm_client or GeminiClient()

    def get_or_create(self, tech_slug: str, prompt_version: str = "tech_card_v1") -> Dict[str, object]:
        """
        기술 카드 스냅샷을 조회하거나 새로 생성합니다.

        @param {str} tech_slug - 기술 식별자.
        @param {str} prompt_version - 프롬프트 버전.
        @returns {Dict[str, object]} 기술 카드 페이로드.
        """
        sources = self._resolve_sources(tech_slug)
        source_hash = self._source_hash(tech_slug, sources)
        snapshot = self.snapshot_store.get_or_create(
            source_hash,
            version=prompt_version,
            builder=lambda: self._compose_card(tech_slug, sources, prompt_version),
            metadata={"tech_slug": tech_slug},
        )
        return snapshot.payload

    def _compose_card(self, tech_slug: str, sources: List[Dict[str, str]], prompt_version: str) -> Dict[str, object]:
        """
        기술 카드 페이로드를 구성합니다.

        @param {str} tech_slug - 기술 식별자.
        @param {List[Dict[str, str]]} sources - 문서 소스 목록.
        @param {str} prompt_version - 프롬프트 버전.
        @returns {Dict[str, object]} 카드 페이로드.
        """
        chunks = self._chunk_sources(tech_slug, sources)
        _ = self._index_chunks(chunks)
        summary = map_reduce_summary([source["content"] for source in sources])
        pitfalls = COMMON_PITFALLS.get(tech_slug, [])
        reel = self._reel.extract(sources)
        change_summary = self._detect_changes(sources)
        reliability_metrics = self._calc_reliability(sources)

        llm_payload = self._compose_card_with_llm(
            tech_slug=tech_slug,
            summary=summary,
            sources=sources,
            pitfalls=pitfalls,
            prompt_version=prompt_version,
        )

        if llm_payload:
            summary = llm_payload["summary"]
            why_it_matters = llm_payload["why_it_matters"]
            when_to_use = llm_payload["when_to_use"]
            alternatives = llm_payload["alternatives"]
            pitfalls = llm_payload["pitfalls"]
            learning_path = llm_payload["learning_path"]
            model_version = llm_payload["model_version"]
        else:
            why_it_matters = [
                "업계 표준에 가까운 사용 사례를 확보할 수 있다",
                "팀 협업과 유지보수에 필요한 패턴을 제공한다",
            ]
            when_to_use = [
                "UI/서비스의 구조를 빠르게 확장해야 할 때",
                "문서와 커뮤니티 리소스가 풍부한 기술을 원할 때",
            ]
            alternatives = _ALTERNATIVE_MAP.get(tech_slug, [])
            learning_path = [
                {"stage": "basic", "items": ["핵심 개념 이해", "기본 예제 구현"]},
                {"stage": "practice", "items": ["작은 기능 단위 프로젝트", "성능/품질 개선"]},
            ]
            model_version = "compose_v1"

        latest_fetch = max((source["fetched_at"] for source in sources), default="2025-01-01")
        payload = {
            "id": f"card_{tech_slug}",
            "name": tech_slug,
            "category": "tech",
            "tech_slug": tech_slug,
            "version": datetime.utcnow().date().isoformat(),
            "summary": summary,
            "summary_vector": cheap_embed(summary),
            "why_it_matters": why_it_matters,
            "when_to_use": when_to_use,
            "alternatives": alternatives,
            "pitfalls": pitfalls,
            "learning_path": learning_path,
            "metadata": {
                "language": reel.metadata.get("language") or "unknown",
                "license": reel.metadata.get("license") or "unknown",
                "latest_version": reel.metadata.get("latest_version") or latest_fetch,
                "last_updated": latest_fetch,
            },
            "relationships": {"based_on": [], "alternatives": _ALTERNATIVE_MAP.get(tech_slug, [])},
            "reliability_metrics": reliability_metrics,
            "latest_changes": change_summary,
            "reel_evidence": reel.evidence,
            "sources": [
                {"title": source["title"], "url": source["url"], "fetched_at": source["fetched_at"]}
                for source in sources
            ],
            "generated_by": {
                "model_version": model_version,
                "prompt_version": prompt_version,
            },
        }
        return payload

    def _resolve_sources(self, tech_slug: str) -> List[Dict[str, str]]:
        """
        로컬/웹 문서를 합쳐 기술 소스를 수집합니다.

        @param {str} tech_slug - 기술 식별자.
        @returns {List[Dict[str, str]]} 소스 목록.
        """
        local_sources = [
            {
                **source,
                "source": "mock",
                "score": source.get("score", _DEFAULT_SOURCE_SCORE),
            }
            for source in TECH_SOURCES.get(tech_slug, [])
        ]
        query = f"{tech_slug} official documentation"
        web_sources = self._web_search.search(
            query,
            top_k=3,
            recency_days=WebSearchService.DEFAULT_RECENCY_DAYS,
        )
        merged = self._dedupe_sources(web_sources + local_sources)
        return merged

    def _source_hash(self, tech_slug: str, sources: List[Dict[str, str]]) -> str:
        """
        기술 카드 소스의 해시 키를 생성합니다.

        @param {str} tech_slug - 기술 식별자.
        @param {List[Dict[str, str]]} sources - 소스 목록.
        @returns {str} 해시 문자열.
        """
        normalized = []
        for source in sources:
            normalized.append(
                {
                    "title": source.get("title", ""),
                    "url": source.get("url", ""),
                    "content": extractive_summary(source.get("content", ""), max_sentences=2),
                }
            )
        normalized.sort(key=lambda item: item["url"] or item["title"])
        return stable_hash_json({"slug": tech_slug, "sources": normalized})

    def _calc_reliability(self, sources: List[Dict[str, str]]) -> Dict[str, object]:
        """
        소스 신뢰도 지표를 계산합니다.

        @param {List[Dict[str, str]]} sources - 소스 목록.
        @returns {Dict[str, object]} 신뢰도 지표.
        """
        if not sources:
            return {"community_score": 40, "doc_freshness": 0, "source_count": 0}
        scores = [float(source.get("score") or _DEFAULT_SOURCE_SCORE) for source in sources]
        avg_score = sum(scores) / max(len(scores), 1)
        freshness_scores = []
        today = datetime.utcnow().date()
        for source in sources:
            fetched_at = source.get("fetched_at") or ""
            try:
                fetched_date = datetime.fromisoformat(fetched_at).date()
            except ValueError:
                continue
            days = (today - fetched_date).days
            freshness_scores.append(max(0, 100 - min(days, 100)))
        doc_freshness = round(sum(freshness_scores) / len(freshness_scores)) if freshness_scores else 50
        community_score = round(min(100, 40 + avg_score * 50 + len(sources) * 3))
        return {
            "community_score": community_score,
            "doc_freshness": doc_freshness,
            "source_count": len(sources),
        }

    def _detect_changes(self, sources: List[Dict[str, str]]) -> Dict[str, object]:
        """
        소스 간 변경사항을 비교합니다.

        @param {List[Dict[str, str]]} sources - 소스 목록.
        @returns {Dict[str, object]} 변경 요약.
        """
        if len(sources) < 2:
            return {"changed": False, "change_ratio": 0.0, "summary": ""}
        before = sources[0]["content"]
        after = sources[-1]["content"]
        change = self._doc_watcher.semantic_diff(before, after)
        return {"changed": change.changed, "change_ratio": change.change_ratio, "summary": change.summary}

    def _chunk_sources(self, tech_slug: str, sources: List[Dict[str, str]], chunk_size: int = 320) -> List[SourceChunk]:
        """
        문서를 청킹하여 벡터 인덱싱용 조각을 만듭니다.

        @param {str} tech_slug - 기술 식별자.
        @param {List[Dict[str, str]]} sources - 소스 목록.
        @param {int} chunk_size - 청크 크기.
        @returns {List[SourceChunk]} 청킹된 조각 목록.
        """
        chunks: List[SourceChunk] = []
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=40)
        for source_idx, source in enumerate(sources):
            documents = splitter.create_documents([source["content"]])
            for chunk_idx, document in enumerate(documents):
                text = document.page_content
                chunk_id = f"{tech_slug}:{source_idx}:{chunk_idx}"
                chunks.append(
                    SourceChunk(
                        chunk_id=chunk_id,
                        text=text,
                        metadata={"source": "tech_card", "tech_slug": tech_slug, "snippet": extractive_summary(text)},
                    )
                )
        return chunks

    def _index_chunks(self, chunks: List[SourceChunk]) -> InMemoryVectorStore:
        """
        청크를 벡터 스토어에 인덱싱합니다.

        @param {List[SourceChunk]} chunks - 청킹된 조각.
        @returns {InMemoryVectorStore} 인덱싱된 벡터 스토어.
        """
        store = InMemoryVectorStore()
        items = [
            VectorItem(
                item_id=chunk.chunk_id,
                vector=cheap_embed(chunk.text),
                metadata={**chunk.metadata, "text": chunk.text},
            )
            for chunk in chunks
        ]
        store.batch_upsert(items)
        return store

    def _dedupe_sources(self, sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        URL 기준으로 중복 소스를 제거합니다.

        @param {List[Dict[str, str]]} sources - 소스 목록.
        @returns {List[Dict[str, str]]} 중복 제거된 소스 목록.
        """
        seen = set()
        deduped = []
        for source in sources:
            url = source.get("url", "")
            if url and url in seen:
                continue
            seen.add(url)
            deduped.append(source)
        return deduped

    def _compose_card_with_llm(
        self,
        tech_slug: str,
        summary: str,
        sources: List[Dict[str, str]],
        pitfalls: List[str],
        prompt_version: str,
    ) -> Optional[Dict[str, object]]:
        """
        LLM을 사용해 기술 카드 본문을 구성합니다.

        @param {str} tech_slug - 기술 식별자.
        @param {str} summary - 기존 요약문.
        @param {List[Dict[str, str]]} sources - 소스 목록.
        @param {List[str]} pitfalls - 기본 주의사항 목록.
        @param {str} prompt_version - 프롬프트 버전.
        @returns {Optional[Dict[str, object]]} LLM 기반 카드 구성 결과.
        """
        if not self._llm_client.available():
            return None

        source_summaries = [
            {
                "title": source.get("title", ""),
                "url": source.get("url", ""),
                "fetched_at": source.get("fetched_at", ""),
                "summary": extractive_summary(source.get("content", ""), max_sentences=2),
            }
            for source in sources
        ]

        prompt = (
            "아래 정보를 참고해서 기술 카드 JSON을 작성해줘. 반드시 JSON만 반환해.\n"
            "키: summary, why_it_matters, when_to_use, alternatives, pitfalls, learning_path\n"
            "- summary: 1~2문장 요약\n"
            "- why_it_matters/when_to_use/pitfalls: 각 2~4개\n"
            "- alternatives: {slug, why} 리스트 (가능하면 1~3개)\n"
            "- learning_path: [{stage, items}] 형태로 basic/practice 2단계 권장\n"
            f"tech_slug: {tech_slug}\n"
            f"기존 요약: {summary}\n"
            f"기본 pitfalls: {pitfalls}\n"
            f"소스 요약: {source_summaries}\n"
            f"기본 대안 후보: {_ALTERNATIVE_MAP.get(tech_slug, [])}\n"
        )

        response = self._llm_client.generate_json(prompt)
        data = response.data if response.data else None
        if not data:
            return None

        normalized = _normalize_card_payload(
            data,
            fallback={
                "summary": summary,
                "why_it_matters": [
                    "업계 표준에 가까운 사용 사례를 확보할 수 있다",
                    "팀 협업과 유지보수에 필요한 패턴을 제공한다",
                ],
                "when_to_use": [
                    "UI/서비스의 구조를 빠르게 확장해야 할 때",
                    "문서와 커뮤니티 리소스가 풍부한 기술을 원할 때",
                ],
                "alternatives": _ALTERNATIVE_MAP.get(tech_slug, []),
                "pitfalls": pitfalls,
                "learning_path": [
                    {"stage": "basic", "items": ["핵심 개념 이해", "기본 예제 구현"]},
                    {"stage": "practice", "items": ["작은 기능 단위 프로젝트", "성능/품질 개선"]},
                ],
            },
        )
        normalized["model_version"] = self._llm_client.model_name
        normalized["prompt_version"] = prompt_version
        return normalized


def _normalize_card_payload(payload: Dict[str, object], fallback: Dict[str, object]) -> Dict[str, object]:
    """
    LLM 응답을 스키마에 맞게 정규화합니다.

    @param {Dict[str, object]} payload - LLM 응답 데이터.
    @param {Dict[str, object]} fallback - 기본값 페이로드.
    @returns {Dict[str, object]} 정규화된 페이로드.
    """
    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = fallback["summary"]

    def _list_of_str(value, default):
        if isinstance(value, list) and all(isinstance(item, str) for item in value) and value:
            return value
        return default

    def _learning_path(value, default):
        if not isinstance(value, list):
            return default
        cleaned = []
        for item in value:
            if not isinstance(item, dict):
                continue
            stage = item.get("stage")
            items = item.get("items")
            if not isinstance(stage, str) or not isinstance(items, list):
                continue
            if not all(isinstance(i, str) for i in items):
                continue
            cleaned.append({"stage": stage, "items": items})
        return cleaned if cleaned else default

    def _alternatives(value, default):
        if not isinstance(value, list):
            return default
        cleaned = []
        for item in value:
            if not isinstance(item, dict):
                continue
            slug = item.get("slug")
            why = item.get("why")
            if isinstance(slug, str) and isinstance(why, str):
                cleaned.append({"slug": slug, "why": why})
        return cleaned if cleaned else default

    return {
        "summary": summary,
        "why_it_matters": _list_of_str(payload.get("why_it_matters"), fallback["why_it_matters"]),
        "when_to_use": _list_of_str(payload.get("when_to_use"), fallback["when_to_use"]),
        "alternatives": _alternatives(payload.get("alternatives"), fallback["alternatives"]),
        "pitfalls": _list_of_str(payload.get("pitfalls"), fallback["pitfalls"]),
        "learning_path": _learning_path(payload.get("learning_path"), fallback["learning_path"]),
    }
