from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from jagalchi_ai.ai_core.models import InitData, NodeResource
from jagalchi_ai.ai_core.service.content_generation.node_content_service import NodeContentService

class NodeContentServiceTests(TestCase):
    def setUp(self):
        self.service = NodeContentService()
        self.init_data = InitData.objects.create(
            roadmap_id="rm_test",
            content="Education curriculum content",
            data_type="text"
        )

    def test_generate_nodes_from_init(self):
        """Init 데이터를 기반으로 노드 생성 테스트 (Fallback 확인)."""
        # GeminiClient는 테스트 환경에서 available=False이므로 Fallback이 작동해야 함
        result = self.service.generate_nodes_from_init(self.init_data.init_data_id)
        self.assertIn("nodes", result)
        self.assertIn("edges", result)
        self.assertEqual(result["nodes"][0]["node_id"], "gen_1")

    def test_generate_nodes_from_init_not_found(self):
        """존재하지 않는 Init Data에 대한 에러 처리."""
        with self.assertRaises(ValueError):
            self.service.generate_nodes_from_init("non_existent")

    def test_generate_node_description(self):
        """노드 설명 생성 테스트 (Fallback 확인)."""
        desc = self.service.generate_node_description("React Hooks")
        self.assertIn("React Hooks", desc)

    def test_save_resource_to_node(self):
        """노드 리소스 저장 테스트."""
        resource = self.service.save_resource_to_node(
            node_id="node_1",
            title="React Tutorial",
            url="https://example.com/react",
            description="Good tutorial"
        )
        self.assertEqual(resource.node_id, "node_1")
        self.assertEqual(resource.title, "React Tutorial")
        self.assertTrue(NodeResource.objects.filter(resource_id=resource.resource_id).exists())

    def test_get_node_resources(self):
        """노드 리소스 목록 조회 테스트."""
        self.service.save_resource_to_node("node_1", "Res 1", "https://url1")
        self.service.save_resource_to_node("node_1", "Res 2", "https://url2")
        self.service.save_resource_to_node("node_2", "Res 3", "https://url3")

        resources = self.service.get_node_resources("node_1")
        self.assertEqual(len(resources), 2)


class NodeContentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.init_data = InitData.objects.create(
            roadmap_id="rm_test",
            content="Education curriculum content",
            data_type="text"
        )

    def test_node_generation_api(self):
        """API: Init 데이터 기반 노드 생성."""
        url = reverse("node-generation")
        response = self.client.get(url, {"init_data_id": self.init_data.init_data_id})
        self.assertEqual(response.status_code, 200)
        self.assertIn("nodes", response.data)

    def test_node_description_api(self):
        """API: 노드 설명 생성."""
        url = reverse("node-description")
        response = self.client.get(url, {"node_title": "Django REST Framework"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["node_title"], "Django REST Framework")
        self.assertIn("description", response.data)

    def test_node_resource_recommendation_api(self):
        """API: 노드 리소스 추천."""
        url = reverse("node-resource-recommendation")
        # mock_data.ROADMAPS에 있는 'rm_frontend'와 그 노드 'node_frontend_1' 사용
        response = self.client.get(url, {"node_id": "node_frontend_1", "roadmap_id": "rm_frontend"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("items", response.data)

    def test_node_resource_save_api(self):
        """API: 노드 리소스 저장."""
        url = reverse("node-resource-save")
        payload = {
            "node_id": "node_123",
            "title": "API Resource",
            "url": "https://api.test/resource",
            "source": "web"
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "API Resource")
        self.assertTrue(NodeResource.objects.filter(node_id="node_123").exists())
