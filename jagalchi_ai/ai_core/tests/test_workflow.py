import unittest

from jagalchi_ai.ai_core.service.coach.simple_workflow import SimpleWorkflow


class WorkflowTests(unittest.TestCase):
    def test_workflow_plan(self) -> None:
        """
        워크플로우 실행 계획이 기대 순서인지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        workflow = SimpleWorkflow()
        plan = workflow.run("session1", "concept", ["graph_explorer"])
        self.assertEqual(plan, ["route", "retrieve", "compose"])


if __name__ == "__main__":
    unittest.main()
