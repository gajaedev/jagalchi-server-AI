# Jagalchi AI Server API 문서

Jagalchi AI 서버는 학습 로드맵과 기술 카드 기반의 AI 학습 코칭 플랫폼입니다.

## 🚀 빠른 시작

```bash
# Docker로 실행
cd jagalchi-server-AI
docker-compose up -d

# API 문서 확인
open http://localhost:8000/api/docs/
```

## 📋 API 엔드포인트 목록

### 시스템
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health/` | 서버 상태 및 서비스 가용성 확인 |
| GET | `/api/docs/` | Swagger UI API 문서 |
| GET | `/api/redoc/` | ReDoc API 문서 |

### 학습 코치 관련
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ai/record-coach` | 학습 기록 AI 피드백 |
| GET | `/api/ai/learning-coach` | 학습 코치 질문 응답 |
| GET | `/api/ai/learning-pattern` | 사용자 학습 패턴 분석 |

### 로드맵 관련
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ai/related-roadmaps` | 연관 로드맵 추천 |
| GET | `/api/ai/roadmap-generated` | 목표 기반 로드맵 생성 |
| GET | `/api/ai/roadmap-recommendation` | 역할 기반 로드맵 추천 |
| GET/POST | `/api/ai/document-roadmap` | 문서 분석 기반 로드맵 추천 |

### 기술 카드
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ai/tech-cards` | 기술 카드 조회/생성 |
| GET | `/api/ai/tech-fingerprint` | 로드맵 기술 태그 분석 |

### 검색 및 추천
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ai/web-search` | Tavily/Exa 웹 검색 |
| GET | `/api/ai/resource-recommendation` | 학습 자료 추천 |
| GET | `/api/ai/graph-rag` | GraphRAG 컨텍스트 조회 |

### 코멘트 분석
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ai/comment-digest` | 코멘트 요약 |
| GET | `/api/ai/comment-duplicates` | 중복 코멘트 탐지 |

### 통합 데모
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ai/demo` | 모든 AI 기능 통합 데모 |

---

## 🔧 주요 API 사용 예시

### 1. 헬스체크
```bash
curl http://localhost:8000/api/health/
```
```json
{
  "status": "ok",
  "services": {"gemini": true, "tavily": true, "exa": true}
}
```

### 2. 학습 기록 AI 피드백
```bash
curl "http://localhost:8000/api/ai/record-coach?roadmap_id=rm_frontend"
```
```json
{
  "record_id": "rec1",
  "scores": {"quality_score": 68, "evidence_level": 3},
  "strengths": ["링크 기반 근거가 있어 신뢰도가 높다"],
  "next_actions": [{"effort": "2h", "task": "에러 로그 기록 추가"}]
}
```

### 3. 학습 코치 질문
```bash
curl "http://localhost:8000/api/ai/learning-coach?question=React%20학습방법&user_id=user_1"
```
```json
{
  "intent": "concept",
  "toolchain": ["graph_explorer"],
  "answer": "핵심 개념 요약: HTML, CSS, 상태관리...",
  "behavior_summary": {"motivation": 0.3, "ability": 0.0, "dropout_risk": 0.017}
}
```

### 4. 웹 검색 (Tavily/Exa)
```bash
curl "http://localhost:8000/api/ai/web-search?query=Python%20튜토리얼&top_k=5"
```
```json
{
  "query": "Python 튜토리얼",
  "results": [
    {"title": "Python.org", "url": "https://python.org", "score": 0.99}
  ],
  "engines_used": ["tavily", "exa"]
}
```

### 5. 문서 기반 로드맵 추천
```bash
curl -X POST "http://localhost:8000/api/ai/document-roadmap" \
  -H "Content-Type: application/json" \
  -d '{"document": "Python과 Django를 1년간 공부했습니다", "goal": "Backend Developer"}'
```
```json
{
  "extracted_keywords": ["python", "django", "백엔드"],
  "recommended_roadmaps": [
    {"related_roadmap_id": "rm_backend", "score": 0.95}
  ]
}
```

---

## 🔑 환경변수 설정

`.env` 파일 생성:
```bash
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
EXA_API_KEY=your_exa_api_key
```

---

## 🐳 Docker 명령어

```bash
# 빌드 및 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f app

# 컨테이너 재시작
docker-compose restart app

# 종료
docker-compose down
```
