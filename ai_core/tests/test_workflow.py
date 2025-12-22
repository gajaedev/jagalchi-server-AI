import unittest

from ai_core.state_workflow import SimpleWorkflow


class WorkflowTests(unittest.TestCase):
    def test_workflow_plan(self) -> None:
        workflow = SimpleWorkflow()
        plan = workflow.run("session1", "concept", ["graph_explorer"])
        self.assertEqual(plan, ["route", "retrieve", "compose"])


if __name__ == "__main__":
    unittest.main()
