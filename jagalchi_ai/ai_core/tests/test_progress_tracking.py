import unittest
from datetime import datetime, timedelta

from jagalchi_ai.ai_core.repository.mock_data import ROADMAPS
from jagalchi_ai.ai_core.service.progress.progress_tracking_service import ProgressTrackingService


class ProgressTrackingTests(unittest.TestCase):
    def test_unlock_flow(self) -> None:
        """
        완료 노드 기준으로 다음 노드가 해제되는지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        roadmap = ROADMAPS["rm_frontend"]
        tracker = ProgressTrackingService()
        tracker.initialize("user_1", roadmap)
        tracker.complete_node("user_1", "node_html", 85)
        unlocked = tracker.unlock_children("user_1", roadmap, "node_html")
        self.assertIn("node_css", unlocked)

    def test_spaced_repetition(self) -> None:
        """
        간격 반복 로직이 복습 상태를 생성하는지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        roadmap = ROADMAPS["rm_frontend"]
        tracker = ProgressTrackingService()
        tracker.initialize("user_1", roadmap)
        tracker.complete_node("user_1", "node_html", 90)
        state = tracker.get_state("user_1", "node_html")
        state.last_reviewed = datetime.utcnow() - timedelta(days=14)
        needs_review = tracker.apply_spaced_repetition("user_1", now=datetime.utcnow())
        self.assertIn("node_html", needs_review)


if __name__ == "__main__":
    unittest.main()
