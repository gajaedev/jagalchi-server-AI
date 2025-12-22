import unittest

from jagalchi_ai.ai_core.core.mock_data import LEARNING_RECORDS, ROADMAPS
from jagalchi_ai.ai_core.record.record_coach import RecordCoachService
from jagalchi_ai.ai_core.core.snapshot import SnapshotStore


class CacheTests(unittest.TestCase):
    def test_record_coach_cache_hit(self) -> None:
        store = SnapshotStore()
        service = RecordCoachService(snapshot_store=store)
        record = LEARNING_RECORDS[0]
        node = ROADMAPS[record.roadmap_id].nodes[-1]

        service.get_feedback(record, node, tags=node.tags, compose_level="quick")
        self.assertEqual(store.hits, 0)
        self.assertEqual(store.misses, 1)

        service.get_feedback(record, node, tags=node.tags, compose_level="quick")
        self.assertEqual(store.hits, 1)


if __name__ == "__main__":
    unittest.main()
