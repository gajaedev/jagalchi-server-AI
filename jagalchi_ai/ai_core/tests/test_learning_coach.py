import unittest

from jagalchi_ai.ai_core.common.schema_validation import validate_learning_coach_output
from jagalchi_ai.ai_core.service.coach.learning_coach import LearningCoachService


class LearningCoachTests(unittest.TestCase):
    def test_learning_coach_schema(self) -> None:
        """
        학습 코치 응답 스키마를 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        service = LearningCoachService()
        payload = service.answer("user_1", "진행 상황 알려줘")
        validate_learning_coach_output(payload)


if __name__ == "__main__":
    unittest.main()
