from dataclasses import dataclass


@dataclass
class RoutingDecision:
    """모델 라우팅 결과."""

    model_name: str
    reason: str
