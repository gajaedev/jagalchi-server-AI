from django.db import models
from django.utils import timezone
import uuid


def generate_init_id():
    return f"init_{uuid.uuid4().hex[:8]}"


def generate_resource_id():
    return f"nr_{uuid.uuid4().hex[:8]}"


class InitData(models.Model):
    """로드맵 생성을 위한 초기 데이터 (파일/텍스트)."""

    init_data_id = models.CharField(
        max_length=50,
        primary_key=True,
        default=generate_init_id,
        editable=False
    )
    roadmap_id = models.CharField(max_length=100, help_text="관련 로드맵 ID")
    content = models.TextField(help_text="데이터 내용")
    data_type = models.CharField(
        max_length=10,
        choices=[("file", "File"), ("text", "Text")],
        default="text",
        help_text="데이터 타입 (file/text)"
    )
    filename = models.CharField(max_length=255, null=True, blank=True, help_text="파일명 (파일인 경우)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_init_data"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["roadmap_id"]),
        ]

    def __str__(self):
        return f"{self.init_data_id} ({self.roadmap_id})"


class NodeResource(models.Model):
    """노드에 추천/저장된 학습 자료."""

    resource_id = models.CharField(
        max_length=50,
        primary_key=True,
        default=generate_resource_id,
        editable=False
    )
    node_id = models.CharField(max_length=100, help_text="관련 노드 ID")
    title = models.CharField(max_length=255, help_text="자료 제목")
    url = models.URLField(max_length=500, help_text="자료 URL")
    source = models.CharField(
        max_length=20,
        choices=[("web", "Web"), ("internal", "Internal"), ("generated", "Generated")],
        default="web",
        help_text="출처 (web/internal/generated)"
    )
    description = models.TextField(null=True, blank=True, help_text="자료 설명")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_node_resource"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["node_id"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.node_id})"