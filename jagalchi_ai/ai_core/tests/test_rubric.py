import unittest

from jagalchi_ai.ai_core.record.rubric import score_record
from jagalchi_ai.ai_core.core.types import LearningRecord, LinkMeta


class RubricScoreTests(unittest.TestCase):
    def test_score_record_levels(self) -> None:
        record = LearningRecord(
            record_id="rec_test",
            memo="목표: 테스트 목표. 문제: 오류 발생. 해결: 원인 수정. 다음: 리팩터링 진행.",
            links=[LinkMeta(url="https://example.com", is_public=True, status_code=200)],
            node_id="node",
            roadmap_id="rm",
        )
        scores = score_record(record)
        self.assertEqual(scores["evidence_level"], 3)
        self.assertEqual(scores["structure_score"], 100)
        self.assertEqual(scores["reproducibility_score"], 100)
        self.assertGreaterEqual(scores["quality_score"], 60)


if __name__ == "__main__":
    unittest.main()
