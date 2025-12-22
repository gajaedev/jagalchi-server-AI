from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ai_core.coach.behavior_model import BehaviorModel
from ai_core.clients.gemini_client import GeminiClient
from ai_core.graph.graph_rag import GraphRAGService
from ai_core.progress.progress_tracking import ProgressTrackingService
from ai_core.recommendation.resource_recommender import ResourceRecommendationService
from ai_core.retrieval.semantic_cache import SemanticCache
from ai_core.coach.state_workflow import SimpleWorkflow
from ai_core.nlp.text_utils import extractive_summary


class LearningCoachService:
    def __init__(
        self,
        graph_rag: Optional[GraphRAGService] = None,
        resource_recommender: Optional[ResourceRecommendationService] = None,
        progress_tracker: Optional[ProgressTrackingService] = None,
        cache: Optional[SemanticCache] = None,
        llm_client: Optional[GeminiClient] = None,
        behavior_model: Optional[BehaviorModel] = None,
        workflow: Optional[SimpleWorkflow] = None,
    ) -> None:
        self._graph_rag = graph_rag or GraphRAGService()
        self._resource_recommender = resource_recommender or ResourceRecommendationService()
        self._progress_tracker = progress_tracker or ProgressTrackingService()
        self._cache = cache or SemanticCache()
        self._llm_client = llm_client or GeminiClient()
        self._behavior_model = behavior_model or BehaviorModel()
        self._workflow = workflow or SimpleWorkflow()

    def answer(
        self,
        user_id: str,
        question: str,
        user_level: str = "beginner",
        compose_level: str = "quick",
    ) -> Dict[str, object]:
        cache_key = {"user_level": user_level}
        cached = self._cache.get(question, metadata=cache_key)
        if cached:
            plan = self._workflow.run(user_id, "cached", ["semantic_cache"])
            return {
                "user_id": user_id,
                "question": question,
                "intent": "cached",
                "toolchain": ["semantic_cache"],
                "plan": plan,
                "answer": cached.answer,
                "retrieval_evidence": [],
                "behavior_summary": self._behavior_model.assess(user_id),
                "model_version": "cache_v1",
                "prompt_version": "coach_v1",
                "created_at": datetime.utcnow().isoformat(),
                "cache_hit": True,
            }

        intent = _route_intent(question)
        toolchain: List[str] = []
        evidence: List[Dict[str, str]] = []
        answer = ""

        if intent == "progress":
            toolchain.append("progress_checker")
            summary = self._progress_tracker.summary(user_id)
            answer = f"현재 진행 상태 요약: {summary}"
        elif intent == "error":
            toolchain.append("doc_retriever")
            result = self._resource_recommender.recommend(question, top_k=1)
            item = result["items"][0] if result["items"] else {}
            answer = f"관련 자료: {item.get('title', '')} {item.get('url', '')}"
            evidence = result["retrieval_evidence"]
        else:
            toolchain.append("graph_explorer")
            context = self._graph_rag.build_context(question, top_k=3)
            nodes = context["graph_snapshot"]["nodes"]
            answer = "핵심 개념 요약: " + ", ".join(node["text"] for node in nodes)
            evidence = context["retrieval_evidence"]

        if compose_level == "full" and self._llm_client.available():
            prompt = _build_coach_prompt(question, answer, evidence, user_level)
            response = self._llm_client.generate_text(prompt)
            if response:
                answer = response

        final_answer = extractive_summary(answer, max_sentences=2)
        self._cache.set(question, final_answer, metadata=cache_key)
        plan = self._workflow.run(user_id, intent, toolchain)

        return {
            "user_id": user_id,
            "question": question,
            "intent": intent,
            "toolchain": toolchain,
            "plan": plan,
            "answer": final_answer,
            "retrieval_evidence": evidence,
            "behavior_summary": self._behavior_model.assess(user_id),
            "model_version": "coach_v1",
            "prompt_version": "coach_v1",
            "created_at": datetime.utcnow().isoformat(),
            "cache_hit": False,
        }


def _route_intent(question: str) -> str:
    lowered = question.lower()
    if any(keyword in lowered for keyword in ["어디까지", "진행", "완료", "progress"]):
        return "progress"
    if any(keyword in lowered for keyword in ["error", "에러", "오류", "실패", "exception"]):
        return "error"
    return "concept"


def _build_coach_prompt(question: str, answer: str, evidence: List[Dict[str, str]], level: str) -> str:
    return (
        "사용자의 질문에 대해 간결하고 실용적인 답변을 생성해줘. "
        "근거로 제공된 evidence를 활용하고, 한글로 답해. "
        f"질문: {question} "
        f"초안: {answer} "
        f"근거: {evidence} "
        f"사용자 레벨: {level}"
    )
