import unittest

from jagalchi_ai.ai_core.core.mock_data import LEARNING_RECORDS, ROADMAPS
from jagalchi_ai.ai_core.record.record_coach import RecordCoachService
from jagalchi_ai.ai_core.core.schema_validation import validate_record_coach_output


class SchemaValidationTests(unittest.TestCase):
    def test_record_coach_schema(self) -> None:
        service = RecordCoachService()
        record = LEARNING_RECORDS[0]
        node = ROADMAPS[record.roadmap_id].nodes[-1]
        output = service.get_feedback(record, node, tags=node.tags, compose_level="quick")
        validate_record_coach_output(output)


if __name__ == "__main__":
    unittest.main()
