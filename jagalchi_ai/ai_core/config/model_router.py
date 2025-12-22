from jagalchi_ai.ai_core.config.routing_decision import RoutingDecision


class ModelRouter:
    """입력 복잡도에 따라 모델을 선택하는 라우터."""

    def __init__(self, small_model: str = "mock-small-v1", large_model: str = "mock-large-v1") -> None:
        """
        @param small_model 기본으로 사용할 소형 모델 이름.
        @param large_model 복잡/긴 입력에 사용할 대형 모델 이름.
        @returns None
        """
        self._small = small_model
        self._large = large_model

    def route(self, text_length: int, complexity: int) -> RoutingDecision:
        """
        @param text_length 입력 텍스트 길이.
        @param complexity 추정 복잡도 점수.
        @returns 선택된 모델과 선택 이유를 포함한 라우팅 결과.
        """
        if text_length > 1200 or complexity > 3:
            return RoutingDecision(model_name=self._large, reason="long_or_complex")
        return RoutingDecision(model_name=self._small, reason="default_small")
