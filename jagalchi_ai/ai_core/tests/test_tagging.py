import unittest

from jagalchi_ai.ai_core.tags.tagging import AutoTagger, TagGraph


class TaggingTests(unittest.TestCase):
    def test_tag_expand(self) -> None:
        graph = TagGraph({"python": ["django", "fastapi"]})
        expanded = graph.expand("python")
        self.assertIn("django", expanded)

    def test_auto_tagger(self) -> None:
        tagger = AutoTagger()
        tags = tagger.tag_text("React와 Zustand 상태관리")
        slugs = [tag["tech_slug"] for tag in tags]
        self.assertIn("react", slugs)


if __name__ == "__main__":
    unittest.main()
