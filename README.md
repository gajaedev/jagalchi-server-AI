# Jagalchi Server AI

Jagalchi 학습 플랫폼의 AI 기능을 위한 Python/Django 기반 모듈입니다.

## 구성
- `ai_core/`: AI 파이프라인, 스냅샷, 캐시, 스키마 검증
- `docs/ai/ai-spec.md`: 기능 스펙 및 파이프라인 문서

## 로컬 실행(선택)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py test
```
