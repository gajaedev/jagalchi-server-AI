# =============================================================================
# Fogg 행동 모델 기반 사용자 행동 분석 모듈 (Fogg Behavior Model)
# =============================================================================
#
# 이 모듈은 스탠퍼드 대학 BJ Fogg 교수의 행동 모델(B=MAP)을 구현합니다.
# 학습 코치가 사용자의 행동 변화를 유도하기 위한 핵심 분석 엔진입니다.
#
# Fogg 행동 모델 (B=MAP):
#     행동(Behavior) = 동기(Motivation) × 능력(Ability) × 트리거(Prompt)
#
#     세 가지 요소가 동시에 적절한 수준으로 존재할 때만 행동이 발생합니다.
#
# 구현된 기능:
#     1. **동기(Motivation) 진단**: 접속 빈도, 학습 일수를 기반으로 측정
#     2. **능력(Ability) 진단**: 클릭률, 피드백 조회율로 학습 참여도 측정
#     3. **트리거(Prompt) 최적화**: 최적의 알림 시간대 예측
#     4. **이탈 위험도(Dropout Risk)**: Cox 비례 위험 모델로 이탈 확률 산출
#
# 참고:
#     - Fogg Behavior Model: https://www.behaviormodel.org/
#     - AI 기능 설계 문서: 3.2 AI 학습 코치 섹션
# =============================================================================

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# -----------------------------------------------------------------------------
# 로컬 모듈 임포트
# -----------------------------------------------------------------------------
from jagalchi_ai.ai_core.domain.event_log import EventLog
from jagalchi_ai.ai_core.repository.mock_data import EVENT_LOGS
from jagalchi_ai.ai_core.service.coach.cox_model import CoxModel


# =============================================================================
# 상수 정의
# =============================================================================

# 동기 점수 계산 시 사용되는 기본값
DEFAULT_MOTIVATION_SCORE = 0.3  # 데이터 없을 때 기본 동기 점수

# 트리거 시간 기본값 (오후 8시)
DEFAULT_PROMPT_HOUR = 20

# 분석 대상 이벤트 타입
ENGAGEMENT_EVENT_TYPES = frozenset({"rec_click", "record_feedback_view"})

# 기본 분석 기간 (일)
DEFAULT_ANALYSIS_DAYS = 30


# =============================================================================
# 행동 모델 클래스
# =============================================================================

class BehaviorModel:
    """
    Fogg 행동 모델(B=MAP) 기반 사용자 행동 분석 클래스.

    이 클래스는 사용자의 학습 이벤트 로그를 분석하여 동기(Motivation),
    능력(Ability), 최적 트리거 시간(Prompt)을 정량화합니다.

    분석 결과는 학습 코치가 개인화된 개입 전략을 수립하는 데 활용됩니다:
        - 동기가 낮은 경우: Spark Trigger (동기 부여 메시지, 성공 사례)
        - 능력이 부족한 경우: Facilitator Trigger (난이도 하향, 힌트 제공)
        - 트리거 최적화: 학습 확률이 높은 시간대에 알림 발송

    Attributes:
        _events: 분석 대상 이벤트 로그 목록
        _cox: Cox 비례 위험 모델 (이탈 확률 계산용)

    Example:
        >>> model = BehaviorModel()
        >>> result = model.assess("user_123", days=30)
        >>> print(f"동기: {result['motivation']}")
        >>> print(f"능력: {result['ability']}")
        >>> print(f"최적 알림 시간: {result['prompt_hour']}시")
        >>> print(f"이탈 위험도: {result['dropout_risk']}")
    """

    def __init__(self, events: Optional[List[EventLog]] = None) -> None:
        """
        BehaviorModel 인스턴스를 초기화합니다.

        Args:
            events:
                분석 대상 이벤트 로그 목록.
                None인 경우 Mock 데이터(EVENT_LOGS)를 사용합니다.
                프로덕션에서는 실제 DB에서 조회한 이벤트를 전달해야 합니다.
        """
        self._events = events or EVENT_LOGS
        self._cox = CoxModel()

    def assess(self, user_id: str, days: int = DEFAULT_ANALYSIS_DAYS) -> Dict[str, Any]:
        """
        특정 사용자의 행동 패턴을 종합 분석합니다.

        최근 N일간의 이벤트 로그를 기반으로 Fogg 모델의 세 가지 요소를 측정하고,
        Cox 모델을 통해 이탈 위험도를 예측합니다.

        Args:
            user_id:
                분석 대상 사용자 ID.
            days:
                분석 기간 (일 단위). 기본값: 30일.

        Returns:
            Dict[str, Any]: 행동 분석 결과 딕셔너리.
                - motivation (float): 동기 점수 (0.0 ~ 1.0)
                    - 0.0: 매우 낮음 (Spark Trigger 필요)
                    - 1.0: 매우 높음 (자발적 학습 중)
                - ability (float): 능력 점수 (0.0 ~ 1.0)
                    - 0.0: 참여도 낮음 (Facilitator Trigger 필요)
                    - 1.0: 활발히 참여 중
                - prompt_hour (int): 최적 알림 시간 (0 ~ 23시)
                    - 사용자가 가장 활발한 시간대 기반
                - dropout_risk (float): 이탈 위험도 (0.0 ~ 1.0)
                    - Cox 비례 위험 모델 기반 예측

        Example:
            >>> result = model.assess("user_1", days=14)
            >>> if result["motivation"] < 0.5:
            ...     send_spark_trigger(user_id)  # 동기 부여 메시지 발송
        """
        # 분석 기간 설정 (최근 N일)
        cutoff = datetime.utcnow() - timedelta(days=days)

        # 해당 사용자의 이벤트만 필터링
        user_events = [
            event for event in self._events
            if event.user_id == user_id and event.created_at >= cutoff
        ]

        # 각 요소별 점수 계산
        motivation = _calculate_motivation_score(user_events, days)
        ability = _calculate_ability_score(user_events)
        prompt_hour = _find_best_prompt_hour(user_events)

        # Cox 모델로 이탈 위험도 산출
        dropout_risk = self._cox.hazard({
            "motivation": motivation,
            "ability": ability,
            "gap": 0.2,  # 학습 갭 (추후 실제 데이터로 대체)
        })

        return {
            "motivation": round(motivation, 2),
            "ability": round(ability, 2),
            "prompt_hour": prompt_hour,
            "dropout_risk": round(dropout_risk, 4),
        }


# =============================================================================
# 유틸리티 함수
# =============================================================================

def _calculate_motivation_score(events: List[EventLog], days: int) -> float:
    """
    동기(Motivation) 점수를 계산합니다.

    접속 빈도를 기반으로 동기 수준을 정량화합니다.
    활성 일수가 분석 기간 대비 높을수록 동기가 높다고 판단합니다.

    계산 공식:
        motivation = min(1.0, active_days / total_days)

    Args:
        events: 분석 대상 이벤트 로그 목록
        days: 분석 기간 (일)

    Returns:
        float: 동기 점수 (0.0 ~ 1.0)
            - 0.3: 데이터 없음 (기본값)
            - 0.0 ~ 0.5: 낮음 (Spark Trigger 권장)
            - 0.5 ~ 0.8: 보통
            - 0.8 ~ 1.0: 높음
    """
    if not events:
        return DEFAULT_MOTIVATION_SCORE

    # 활성 일수 계산 (중복 제거)
    active_days = len({event.created_at.date() for event in events})

    # 분석 기간 대비 활성 일수 비율 (최대 1.0)
    return min(1.0, active_days / max(days, 1))


def _calculate_ability_score(events: List[EventLog]) -> float:
    """
    능력(Ability) 점수를 계산합니다.

    학습 참여도를 기반으로 능력 수준을 정량화합니다.
    추천 클릭, 피드백 조회 등 적극적 참여 이벤트의 비율로 측정합니다.

    계산 공식:
        ability = min(1.0, engagement_events / total_events)

    Args:
        events: 분석 대상 이벤트 로그 목록

    Returns:
        float: 능력 점수 (0.0 ~ 1.0)
            - 0.0 ~ 0.4: 낮음 (Facilitator Trigger 권장)
            - 0.4 ~ 0.7: 보통
            - 0.7 ~ 1.0: 높음
    """
    if not events:
        return 0.0

    # 참여 이벤트 (추천 클릭, 피드백 조회 등)만 필터링
    engagement_count = sum(
        1 for event in events
        if event.event_type in ENGAGEMENT_EVENT_TYPES
    )

    # 전체 이벤트 대비 참여 이벤트 비율
    return min(1.0, engagement_count / max(len(events), 1))


def _find_best_prompt_hour(events: List[EventLog]) -> int:
    """
    최적의 트리거(알림) 시간을 찾습니다.

    사용자의 과거 활동 패턴을 분석하여 가장 자주 접속하는 시간대를 반환합니다.
    이 시간에 알림을 보내면 학습 시작 확률이 가장 높습니다.

    Args:
        events: 분석 대상 이벤트 로그 목록

    Returns:
        int: 최적 알림 시간 (0 ~ 23시)
            - 기본값: 20시 (오후 8시)

    Note:
        적절하지 않은 타이밍의 알림은 오히려 동기를 저하시킬 수 있습니다.
        이 함수는 사용자 개인의 패턴에 맞춘 최적 시간을 찾아줍니다.
    """
    if not events:
        return DEFAULT_PROMPT_HOUR

    # 시간대별 이벤트 수 집계
    hour_counts = Counter(event.created_at.hour for event in events)

    # 가장 빈도가 높은 시간대 반환
    most_common_hour, _ = hour_counts.most_common(1)[0]
    return most_common_hour
