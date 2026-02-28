from django.test import TestCase, override_settings
from rest_framework.test import APIClient

@override_settings(
    AI_AUTH_ENABLED=False,
)
class N8nIntegrationSmokeTestTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_smoke_test_returns_ok(self):
        resp = self.client.get("/ai/integration/smoke-test")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})
