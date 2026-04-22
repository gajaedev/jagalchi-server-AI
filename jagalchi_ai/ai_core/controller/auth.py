from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission


@dataclass(frozen=True, slots=True)
class AIAccessTokenUser:
    """
    DB 사용자 모델 없이도 DRF의 인증/권한 체크를 통과하기 위한 토큰 기반 유저 객체.
    """

    sub: str
    roadmap_id: Optional[str] = None
    permissions: frozenset[str] = field(default_factory=frozenset)
    raw_claims: dict[str, Any] = field(default_factory=dict)

    @property
    def is_authenticated(self) -> bool:  # DRF IsAuthenticated 호환
        return True

    @property
    def pk(self) -> str:
        # DRF UserRateThrottle 등이 request.user.pk 를 참조한다.
        return self.sub

    def has_any_permission(self, *candidates: str) -> bool:
        perms = self.permissions
        return any(candidate in perms for candidate in candidates)


def _normalize_permissions(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        items = [item.strip().upper() for item in value.split(",") if item.strip()]
        return frozenset(items)
    if isinstance(value, Iterable):
        items: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                items.append(item.strip().upper())
        return frozenset(items)
    return frozenset()


def _build_gateway_user(request) -> Optional[AIAccessTokenUser]:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return None

    permissions = _normalize_permissions(request.headers.get("X-Permissions"))
    roadmap_id = request.headers.get("X-Roadmap-ID")

    return AIAccessTokenUser(
        sub=str(user_id),
        roadmap_id=roadmap_id,
        permissions=permissions,
        raw_claims={
            "sub": str(user_id),
            "roadmapId": roadmap_id,
            "permissions": list(permissions),
            "source": "gateway-headers",
        },
    )


class AIAccessTokenAuthentication(BaseAuthentication):
    """
    Authorization: Bearer <jwt> 헤더 기반 JWT 인증.

    토큰 페이로드 예시:
      {
        "sub": "user-1",
        "roadmapId": "roadmap-1",
        "permissions": ["EDIT"],
        "exp": 1893456000
      }
    """

    keyword = "Bearer"

    def authenticate(self, request):
        if not getattr(settings, "AI_AUTH_ENABLED", True):
            return None

        gateway_user = _build_gateway_user(request)
        if gateway_user is not None:
            return (gateway_user, gateway_user.raw_claims)

        auth = get_authorization_header(request).split()
        if not auth:
            return None

        if auth[0].lower() != b"bearer":
            raise AuthenticationFailed(
                "Invalid authorization header. Expected Bearer token."
            )

        if len(auth) != 2:
            raise AuthenticationFailed(
                "Invalid authorization header. Expected 'Bearer <token>'."
            )

        token = auth[1].decode("utf-8")
        secret = getattr(settings, "AI_AUTH_JWT_SECRET", "") or ""
        algorithm = getattr(settings, "AI_AUTH_JWT_ALGORITHM", "HS256")
        leeway = int(getattr(settings, "AI_AUTH_JWT_LEEWAY_SECONDS", 0) or 0)

        if not secret:
            # 설정 누락은 401로 내려서 클라이언트가 "인증 필요"로 처리하게 한다.
            raise AuthenticationFailed(
                "Server auth misconfigured: AI_AUTH_JWT_SECRET is empty."
            )

        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[algorithm],
                options={"require": ["sub", "exp"]},
                leeway=leeway,
            )
        except jwt.ExpiredSignatureError as e:
            raise AuthenticationFailed("Token expired.") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed("Invalid token.") from e

        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub.strip():
            raise AuthenticationFailed(
                "Invalid token payload: 'sub' must be a non-empty string."
            )

        roadmap_id = payload.get("roadmapId") or payload.get("roadmap_id")
        if roadmap_id is not None and (
            not isinstance(roadmap_id, str) or not roadmap_id.strip()
        ):
            raise AuthenticationFailed(
                "Invalid token payload: 'roadmapId' must be a string when provided."
            )

        permissions = _normalize_permissions(payload.get("permissions"))

        user = AIAccessTokenUser(
            sub=sub,
            roadmap_id=roadmap_id,
            permissions=permissions,
            raw_claims=payload,
        )
        return (user, payload)

    def authenticate_header(self, request) -> str:
        return self.keyword


class HasAIAccess(BasePermission):
    """
    AI API 접근 제어.

    - AI_AUTH_ENABLED=false: 항상 허용
    - 안전 메서드(GET/HEAD/OPTIONS): READ 또는 EDIT 또는 ADMIN
    - 변경 메서드(POST/PUT/PATCH/DELETE): EDIT 또는 ADMIN
    """

    def has_permission(self, request, view) -> bool:
        if not getattr(settings, "AI_AUTH_ENABLED", True):
            return True

        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            return False

        permissions: frozenset[str] = getattr(user, "permissions", frozenset())

        # 최소 권한 모델: EDIT는 READ를 포함한다고 간주
        if request.method in SAFE_METHODS:
            return (
                "READ" in permissions or "EDIT" in permissions or "ADMIN" in permissions
            )
        return "EDIT" in permissions or "ADMIN" in permissions


def get_ai_user(request) -> Optional[AIAccessTokenUser]:
    user = getattr(request, "user", None)
    return user if isinstance(user, AIAccessTokenUser) else None


def resolve_scoped_param(
    request,
    *,
    param_value: Optional[str],
    token_value: Optional[str],
    field_name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    쿼리/바디 파라미터가 토큰 스코프(sub/roadmap_id)와 충돌하면 403을 반환하게 한다.
    """

    if param_value and token_value and param_value != token_value:
        raise PermissionDenied(f"{field_name} does not match token scope.")

    return param_value or token_value or default
