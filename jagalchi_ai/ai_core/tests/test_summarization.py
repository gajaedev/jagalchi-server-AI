import unittest

from jagalchi_ai.ai_core.common.nlp.summarization import textrank_sentences


class SummarizationTests(unittest.TestCase):
    def test_textrank(self) -> None:
        text = "React는 UI를 만든다. 컴포넌트 기반이다. 상태 관리를 이해해야 한다."
        sentences = textrank_sentences(text, top_n=2)
        self.assertEqual(len(sentences), 2)


if __name__ == "__main__":
    unittest.main()
