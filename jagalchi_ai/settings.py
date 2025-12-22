"""
=============================================================================
Jagalchi AI Server - Django 설정 모듈 (Settings Module)
=============================================================================

이 모듈은 Django 프로젝트의 전체 설정을 관리합니다.
`pydantic-settings`를 활용하여 환경변수를 타입 안전(Type-Safe)하게 로드하고 검증합니다.

설계 원칙:
    1.  **환경 분리 (Environment Isolation)**: `.env` 파일 및 환경변수를 통해 개발/운영 환경을 철저히 분리합니다.
    2.  **타입 검증 (Type Validation)**: Pydantic을 사용하여 잘못된 환경변수 입력 시 즉시 오류를 발생시켜,
        잘못된 설정으로 인한 런타임 이슈를 예방합니다.
    3.  **보안 강화 (Security)**: 시크릿 키, 디버그 모드 등 민감한 정보는 반드시 검증된 값을 사용합니다.
    4.  **명시적 구성 (Explicit Configuration)**: 암묵적인 기본값 대신 명시적인 설정을 지향합니다.

주요 환경변수:
    - `DJANGO_SECRET_KEY`: 보안 서명용 비밀키 (필수)
    - `DJANGO_DEBUG`: 디버그 모드 활성화 여부 (운영 환경에서는 반드시 False)
    - `DATABASE_URL`: 데이터베이스 연결 문자열
    - `TAVILY_API_KEY`: 웹 검색용 API 키

자세한 내용은 `docs/CONVENTIONS.md`를 참조하십시오.
=============================================================================
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# -----------------------------------------------------------------------------
# 1. 환경변수 스키마 정의 (Pydantic Settings)
# -----------------------------------------------------------------------------
# 프로젝트 루트 디렉토리 (manage.py 위치)
BASE_DIR = Path(__file__).resolve().parent.parent

class EnvSettings(BaseSettings):
    """
    환경변수 로딩 및 검증을 위한 Pydantic 모델.
    모든 환경변수는 이 클래스를 통해 접근해야 합니다.
    """
    # Django 핵심 설정
    DJANGO_SECRET_KEY: SecretStr = Field(
        default="django-insecure-dev-only-do-not-use-in-production",
        description="Django 시크릿 키"
    )
    DJANGO_DEBUG: bool = Field(default=False, description="디버그 모드")
    DJANGO_ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "0.0.0.0"],
        description="허용 호스트 목록"
    )

    # 데이터베이스 설정
    DATABASE_ENGINE: str = "django.db.backends.sqlite3"
    DATABASE_NAME: str = str(BASE_DIR / "db.sqlite3")
    DATABASE_USER: str = ""
    DATABASE_PASSWORD: str = ""
    DATABASE_HOST: str = ""
    DATABASE_PORT: str = ""
    DATABASE_CONN_MAX_AGE: int = 60

    # AI 클라이언트 설정
    GEMINI_API_KEY: Optional[SecretStr] = None
    TAVILY_API_KEY: Optional[SecretStr] = None
    EXA_API_KEY: Optional[SecretStr] = None
    
    AI_DISABLE_LLM: bool = False
    AI_DISABLE_EXTERNAL: bool = False
    AI_DEFAULT_MODEL: str = "gemini-2.5-flash"
    AI_TIMEOUT: int = 30
    AI_MAX_RETRIES: int = 3

    # 캐시 (Redis) 설정
    REDIS_URL: Optional[str] = None
    CACHE_TIMEOUT: int = 300
    CACHE_MAX_ENTRIES: int = 1000

    # CORS 설정
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="CORS 허용 오리진"
    )

    # 보안 설정 (Prod)
    SECURE_SSL_REDIRECT: bool = False
    SECURE_HSTS_SECONDS: int = 31536000

    # 로깅 레벨
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 정의되지 않은 환경변수는 무시
        case_sensitive=True
    )

# 설정 로드 (싱글톤)
try:
    env = EnvSettings()
except Exception as e:
    # 설정 로드 실패 시 치명적 오류로 간주하고 프로세스 종료
    print(f"=================================================================")
    print(f" [CRITICAL] 환경변수 설정 로드 실패")
    print(f" .env 파일 또는 환경변수를 확인해주세요.")
    print(f" Error: {e}")
    print(f"=================================================================")
    sys.exit(1)


# -----------------------------------------------------------------------------
# 2. Django 설정 매핑
# -----------------------------------------------------------------------------

SECRET_KEY = env.DJANGO_SECRET_KEY.get_secret_value()
DEBUG = env.DJANGO_DEBUG
ALLOWED_HOSTS = env.DJANGO_ALLOWED_HOSTS

# -----------------------------------------------------------------------------
# 애플리케이션 정의
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django 기본 앱
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # 서드파티 앱
    "rest_framework",               # Django REST Framework
    "drf_spectacular",              # OpenAPI 스키마
    "corsheaders",                  # CORS

    # 프로젝트 앱 (비즈니스 로직)
    "jagalchi_ai.ai_core",
]

MIDDLEWARE = [
    # 보안 (가장 먼저)
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # 정적 파일
    
    # CORS (CommonMiddleware보다 먼저)
    "corsheaders.middleware.CorsMiddleware",
    
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "jagalchi_ai.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "jagalchi_ai.wsgi.application"
ASGI_APPLICATION = "jagalchi_ai.asgi.application"

# -----------------------------------------------------------------------------
# 데이터베이스 설정
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": env.DATABASE_ENGINE,
        "NAME": env.DATABASE_NAME,
        "USER": env.DATABASE_USER,
        "PASSWORD": env.DATABASE_PASSWORD,
        "HOST": env.DATABASE_HOST,
        "PORT": env.DATABASE_PORT,
        "CONN_MAX_AGE": env.DATABASE_CONN_MAX_AGE,
    }
}

# -----------------------------------------------------------------------------
# 비밀번호 검증
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# 국제화 및 시간대
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# 정적 파일 (Static Files)
# -----------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------------
# CORS 설정
# -----------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG  # 개발 모드일 때만 전체 허용
CORS_ALLOWED_ORIGINS = env.CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = [
    "accept", "accept-encoding", "authorization", "content-type",
    "dnt", "origin", "user-agent", "x-csrftoken", "x-requested-with",
]

# -----------------------------------------------------------------------------
# Django REST Framework
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNICODE_JSON": True,  # 한글 깨짐 방지
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ] + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
}

# -----------------------------------------------------------------------------
# OpenAPI (Swagger) 설정
# -----------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Jagalchi AI API",
    "DESCRIPTION": "Jagalchi AI 서버 REST API 문서 (Generated by drf-spectacular)",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# -----------------------------------------------------------------------------
# 로깅 (Logging)
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {module}:{lineno} - {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[{asctime}] {levelname} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose" if DEBUG else "simple",
            "stream": sys.stdout,
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "jagalchi.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "jagalchi_ai.ai_core": {"handlers": ["console"], "level": env.LOG_LEVEL, "propagate": False},
        "": {"handlers": ["console"], "level": env.LOG_LEVEL},
    },
}
(BASE_DIR / "logs").mkdir(exist_ok=True)

# -----------------------------------------------------------------------------
# 캐시 설정
# -----------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
        "TIMEOUT": env.CACHE_TIMEOUT,
        "OPTIONS": {"MAX_ENTRIES": env.CACHE_MAX_ENTRIES},
    }
}

if env.REDIS_URL:
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env.REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }

# -----------------------------------------------------------------------------
# AI 관련 설정 (전역 변수로 노출)
# -----------------------------------------------------------------------------
GEMINI_API_KEY = env.GEMINI_API_KEY.get_secret_value() if env.GEMINI_API_KEY else ""
TAVILY_API_KEY = env.TAVILY_API_KEY.get_secret_value() if env.TAVILY_API_KEY else ""
EXA_API_KEY = env.EXA_API_KEY.get_secret_value() if env.EXA_API_KEY else ""

AI_DISABLE_LLM = env.AI_DISABLE_LLM
AI_DISABLE_EXTERNAL = env.AI_DISABLE_EXTERNAL
AI_DEFAULT_MODEL = env.AI_DEFAULT_MODEL
AI_TIMEOUT = env.AI_TIMEOUT
AI_MAX_RETRIES = env.AI_MAX_RETRIES

# -----------------------------------------------------------------------------
# 운영 환경 보안 설정
# -----------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env.SECURE_SSL_REDIRECT
    SECURE_HSTS_SECONDS = env.SECURE_HSTS_SECONDS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")