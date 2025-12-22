import unittest

from jagalchi_ai.ai_core.service.tech.doc_watcher import DocWatcher


class DocWatcherTests(unittest.TestCase):
    def test_semantic_diff(self) -> None:
        """
        문서 변경 감지 비율 계산을 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        watcher = DocWatcher(change_threshold=0.1)
        change = watcher.semantic_diff("React docs", "React docs updated")
        self.assertTrue(change.change_ratio > 0)


if __name__ == "__main__":
    unittest.main()
