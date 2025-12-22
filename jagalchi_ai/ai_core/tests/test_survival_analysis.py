import unittest

from jagalchi_ai.ai_core.service.coach.cox_model import CoxModel


class SurvivalAnalysisTests(unittest.TestCase):
    def test_hazard(self) -> None:
        """
        Cox 모델 위험도 계산이 양수인지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        model = CoxModel()
        hazard = model.hazard({"motivation": 0.5, "ability": 0.5, "gap": 0.2})
        self.assertGreater(hazard, 0)


if __name__ == "__main__":
    unittest.main()
