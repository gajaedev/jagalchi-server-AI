import unittest

from jagalchi_ai.ai_core.coach.learning_coach import LearningCoachService
from jagalchi_ai.ai_core.core.schema_validation import validate_learning_coach_output


class LearningCoachTests(unittest.TestCase):
    def test_learning_coach_schema(self) -> None:
        service = LearningCoachService()
        payload = service.answer("user_1", "진행 상황 알려줘")
        validate_learning_coach_output(payload)


if __name__ == "__main__":
    unittest.main()
