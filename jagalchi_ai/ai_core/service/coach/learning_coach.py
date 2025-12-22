# =============================================================================
# 학습 코치 서비스 모듈 (Learning Coach Service Module)
# =============================================================================
#
# 이 모듈은 Jagalchi AI의 핵심 "학습 코치" 기능을 구현합니다.
# 단순한 챗봇을 넘어서, 로드맵과 기술 카드의 정보를 통합하여
# 사용자를 능동적으로 가이드하는 **에이전트(Agent)** 역할을 수행합니다.
#
# 설계 철학:
#     1. **에이전트 기반 RAG (Agentic RAG)**: 사용자의 질문 의도를 파악하고
#        적절한 도구(Tool)를 선택하여 답을 찾아내는 ReAct 패턴 사용
#     2. **시맨틱 캐싱 (Semantic Caching)**: 유사한 질문에 대해 LLM 호출 없이
#        캐시된 답변을 즉시 반환하여 비용과 지연 시간 절감
#     3. **행동 모델 통합 (Fogg Behavior Model)**: 사용자의 동기, 능력, 트리거를
#        분석하여 개인화된 학습 코칭 제공
#
# 사용 가능한 도구 (Tools):
#     - GraphExplorer: 지식 그래프 조회 (개념 정의, 선수 관계, 연관 기술)
#     - DocRetriever: 벡터 DB 검색 (구체적 사용법, 에러 해결법)
#     - ProgressChecker: 사용자 학습 진행 상황 조회
#
# 사용 예시:
#     >>> from jagalchi_ai.ai_core.service.coach.learning_coach import LearningCoachService
#     >>> coach = LearningCoachService()
#     >>> result = coach.answer("user_123", "React useEffect 에러 해결 방법")
#     >>> print(result["answer"])
#
# 참고:
#     - AI 기능 설계 문서: /AI/AI 기능 설계 및 고도화 전략.txt
#     - ReAct 패턴: https://arxiv.org/abs/2210.03629
# =============================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

# -----------------------------------------------------------------------------
# 로컬 모듈 임포트
# -----------------------------------------------------------------------------
from jagalchi_ai.ai_core.client import GeminiClient
from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary
from jagalchi_ai.ai_core.repository.semantic_cache import SemanticCache
from jagalchi_ai.ai_core.service.coach.behavior_model import BehaviorModel
from jagalchi_ai.ai_core.service.coach.simple_workflow import SimpleWorkflow
from jagalchi_ai.ai_core.service.graph.graph_rag import GraphRAGService
from jagalchi_ai.ai_core.service.progress.progress_tracking_service import ProgressTrackingService
from jagalchi_ai.ai_core.service.recommendation.resource_recommender import ResourceRecommendationService


# =============================================================================
# 상수 정의
# =============================================================================

# 의도 분류 키워드 매핑
INTENT_KEYWORDS: Dict[str, List[str]] = {
    "progress": ["어디까지", "진행", "완료", "progress", "현재", "상태"],
    "error": ["error", "에러", "오류", "실패", "exception", "버그", "안됨", "안돼"],
}

# 기본 compose level (빠른 응답 vs 상세 응답)
DEFAULT_COMPOSE_LEVEL = "quick"

# 모델/프롬프트 버전 (캐시 무효화 및 추적용)
MODEL_VERSION = "coach_v1"
PROMPT_VERSION = "coach_v1"


# =============================================================================
# 학습 코치 서비스 클래스
# =============================================================================

class LearningCoachService:
    """
    학습 코치 서비스 클래스.

    사용자의 질문에 대해 적절한 도구를 선택하고, 맥락에 맞는 답변을 생성하는
    오케스트레이터(Orchestrator) 역할을 수행합니다.

    이 클래스는 다음과 같은 컴포넌트를 조합하여 동작합니다:
        - GraphRAGService: 지식 그래프 기반 컨텍스트 생성
        - ResourceRecommendationService: 관련 학습 자료 추천
        - ProgressTrackingService: 사용자 진행 상황 추적
        - SemanticCache: 유사 질문 캐싱
        - GeminiClient: LLM 기반 답변 생성
        - BehaviorModel: 사용자 행동 분석 (Fogg B=MAP 모델)
        - SimpleWorkflow: 상태 기반 워크플로우 관리

    Attributes:
        _graph_rag: 지식 그래프 RAG 서비스
        _resource_recommender: 자료 추천 서비스
        _progress_tracker: 진행 상황 추적 서비스
        _cache: 시맨틱 캐시
        _llm_client: LLM 클라이언트 (Gemini)
        _behavior_model: 행동 모델 분석기
        _workflow: 워크플로우 관리자

    Example:
        >>> # 기본 사용법
        >>> coach = LearningCoachService()
        >>> result = coach.answer("user_1", "React란 무엇인가요?")

        >>> # 커스텀 컴포넌트 사용
        >>> from jagalchi_ai.ai_core.client import GeminiClient
        >>> coach = LearningCoachService(llm_client=GeminiClient())
        >>> result = coach.answer("user_1", "에러가 발생해요", compose_level="full")
    """

    # -------------------------------------------------------------------------
    # 초기화
    # -------------------------------------------------------------------------

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
        """
        LearningCoachService 인스턴스를 초기화합니다.

        모든 의존성은 선택적이며, 제공되지 않으면 기본 인스턴스가 생성됩니다.
        이 패턴은 테스트 시 Mock 객체 주입을 용이하게 합니다.

        Args:
            graph_rag:
                지식 그래프 RAG 서비스. 개념 간 관계 탐색에 사용.
            resource_recommender:
                학습 자료 추천 서비스. 에러 해결, 튜토리얼 검색 등에 활용.
            progress_tracker:
                사용자 진행 상황 추적 서비스. "어디까지 했지?" 질문 처리.
            cache:
                시맨틱 캐시. 유사 질문에 대한 빠른 응답 제공.
            llm_client:
                LLM 클라이언트. 답변 생성 및 정제에 사용.
            behavior_model:
                Fogg 행동 모델 평가기. 동기/능력/트리거 분석.
            workflow:
                상태 기반 워크플로우. 에이전트의 실행 계획 관리.

        @param {Optional[GraphRAGService]} graph_rag - 지식 그래프 RAG 서비스.
        @param {Optional[ResourceRecommendationService]} resource_recommender - 자료 추천 서비스.
        @param {Optional[ProgressTrackingService]} progress_tracker - 진행 상황 추적 서비스.
        @param {Optional[SemanticCache]} cache - 시맨틱 캐시.
        @param {Optional[GeminiClient]} llm_client - LLM 클라이언트.
        @param {Optional[BehaviorModel]} behavior_model - 행동 모델 분석기.
        @param {Optional[SimpleWorkflow]} workflow - 워크플로우 관리자.
        @returns {None} 기본 의존성을 초기화합니다.
        """
        # 의존성 주입 (Dependency Injection) 패턴 적용
        # None인 경우 기본 인스턴스 생성
        self._graph_rag = graph_rag or GraphRAGService()
        self._resource_recommender = resource_recommender or ResourceRecommendationService()
        self._progress_tracker = progress_tracker or ProgressTrackingService()
        self._cache = cache or SemanticCache()
        self._llm_client = llm_client or GeminiClient()
        self._behavior_model = behavior_model or BehaviorModel()
        self._workflow = workflow or SimpleWorkflow()

    # -------------------------------------------------------------------------
    # 메인 API
    # -------------------------------------------------------------------------

    def answer(
        self,
        user_id: str,
        question: str,
        user_level: str = "beginner",
        compose_level: str = DEFAULT_COMPOSE_LEVEL,
    ) -> Dict[str, Any]:
        """
        사용자의 질문에 대한 학습 코치 답변을 생성합니다.

        이 메서드는 다음과 같은 파이프라인으로 동작합니다:
            1. 시맨틱 캐시 확인 (Cache Hit 시 즉시 반환)
            2. 질문 의도 분류 (progress / error / concept)
            3. 의도에 따른 적절한 도구 선택 및 실행
            4. (compose_level="full"인 경우) LLM으로 답변 정제
            5. 캐시 저장 및 최종 응답 반환

        Args:
            user_id:
                사용자 고유 식별자. 진행 상황 추적 및 개인화에 사용.
            question:
                사용자의 질문 텍스트.
            user_level:
                사용자 학습 수준 ("beginner", "intermediate", "advanced").
                캐시 키와 답변 톤 조절에 활용.
            compose_level:
                답변 상세 수준.
                - "quick": 빠른 응답 (캐시/로컬 처리만)
                - "full": 상세 응답 (LLM 정제 포함)

        Returns:
            Dict[str, Any]: 학습 코치 응답 딕셔너리.
                - user_id: 사용자 ID
                - question: 원본 질문
                - intent: 분류된 의도 ("progress" | "error" | "concept")
                - toolchain: 사용된 도구 목록
                - plan: 워크플로우 실행 계획
                - answer: 최종 답변 텍스트
                - retrieval_evidence: 검색된 근거 목록
                - behavior_summary: 사용자 행동 분석 결과
                - model_version: 사용된 모델 버전
                - prompt_version: 사용된 프롬프트 버전
                - created_at: 응답 생성 시각 (ISO 8601)
                - cache_hit: 캐시 히트 여부

        Example:
            >>> coach = LearningCoachService()
            >>> response = coach.answer("user_1", "React 상태 관리 방법")
            >>> print(response["intent"])  # "concept"
            >>> print(response["answer"])  # "핵심 개념 요약: React, State, ..."

        @param {str} user_id - 사용자 고유 식별자.
        @param {str} question - 사용자 질문 텍스트.
        @param {str} user_level - 사용자 학습 수준.
        @param {str} compose_level - 답변 상세 수준.
        @returns {Dict[str, Any]} 학습 코치 응답 딕셔너리.
        """
        # ---------------------------------------------------------------------
        # Step 1: 시맨틱 캐시 확인
        # ---------------------------------------------------------------------
        # 유사한 질문이 캐시에 있으면 LLM 호출 없이 즉시 반환
        # 이를 통해 비용 절감 및 응답 속도 향상 (최대 80% 비용 절감 가능)
        cache_key = {"user_level": user_level}
        cached = self._cache.get(question, metadata=cache_key)

        if cached:
            plan = self._workflow.run(user_id, "cached", ["semantic_cache"])
            return self._build_response(
                user_id=user_id,
                question=question,
                intent="cached",
                toolchain=["semantic_cache"],
                plan=plan,
                answer=cached.answer,
                evidence=[],
                cache_hit=True,
            )

        # ---------------------------------------------------------------------
        # Step 2: 질문 의도 분류 (Intent Classification)
        # ---------------------------------------------------------------------
        # ReAct 패턴의 첫 번째 단계: 사용자의 질문 의도 파악
        intent = _classify_intent(question)

        # ---------------------------------------------------------------------
        # Step 3: 의도에 따른 도구 선택 및 실행
        # ---------------------------------------------------------------------
        toolchain: List[str] = []
        evidence: List[Dict[str, str]] = []
        answer = ""

        if intent == "progress":
            # 진행 상황 질문: ProgressChecker 도구 사용
            toolchain.append("progress_checker")
            summary = self._progress_tracker.summary(user_id)
            answer = f"현재 진행 상태 요약: {summary}"

        elif intent == "error":
            # 에러/문제 해결 질문: DocRetriever 도구 사용
            toolchain.append("doc_retriever")
            result = self._resource_recommender.recommend(question, top_k=1)
            item = result["items"][0] if result["items"] else {}
            answer = f"관련 자료: {item.get('title', '')} {item.get('url', '')}"
            evidence = result["retrieval_evidence"]

        else:
            # 개념 질문 (기본): GraphExplorer 도구 사용
            toolchain.append("graph_explorer")
            context = self._graph_rag.build_context(question, top_k=3)
            nodes = context["graph_snapshot"]["nodes"]
            answer = "핵심 개념 요약: " + ", ".join(node["text"] for node in nodes)
            evidence = context["retrieval_evidence"]

        # ---------------------------------------------------------------------
        # Step 4: (선택적) LLM을 통한 답변 정제
        # ---------------------------------------------------------------------
        # compose_level="full"이고 LLM이 사용 가능한 경우에만 실행
        if compose_level == "full" and self._llm_client.available():
            prompt = _build_coach_prompt(question, answer, evidence, user_level)
            response = self._llm_client.generate_text(prompt)
            if response:
                answer = response

        # ---------------------------------------------------------------------
        # Step 5: 캐시 저장 및 최종 응답 생성
        # ---------------------------------------------------------------------
        # 추출적 요약으로 답변 간소화 (최대 2문장)
        final_answer = extractive_summary(answer, max_sentences=2)

        # 캐시에 저장 (다음 유사 질문에서 즉시 반환 가능)
        self._cache.set(question, final_answer, metadata=cache_key)

        # 워크플로우 실행 계획 생성
        plan = self._workflow.run(user_id, intent, toolchain)

        return self._build_response(
            user_id=user_id,
            question=question,
            intent=intent,
            toolchain=toolchain,
            plan=plan,
            answer=final_answer,
            evidence=evidence,
            cache_hit=False,
        )

    # -------------------------------------------------------------------------
    # 내부 헬퍼 메서드
    # -------------------------------------------------------------------------

    def _build_response(
        self,
        user_id: str,
        question: str,
        intent: str,
        toolchain: List[str],
        plan: Dict[str, Any],
        answer: str,
        evidence: List[Dict[str, str]],
        cache_hit: bool,
    ) -> Dict[str, Any]:
        """
        학습 코치 응답 딕셔너리를 구성합니다.

        이 메서드는 응답 구조를 표준화하여 일관된 API 응답을 보장합니다.

        Args:
            user_id: 사용자 ID
            question: 원본 질문
            intent: 분류된 의도
            toolchain: 사용된 도구 목록
            plan: 워크플로우 실행 계획
            answer: 최종 답변
            evidence: 검색 근거 목록
            cache_hit: 캐시 히트 여부

        Returns:
            Dict[str, Any]: 표준화된 응답 딕셔너리

        @param {str} user_id - 사용자 ID.
        @param {str} question - 원본 질문.
        @param {str} intent - 분류된 의도.
        @param {List[str]} toolchain - 사용된 도구 목록.
        @param {Dict[str, Any]} plan - 워크플로우 실행 계획.
        @param {str} answer - 최종 답변.
        @param {List[Dict[str, str]]} evidence - 검색 근거 목록.
        @param {bool} cache_hit - 캐시 히트 여부.
        @returns {Dict[str, Any]} 표준화된 응답 딕셔너리.
        """
        return {
            "user_id": user_id,
            "question": question,
            "intent": intent,
            "toolchain": toolchain,
            "plan": plan,
            "answer": answer,
            "retrieval_evidence": evidence,
            "behavior_summary": self._behavior_model.assess(user_id),
            "model_version": MODEL_VERSION,
            "prompt_version": PROMPT_VERSION,
            "created_at": datetime.utcnow().isoformat(),
            "cache_hit": cache_hit,
        }


# =============================================================================
# 유틸리티 함수
# =============================================================================

def _classify_intent(question: str) -> str:
    """
    사용자 질문의 의도를 분류합니다.

    키워드 기반의 간단한 규칙으로 의도를 분류합니다.
    더 정교한 분류가 필요한 경우 ML 기반 분류기로 대체 가능합니다.

    Args:
        question: 사용자 질문 텍스트

    Returns:
        str: 분류된 의도
            - "progress": 진행 상황 확인 질문
            - "error": 에러/문제 해결 질문
            - "concept": 개념 이해 질문 (기본값)

    Example:
        >>> _classify_intent("어디까지 완료했지?")
        "progress"
        >>> _classify_intent("TypeError 에러가 발생해요")
        "error"
        >>> _classify_intent("React의 Virtual DOM이란?")
        "concept"

    @param {str} question - 사용자 질문 텍스트.
    @returns {str} 분류된 의도 문자열.
    """
    lowered = question.lower()

    # 진행 상황 관련 키워드 검사
    if any(keyword in lowered for keyword in INTENT_KEYWORDS["progress"]):
        return "progress"

    # 에러/문제 해결 관련 키워드 검사
    if any(keyword in lowered for keyword in INTENT_KEYWORDS["error"]):
        return "error"

    # 기본값: 개념 질문
    return "concept"


def _build_coach_prompt(
    question: str,
    answer: str,
    evidence: List[Dict[str, str]],
    level: str,
) -> str:
    """
    LLM에 전달할 학습 코치 프롬프트를 생성합니다.

    이 프롬프트는 Gemini 모델이 사용자의 학습 수준에 맞게
    친근하고 실용적인 답변을 생성하도록 안내합니다.

    Args:
        question: 사용자의 원본 질문
        answer: 도구 실행 결과로 생성된 초안 답변
        evidence: 검색된 근거 자료 목록
        level: 사용자 학습 수준 ("beginner", "intermediate", "advanced")

    Returns:
        str: LLM에 전달할 전체 프롬프트 문자열

    @param {str} question - 사용자 질문 텍스트.
    @param {str} answer - 도구 실행 결과 초안.
    @param {List[Dict[str, str]]} evidence - 검색 근거 목록.
    @param {str} level - 사용자 학습 수준.
    @returns {str} 완성된 프롬프트 문자열.
    """
    return (
        "사용자의 질문에 대해 간결하고 실용적인 답변을 생성해줘. "
        "근거로 제공된 evidence를 활용하고, 한글로 답해. "
        f"질문: {question} "
        f"초안: {answer} "
        f"근거: {evidence} "
        f"사용자 레벨: {level}"
    )
