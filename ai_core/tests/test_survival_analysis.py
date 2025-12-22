import unittest

from ai_core.coach.survival_analysis import CoxModel


class SurvivalAnalysisTests(unittest.TestCase):
    def test_hazard(self) -> None:
        model = CoxModel()
        hazard = model.hazard({"motivation": 0.5, "ability": 0.5, "gap": 0.2})
        self.assertGreater(hazard, 0)


if __name__ == "__main__":
    unittest.main()
