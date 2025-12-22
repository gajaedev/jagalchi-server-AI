import unittest

from jagalchi_ai.ai_core.common.schema_validation import validate_record_coach_output
from jagalchi_ai.ai_core.repository.mock_data import LEARNING_RECORDS, ROADMAPS
from jagalchi_ai.ai_core.service.record.record_coach import RecordCoachService


class SchemaValidationTests(unittest.TestCase):
    def test_record_coach_schema(self) -> None:
        """
        학습 기록 코치 스키마를 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        service = RecordCoachService()
        record = LEARNING_RECORDS[0]
        node = ROADMAPS[record.roadmap_id].nodes[-1]
        output = service.get_feedback(record, node, tags=node.tags, compose_level="quick")
        validate_record_coach_output(output)


if __name__ == "__main__":
    unittest.main()
