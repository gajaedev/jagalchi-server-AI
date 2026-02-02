from __future__ import annotations

from typing import List, Optional
from jagalchi_ai.ai_core.models import InitData


class InitDataService:
    """로드맵 Init 데이터 관리 서비스 (DB 기반)."""

    def create_init_data(
        self,
        roadmap_id: str,
        content: str,
        data_type: str = "text",
        filename: Optional[str] = None,
    ) -> InitData:
        """
        Init 데이터를 생성합니다.
        """
        return InitData.objects.create(
            roadmap_id=roadmap_id,
            content=content,
            data_type=data_type,
            filename=filename,
        )

    def get_list_by_roadmap(self, roadmap_id: str) -> List[InitData]:
        """
        특정 로드맵의 Init 데이터 목록을 조회합니다.
        """
        return list(InitData.objects.filter(roadmap_id=roadmap_id))

    def get_init_data(self, init_data_id: str) -> Optional[InitData]:
        """
        Init 데이터를 단건 조회합니다.
        """
        try:
            return InitData.objects.get(init_data_id=init_data_id)
        except InitData.DoesNotExist:
            return None

    def update_init_data(self, init_data_id: str, content: str) -> Optional[InitData]:
        """
        Init 데이터를 수정합니다.
        """
        try:
            init_data = InitData.objects.get(init_data_id=init_data_id)
            init_data.content = content
            init_data.save()
            return init_data
        except InitData.DoesNotExist:
            return None

    def delete_init_data(self, init_data_id: str) -> bool:
        """
        Init 데이터를 삭제합니다.
        """
        try:
            init_data = InitData.objects.get(init_data_id=init_data_id)
            init_data.delete()
            return True
        except InitData.DoesNotExist:
            return False