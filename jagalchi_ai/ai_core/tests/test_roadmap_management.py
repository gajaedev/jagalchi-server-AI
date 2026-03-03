from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from jagalchi_ai.ai_core.models import InitData
from jagalchi_ai.ai_core.service.roadmap_management.init_data_service import InitDataService

class InitDataServiceTests(TestCase):
    def setUp(self):
        self.service = InitDataService()
        self.roadmap_id = "test_roadmap"
        self.content = "Test content for roadmap"

    def test_create_init_data(self):
        """Init 데이터 생성 테스트."""
        init_data = self.service.create_init_data(
            roadmap_id=self.roadmap_id,
            content=self.content,
            data_type="text"
        )
        self.assertIsNotNone(init_data.init_data_id)
        self.assertEqual(init_data.roadmap_id, self.roadmap_id)
        self.assertEqual(init_data.content, self.content)
        self.assertEqual(init_data.data_type, "text")

    def test_get_list_by_roadmap(self):
        """특정 로드맵의 Init 데이터 목록 조회 테스트."""
        self.service.create_init_data(self.roadmap_id, "Content 1")
        self.service.create_init_data(self.roadmap_id, "Content 2")
        self.service.create_init_data("other_roadmap", "Other Content")

        data_list = self.service.get_list_by_roadmap(self.roadmap_id)
        self.assertEqual(len(data_list), 2)
        for item in data_list:
            self.assertEqual(item.roadmap_id, self.roadmap_id)

    def test_get_init_data(self):
        """Init 데이터 단건 조회 테스트."""
        created = self.service.create_init_data(self.roadmap_id, self.content)
        retrieved = self.service.get_init_data(created.init_data_id)
        self.assertEqual(retrieved.init_data_id, created.init_data_id)
        self.assertEqual(retrieved.content, self.content)

        self.assertIsNone(self.service.get_init_data("non_existent"))

    def test_update_init_data(self):
        """Init 데이터 수정 테스트."""
        created = self.service.create_init_data(self.roadmap_id, self.content)
        new_content = "Updated content"
        updated = self.service.update_init_data(created.init_data_id, new_content)
        self.assertEqual(updated.content, new_content)

        # DB 반영 확인
        db_data = InitData.objects.get(init_data_id=created.init_data_id)
        self.assertEqual(db_data.content, new_content)

    def test_delete_init_data(self):
        """Init 데이터 삭제 테스트."""
        created = self.service.create_init_data(self.roadmap_id, self.content)
        success = self.service.delete_init_data(created.init_data_id)
        self.assertTrue(success)
        self.assertFalse(InitData.objects.filter(init_data_id=created.init_data_id).exists())

        # 없는 데이터 삭제 시도
        self.assertFalse(self.service.delete_init_data("non_existent"))


class InitDataAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.roadmap_id = "api_test_roadmap"
        self.init_data = InitData.objects.create(
            roadmap_id=self.roadmap_id,
            content="Initial content",
            data_type="text"
        )

    def test_list_init_data(self):
        """API: Init Data 목록 조회."""
        url = reverse("init-data-list-create")
        response = self.client.get(url, {"roadmap_id": self.roadmap_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["init_data_id"], self.init_data.init_data_id)

    def test_create_init_data(self):
        """API: Init Data 생성."""
        url = reverse("init-data-list-create")
        payload = {
            "roadmap_id": "new_roadmap",
            "content": "New API content",
            "data_type": "text"
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200) # _serialize returns 200 by default if not specified
        self.assertEqual(response.data["roadmap_id"], "new_roadmap")
        self.assertTrue(InitData.objects.filter(roadmap_id="new_roadmap").exists())

    def test_get_init_data_detail(self):
        """API: Init Data 상세 조회."""
        url = reverse("init-data-detail", kwargs={"init_data_id": self.init_data.init_data_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["content"], self.init_data.content)

    def test_update_init_data(self):
        """API: Init Data 수정."""
        url = reverse("init-data-detail", kwargs={"init_data_id": self.init_data.init_data_id})
        payload = {"content": "Updated content via API"}
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["content"], "Updated content via API")

    def test_delete_init_data(self):
        """API: Init Data 삭제."""
        url = reverse("init-data-detail", kwargs={"init_data_id": self.init_data.init_data_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(InitData.objects.filter(init_data_id=self.init_data.init_data_id).exists())
