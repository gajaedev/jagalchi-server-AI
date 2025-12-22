import unittest

from jagalchi_ai.ai_core.service.comments.comment_quality_service import CommentQualityService
from jagalchi_ai.ai_core.service.comments.comment_thread_service import CommentThreadService


class CommentQualityTests(unittest.TestCase):
    def test_materialized_path(self) -> None:
        """
        대댓글 경로가 올바르게 생성되는지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        thread = CommentThreadService()
        root = thread.create_root("rm_frontend", "node_js", "첫 댓글")
        reply = thread.reply(root.comment_id, "대댓글")
        self.assertTrue(reply.path.startswith(root.path + "."))

    def test_relevance(self) -> None:
        """
        코멘트 관련성 및 모더레이션 결과를 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        quality = CommentQualityService(relevance_threshold=0.1)
        relevant = quality.check_relevance("React hooks 사용", "React hooks는 상태를 관리한다")
        self.assertTrue(relevant)
        moderation = quality.moderate("내용이 좋아요", "React hooks는 상태를 관리한다")
        self.assertIn("aspect_sentiment", moderation)


if __name__ == "__main__":
    unittest.main()
