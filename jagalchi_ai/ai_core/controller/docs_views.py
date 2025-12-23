from __future__ import annotations

from drf_spectacular.utils import OpenApiTypes, extend_schema
from drf_spectacular.views import SpectacularRedocView, SpectacularSwaggerView


class SwaggerUIView(SpectacularSwaggerView):
    """
    Swagger UI를 표시하는 APIView 래퍼.

    Swagger 화면을 OpenAPI 스키마에 노출하기 위해 APIView로 감싼다.
    """

    @extend_schema(
        summary="Swagger UI",
        description="Swagger UI 문서 화면입니다. 프론트/백엔드가 API 스펙을 확인할 때 사용합니다.",
        responses={200: OpenApiTypes.STR},
    )
    def get(self, request, *args, **kwargs):
        """
        Swagger UI 화면을 렌더링합니다.

        @param {Request} request - DRF 요청 객체.
        @returns {Response} Swagger UI HTML 응답.
        """
        return super().get(request, *args, **kwargs)


class RedocUIView(SpectacularRedocView):
    """
    Redoc UI를 표시하는 APIView 래퍼.

    Redoc 화면을 OpenAPI 스키마에 노출하기 위해 APIView로 감싼다.
    """

    @extend_schema(
        summary="Redoc UI",
        description="Redoc 문서 화면입니다. 디자인 친화적인 문서 뷰를 제공합니다.",
        responses={200: OpenApiTypes.STR},
    )
    def get(self, request, *args, **kwargs):
        """
        Redoc UI 화면을 렌더링합니다.

        @param {Request} request - DRF 요청 객체.
        @returns {Response} Redoc UI HTML 응답.
        """
        return super().get(request, *args, **kwargs)
