import unittest

from jagalchi_ai.ai_core.domain.learning_record import LearningRecord
from jagalchi_ai.ai_core.domain.link_meta import LinkMeta
from jagalchi_ai.ai_core.service.record.rubric import score_record


class RubricScoreTests(unittest.TestCase):
    def test_score_record_levels(self) -> None:
        """
        기록 루브릭 점수가 기대 범위인지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
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
