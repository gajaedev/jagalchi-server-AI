import unittest

from jagalchi_ai.ai_core.service.tags.auto_tagger import AutoTagger
from jagalchi_ai.ai_core.service.tags.tag_graph import TagGraph


class TaggingTests(unittest.TestCase):
    def test_tag_expand(self) -> None:
        """
        태그 그래프 확장 로직을 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        graph = TagGraph({"python": ["django", "fastapi"]})
        expanded = graph.expand("python")
        self.assertIn("django", expanded)

    def test_auto_tagger(self) -> None:
        """
        자동 태그 추출이 기술 슬러그를 포함하는지 확인합니다.

        @returns {None} 테스트만 수행합니다.
        """
        tagger = AutoTagger()
        tags = tagger.tag_text("React와 Zustand 상태관리")
        slugs = [tag["tech_slug"] for tag in tags]
        self.assertIn("react", slugs)


if __name__ == "__main__":
    unittest.main()
