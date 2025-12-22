# =============================================================================
# Jagalchi AI Server - 프로덕션 Docker 이미지
# =============================================================================
# 멀티스테이지 빌드를 통해 최적화된 프로덕션 이미지를 생성합니다.
#
# 빌드 방법:
#   docker build -t jagalchi-ai:latest .
#   docker build --target development -t jagalchi-ai:dev .
#
# 실행 방법:
#   docker run -p 8000:8000 --env-file .env jagalchi-ai:latest
# =============================================================================

# -----------------------------------------------------------------------------
# 1단계: 기본 이미지 (공통 설정)
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS base

# 메타데이터 라벨 설정
LABEL maintainer="Jagalchi AI Team"
LABEL version="1.0.0"
LABEL description="Jagalchi AI Server - 학습 로드맵 AI 추천 시스템"

# Python 환경 최적화 설정
# - PYTHONDONTWRITEBYTECODE: .pyc 파일 생성 방지 (컨테이너 크기 최소화)
# - PYTHONUNBUFFERED: 출력 버퍼링 비활성화 (로그 즉시 출력)
# - PYTHONFAULTHANDLER: 세그폴트 발생 시 트레이스백 출력
# - PYTHONHASHSEED: 해시 시드 고정 (재현 가능성)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 작업 디렉토리 설정
WORKDIR /app

# -----------------------------------------------------------------------------
# 2단계: 빌드 스테이지 (의존성 설치)
# -----------------------------------------------------------------------------
FROM base AS builder

# 빌드 도구 및 시스템 의존성 설치
# - libgomp1: OpenMP 라이브러리 (FAISS, scikit-learn 등에 필요)
# - build-essential: C/C++ 컴파일러 (일부 패키지 빌드용)
# - curl: 헬스체크 및 파일 다운로드용
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# pip 업그레이드 및 가상환경 생성
RUN python -m pip install --upgrade pip setuptools wheel

# 의존성 먼저 설치 (Docker 캐시 최적화)
# 소스 코드 변경 시 의존성 재설치 방지
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# 3단계: 개발 이미지
# -----------------------------------------------------------------------------
FROM builder AS development

# 개발용 추가 도구 설치
RUN pip install --no-cache-dir \
    ipython \
    ipdb \
    watchfiles

# 소스 코드 복사
COPY . /app/

# 개발 서버 포트 노출
EXPOSE 8000

# 개발 서버 실행 (핫 리로드 활성화)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# -----------------------------------------------------------------------------
# 4단계: 프로덕션 이미지
# -----------------------------------------------------------------------------
FROM base AS production

# 런타임 의존성만 설치 (빌드 도구 제외)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 빌드 스테이지에서 설치된 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 비root 사용자 생성 (보안 강화)
# - 컨테이너가 root로 실행되지 않도록 함
# - 호스트 시스템과의 권한 분리
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# 소스 코드 복사
COPY --chown=appuser:appgroup . /app/

# 정적 파일 수집 디렉토리 생성
RUN mkdir -p /app/staticfiles /app/logs \
    && chown -R appuser:appgroup /app/staticfiles /app/logs

# 비root 사용자로 전환
USER appuser

# 정적 파일 수집 (Django collectstatic)
RUN python manage.py collectstatic --noinput --clear 2>/dev/null || true

# 프로덕션 포트 노출
EXPOSE 8000

# 헬스체크 설정
# - 30초마다 /api/health 엔드포인트 확인
# - 5초 타임아웃, 3번 실패 시 unhealthy 상태
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

# Gunicorn을 사용한 프로덕션 서버 실행
# - workers: CPU 코어 수 * 2 + 1 권장
# - timeout: 요청 타임아웃 (AI 처리 시간 고려)
# - graceful-timeout: 우아한 종료 대기 시간
# - access-logfile: 액세스 로그를 stdout으로
# - error-logfile: 에러 로그를 stderr로
CMD ["gunicorn", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--timeout", "120", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "50", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--capture-output", \
    "--enable-stdio-inheritance", \
    "jagalchi_ai.asgi:application"]
