from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.client import GeminiClient
from jagalchi_ai.ai_core.common.hashing import stable_hash_json
from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed, extractive_summary
from jagalchi_ai.ai_core.config.model_router import ModelRouter
from jagalchi_ai.ai_core.domain.document import Document
from jagalchi_ai.ai_core.domain.learning_record import LearningRecord
from jagalchi_ai.ai_core.domain.retrieval_item import RetrievalItem
from jagalchi_ai.ai_core.domain.roadmap_node import RoadmapNode
from jagalchi_ai.ai_core.repository.in_memory_vector_store import InMemoryVectorStore
from jagalchi_ai.ai_core.repository.mock_data import COMMON_PITFALLS, GOOD_RECORD_EXAMPLES, TECH_SOURCES
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore
from jagalchi_ai.ai_core.service.record.code_feedback import analyze_code
from jagalchi_ai.ai_core.service.record.rubric import score_record
from jagalchi_ai.ai_core.service.retrieval.bm25_index import BM25Index
from jagalchi_ai.ai_core.service.retrieval.hybrid_retriever import HybridRetriever
from jagalchi_ai.ai_core.service.retrieval.vector_retriever import VectorRetriever


class RecordCoachService:
    """학습 기록 피드백 생성 서비스."""

    def __init__(
        self,
        snapshot_store: Optional[SnapshotStore] = None,
        retriever: Optional[HybridRetriever] = None,
        model_router: Optional[ModelRouter] = None,
        llm_client: Optional[GeminiClient] = None,
    ) -> None:
        self.snapshot_store = snapshot_store or SnapshotStore()
        self.model_router = model_router or ModelRouter()
        self.retriever = retriever or build_default_retriever()
        self.llm_client = llm_client or GeminiClient()

    def get_feedback(
        self,
        record: LearningRecord,
        node: RoadmapNode,
        tags: List[str],
        compose_level: str = "quick",
        prompt_version: str = "record_coach_v1",
    ) -> Dict[str, object]:
        cache_key = stable_hash_json(
            {
                "memo": record.memo,
                "links": [link.url for link in record.links],
                "node": record.node_id,
                "roadmap": record.roadmap_id,
                "compose_level": compose_level,
            }
        )

        snapshot = self.snapshot_store.get_or_create(
            cache_key,
            version=prompt_version,
            builder=lambda: self._build_payload(record, node, tags, compose_level, prompt_version),
            metadata={"record_id": record.record_id},
        )
        return snapshot.payload

    def _build_payload(
        self,
        record: LearningRecord,
        node: RoadmapNode,
        tags: List[str],
        compose_level: str,
        prompt_version: str,
    ) -> Dict[str, object]:
        scores = score_record(record)
        summary = extractive_summary(record.memo)
        query = " ".join([node.title, " ".join(tags), summary]).strip()

        evidence = self.retriever.search(query, top_k=5)
        strengths, gaps = _analyze_strengths(scores)
        followups = _followup_questions(scores)
        next_actions = _next_actions(scores)

        rewrite = _compose_rewrite(record, scores, compose_level, self.model_router, self.llm_client)
        code_feedback = _maybe_code_feedback(record.memo)

        payload = {
            "record_id": record.record_id,
            "model_version": rewrite["model_version"],
            "prompt_version": prompt_version,
            "created_at": datetime.utcnow().isoformat(),
            "scores": scores,
            "strengths": strengths,
            "gaps": gaps,
            "rewrite_suggestions": {
                "portfolio_bullets": rewrite["portfolio_bullets"],
                "improved_memo": rewrite["improved_memo"],
            },
            "code_feedback": code_feedback,
            "next_actions": next_actions,
            "followup_questions": followups,
            "retrieval_evidence": _to_evidence_payload(evidence),
        }
        return payload


def build_default_retriever() -> HybridRetriever:
    bm25 = BM25Index()
    vector_store = InMemoryVectorStore()

    documents: List[Document] = []

    for slug, sources in TECH_SOURCES.items():
        content = " ".join(source["content"] for source in sources)
        doc_id = f"tech_card:{slug}"
        documents.append(
            Document(
                doc_id=doc_id,
                text=content,
                metadata={"source": "tech_card", "slug": slug, "snippet": extractive_summary(content)},
            )
        )
        vector_store.upsert(doc_id, vector=cheap_embed(content), metadata={"source": "tech_card", "snippet": content})

    for slug, pitfalls in COMMON_PITFALLS.items():
        for idx, pitfall in enumerate(pitfalls):
            doc_id = f"pitfall:{slug}:{idx}"
            documents.append(
                Document(
                    doc_id=doc_id,
                    text=pitfall,
                    metadata={"source": "common_pitfalls", "slug": slug, "snippet": pitfall},
                )
            )

    for idx, example in enumerate(GOOD_RECORD_EXAMPLES):
        doc_id = f"good_record:{idx}"
        documents.append(
            Document(
                doc_id=doc_id,
                text=example,
                metadata={"source": "good_record_examples", "snippet": extractive_summary(example)},
            )
        )

    bm25.add_documents(documents)

    vector_retriever = VectorRetriever(vector_store)
    hybrid = HybridRetriever(
        retrievers=[("bm25", bm25.search), ("vector", vector_retriever.search)],
        weights={"bm25": 1.0, "vector": 0.5},
    )
    return hybrid


def _analyze_strengths(scores: Dict[str, int]) -> tuple[List[str], List[str]]:
    strengths = []
    gaps = []
    if scores["evidence_level"] >= 2:
        strengths.append("링크 기반 근거가 있어 신뢰도가 높다")
    else:
        gaps.append("근거 링크가 부족해 신뢰도가 낮다")

    if scores["structure_score"] >= 50:
        strengths.append("목표/문제/해결 구조가 일정 부분 보인다")
    else:
        gaps.append("목표/문제/해결/다음 항목이 부족하다")

    if scores["specificity_score"] >= 40:
        strengths.append("구체적인 키워드가 포함되어 있다")
    else:
        gaps.append("구체적인 수치나 에러 메시지가 부족하다")

    if scores["reproducibility_score"] >= 60:
        strengths.append("재현 가능한 링크가 포함되어 있다")
    else:
        gaps.append("외부 링크의 공개 여부를 확인해야 한다")

    return strengths, gaps


def _followup_questions(scores: Dict[str, int]) -> List[str]:
    questions = []
    if scores["evidence_level"] < 2:
        questions.append("추가로 공유할 수 있는 데모/레포 링크가 있나요?")
    if scores["structure_score"] < 50:
        questions.append("문제 상황과 해결 과정을 한 줄씩 나눠 적어줄 수 있나요?")
    if scores["specificity_score"] < 40:
        questions.append("에러 메시지나 성능 수치를 포함해줄 수 있나요?")
    return questions


def _next_actions(scores: Dict[str, int]) -> List[Dict[str, str]]:
    actions = []
    if scores["evidence_level"] < 2:
        actions.append({"effort": "10m", "task": "데모 링크 또는 스크린샷 추가"})
    if scores["structure_score"] < 50:
        actions.append({"effort": "30m", "task": "목표/문제/해결/다음 항목으로 메모 재구성"})
    if scores["specificity_score"] < 40:
        actions.append({"effort": "2h", "task": "에러 로그/수치 기록 및 원인 분석 추가"})
    return actions


def _compose_rewrite(
    record: LearningRecord,
    scores: Dict[str, int],
    compose_level: str,
    router: ModelRouter,
    llm_client: GeminiClient,
) -> Dict[str, object]:
    if compose_level == "quick":
        # 빠른 응답 단계에서는 룰 기반으로만 반환한다.
        return {
            "model_version": "rule-based",
            "portfolio_bullets": [],
            "improved_memo": "",
        }

    complexity = 1 + int(scores["structure_score"] < 50) + int(scores["specificity_score"] < 40)
    routing = router.route(len(record.memo), complexity)

    if compose_level == "full" and llm_client.available():
        prompt = _build_record_prompt(record.memo, scores)
        response = llm_client.generate_json(prompt)
        if response.data and _valid_rewrite_payload(response.data):
            return {
                "model_version": llm_client.model_name,
                "portfolio_bullets": response.data["portfolio_bullets"],
                "improved_memo": response.data["improved_memo"],
            }

    bullets = [
        f"문제 상황을 정의하고 해결 방안을 적용해 개선했다 ({scores['quality_score']}점 기반).",
        "다음 단계로 반복 작업을 줄이기 위한 리팩터링을 계획했다.",
    ]
    improved = (
        "목표: 해결하려는 문제를 명확히 정의함. "
        "문제: 특정 오류/이슈가 발생함. "
        "해결: 적용한 조치와 결과를 기록함. "
        "다음: 재현/리팩터링 계획을 작성함."
    )

    return {
        "model_version": routing.model_name,
        "portfolio_bullets": bullets,
        "improved_memo": improved,
    }


def _build_record_prompt(memo: str, scores: Dict[str, int]) -> str:
    return (
        "다음 학습 기록을 포트폴리오 수준으로 개선할 문장을 JSON으로 반환해줘. "
        "반드시 JSON만 반환하고, 키는 portfolio_bullets(문장 배열)와 improved_memo(한 문장)만 사용해. "
        f"학습 기록: {memo} "
        f"점수: {scores} "
    )


def _valid_rewrite_payload(payload: Dict[str, object]) -> bool:
    if not isinstance(payload.get("portfolio_bullets"), list):
        return False
    if not isinstance(payload.get("improved_memo"), str):
        return False
    return True


def _to_evidence_payload(items: List[RetrievalItem]) -> List[Dict[str, str]]:
    payload = []
    for item in items:
        payload.append({
            "source": item.source,
            "id": item.item_id,
            "snippet": item.snippet,
        })
    return payload


def _maybe_code_feedback(memo: str) -> Dict[str, object]:
    if "```" not in memo:
        return {}
    code = memo.split("```")
    if len(code) < 2:
        return {}
    return analyze_code(code[1])
