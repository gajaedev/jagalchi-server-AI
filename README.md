# Jagalchi Server AI

Jagalchi 학습 플랫폼의 AI 기능을 위한 Python/Django 기반 모듈입니다.

## 구성
- `jagalchi_ai/ai_core/`: AI 파이프라인, 스냅샷, 캐시, 스키마 검증
- `docs/ai/ai-spec.md`: 기능 스펙 및 파이프라인 문서
- `jagalchi_ai/ai_core/scripts/verify_gemini.py`: Gemini 연결 확인 스크립트
- `jagalchi_ai/ai_core/scripts/verify_tavily.py`: Tavily 검색 확인 스크립트
- `jagalchi_ai/ai_core/scripts/verify_exa.py`: Exa 검색 확인 스크립트

## 환경 변수
- `GEMINI_API_KEY`: Google AI Studio 키 (로컬은 `.env` 사용)
- `TAVILY_API_KEY`: Tavily 검색 키 (로컬은 `.env` 사용)
- `EXA_API_KEY`: Exa 검색 키 (로컬은 `.env` 사용)

## 로컬 실행(선택)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py test
```

## Docker 실행
```bash
docker compose up --build
```

## Gemini 연결 확인(선택)
```bash
export GEMINI_API_KEY=your-key
python -m jagalchi_ai.ai_core.scripts.verify_gemini
```

## Tavily 검색 확인(선택)
```bash
export TAVILY_API_KEY=your-key
python -m jagalchi_ai.ai_core.scripts.verify_tavily
```

## Exa 검색 확인(선택)
```bash
export EXA_API_KEY=your-key
python -m jagalchi_ai.ai_core.scripts.verify_exa
```
