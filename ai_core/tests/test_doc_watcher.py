import unittest

from ai_core.doc_watcher import DocWatcher


class DocWatcherTests(unittest.TestCase):
    def test_semantic_diff(self) -> None:
        watcher = DocWatcher(change_threshold=0.1)
        change = watcher.semantic_diff("React docs", "React docs updated")
        self.assertTrue(change.change_ratio > 0)


if __name__ == "__main__":
    unittest.main()
