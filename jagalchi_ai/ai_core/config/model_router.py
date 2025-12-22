from jagalchi_ai.ai_core.config.routing_decision import RoutingDecision


class ModelRouter:
    """입력 복잡도에 따라 모델을 선택하는 라우터."""

    def __init__(self, small_model: str = "mock-small-v1", large_model: str = "mock-large-v1") -> None:
        self._small = small_model
        self._large = large_model

    def route(self, text_length: int, complexity: int) -> RoutingDecision:
        if text_length > 1200 or complexity > 3:
            return RoutingDecision(model_name=self._large, reason="long_or_complex")
        return RoutingDecision(model_name=self._small, reason="default_small")
