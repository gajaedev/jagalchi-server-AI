import unittest

from jagalchi_ai.ai_core.tech.reel_pipeline import ReelPipeline


class ReelPipelineTests(unittest.TestCase):
    def test_reel_extract(self) -> None:
        sources = [
            {"title": "Doc", "content": "License: MIT v1.2.3 Language: Python", "fetched_at": "2025-01-01"}
        ]
        pipeline = ReelPipeline()
        result = pipeline.extract(sources)
        self.assertIn("license", result.metadata)


if __name__ == "__main__":
    unittest.main()
