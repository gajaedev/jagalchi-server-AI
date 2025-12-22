# =============================================================================
# 상태 기반 워크플로우 모듈 (Stateful Workflow Module)
# =============================================================================
#
# 이 모듈은 LangGraph 스타일의 상태 기반 워크플로우를 구현합니다.
# 학습 코치 에이전트의 실행 계획을 관리하고 체크포인트를 저장합니다.
#
# 워크플로우 단계:
#     1. **Route (라우팅)**: 사용자 의도 분류 및 도구 선택
#     2. **Retrieve (검색)**: 선택된 도구로 정보 검색
#     3. **Compose (구성)**: 최종 답변 생성
#
# 설계 원칙:
#     - **체크포인트 지속성**: 각 단계의 상태를 저장하여 세션 복구 가능
#     - **확장 가능성**: 새로운 단계 추가 시 plan 리스트만 수정
#     - **LangGraph 호환성**: 향후 LangGraph로 마이그레이션 시 최소 변경
#
# 참고:
#     - LangGraph: https://docs.langchain.com/oss/python/langgraph
#     - AI 기능 설계 문서: 3.2.2 LangGraph 기반 상태 기반 워크플로우
# =============================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

# -----------------------------------------------------------------------------
# 로컬 모듈 임포트
# -----------------------------------------------------------------------------
from jagalchi_ai.ai_core.domain.workflow_state import WorkflowState
from jagalchi_ai.ai_core.service.coach.in_memory_checkpoint import InMemoryCheckpoint


# =============================================================================
# 상수 정의
# =============================================================================

# 기본 워크플로우 단계 (순서 중요)
DEFAULT_WORKFLOW_PLAN: List[str] = ["route", "retrieve", "compose"]


# =============================================================================
# 워크플로우 클래스
# =============================================================================

class SimpleWorkflow:
    """
    기본 3단계 상태 기반 워크플로우.

    이 클래스는 학습 코치 에이전트의 실행 계획을 관리합니다.
    각 단계의 실행 상태를 체크포인트로 저장하여 세션이 중단되더라도
    복구할 수 있는 기반을 제공합니다.

    워크플로우 단계:
        1. route: 사용자 의도(intent) 분류
        2. retrieve: 적절한 도구(tools)로 정보 검색
        3. compose: 최종 답변 구성

    Attributes:
        _checkpoint: 상태 저장소 (InMemoryCheckpoint)

    Example:
        >>> workflow = SimpleWorkflow()
        >>> plan = workflow.run(
        ...     session_id="session_123",
        ...     intent="concept",
        ...     tools=["graph_explorer"]
        ... )
        >>> print(plan)  # ["route", "retrieve", "compose"]

    Note:
        현재는 InMemoryCheckpoint를 사용하지만, 프로덕션에서는
        PostgresCheckpoint 등으로 교체하여 영구 저장이 가능합니다.
        (LangGraph의 langgraph-checkpoint-postgres 참조)
    """

    def __init__(self, checkpoint: Optional[InMemoryCheckpoint] = None) -> None:
        """
        SimpleWorkflow 인스턴스를 초기화합니다.

        Args:
            checkpoint:
                상태 저장소. None인 경우 InMemoryCheckpoint를 생성합니다.
                테스트 시 Mock 객체를 주입할 수 있습니다.

        @param {Optional[InMemoryCheckpoint]} checkpoint - 상태 저장소.
        @returns {None} 체크포인트를 초기화합니다.
        """
        self._checkpoint = checkpoint or InMemoryCheckpoint()

    def run(
        self,
        session_id: str,
        intent: str,
        tools: List[str],
    ) -> List[str]:
        """
        워크플로우를 실행하고 계획을 반환합니다.

        각 단계별로 상태를 체크포인트에 저장하여 세션 복구 및
        디버깅이 가능하도록 합니다.

        Args:
            session_id:
                세션 고유 식별자. 사용자 세션 또는 요청 ID.
            intent:
                분류된 사용자 의도 ("concept", "error", "progress" 등).
            tools:
                사용된 도구 목록 (["graph_explorer", "doc_retriever"] 등).

        Returns:
            List[str]: 실행된 워크플로우 단계 목록.
                현재는 항상 ["route", "retrieve", "compose"]를 반환하지만,
                향후 조건부 분기가 추가될 수 있습니다.

        Example:
            >>> workflow = SimpleWorkflow()
            >>> plan = workflow.run("sess_1", "error", ["doc_retriever"])
            >>> assert plan == ["route", "retrieve", "compose"]

        @param {str} session_id - 세션 고유 식별자.
        @param {str} intent - 분류된 사용자 의도.
        @param {List[str]} tools - 사용된 도구 목록.
        @returns {List[str]} 실행된 워크플로우 단계 목록.
        """
        plan = DEFAULT_WORKFLOW_PLAN.copy()

        # Step 1: Route (라우팅) 상태 저장
        # 사용자 의도 분류 결과를 기록
        self._save_state(session_id, "route", {"intent": intent})

        # Step 2: Retrieve (검색) 상태 저장
        # 사용된 도구 목록을 기록
        self._save_state(session_id, "retrieve", {"tools": tools})

        # Step 3: Compose (구성) 상태 저장
        # 최종 답변 생성 단계 완료 기록
        self._save_state(session_id, "compose", {})

        return plan

    def _save_state(
        self,
        session_id: str,
        step_name: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        워크플로우 상태를 체크포인트에 저장합니다.

        Args:
            session_id: 세션 ID
            step_name: 단계 이름 ("route", "retrieve", "compose")
            payload: 상태 데이터 딕셔너리

        @param {str} session_id - 세션 ID.
        @param {str} step_name - 단계 이름.
        @param {Dict[str, Any]} payload - 상태 데이터.
        @returns {None} 체크포인트에 상태를 기록합니다.
        """
        self._checkpoint.save(
            session_id,
            WorkflowState(
                name=step_name,
                payload=payload,
                created_at=datetime.utcnow().isoformat(),
            ),
        )

    def get_history(self, session_id: str) -> List[WorkflowState]:
        """
        특정 세션의 워크플로우 히스토리를 조회합니다.

        Args:
            session_id: 조회할 세션 ID

        Returns:
            List[WorkflowState]: 저장된 상태 목록 (시간순)

        @param {str} session_id - 조회할 세션 ID.
        @returns {List[WorkflowState]} 저장된 상태 목록.
        """
        return self._checkpoint.get_all(session_id)
