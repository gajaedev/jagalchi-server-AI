# Jagalchi AI Spec

본 문서는 Jagalchi AI 기능의 스키마, 파이프라인, 캐시/비용 전략을 정의한다.

## 공통 원칙
- 멀티스테이지: Retrieval → Judge → Compose
- 출력은 고정 JSON 스키마로만 제공
- 결과는 스냅샷 저장 + 버전 관리
- 비용 최적화: 입력/소스 해시 동일 시 재생성 금지
- 재현 가능성: model_version, prompt_version, retrieval_evidence, created_at 포함

## 공통 모듈
- `hashing`: 입력/소스 해시 생성
- `snapshot`: 스냅샷 캐시 저장
- `schema_validation`: 스키마 검증
- `vector_store`: in-memory 벡터 스토어 인터페이스
- `retrieval`: BM25 + Vector + Graph 하이브리드
- `ranking`: 연관 로드맵 랭킹 가중치
- `model_routing`: 작은 모델 우선 라우팅
- `graph_rag`: 그래프 기반 근거 수집
- `roadmap_generator`: 그래프 RAG 기반 로드맵 생성
- `resource_recommender`: 자료 추천 검색
- `learning_analytics`: 학습 패턴 분석
- `gemini_client`: Gemini LLM 호출(선택)

---

## 1) Record Coach (학습 기록 AI 피드백)
### 파이프라인
1. Retrieval
   - query = node title + tags + record summary
   - sources: tech_cards chunks, common_pitfalls, good_record_examples
   - 하이브리드 검색으로 evidence 수집
2. Judge
   - 규칙 기반 루브릭 점수화
   - evidence_level, structure_score, specificity_score, reproducibility_score, quality_score
3. Compose
   - quick: 점수/질문만 반환
   - full: rewrite_suggestions 생성

### 캐시
- record_hash(메모+링크+노드+compose_level) 동일 시 재사용
- 스냅샷에 prompt_version 기록

### 스키마
```json
{
  "record_id": "...",
  "model_version": "...",
  "prompt_version": "...",
  "created_at": "...",
  "scores": {
    "evidence_level": 2,
    "structure_score": 60,
    "specificity_score": 45,
    "reproducibility_score": 80,
    "quality_score": 62
  },
  "strengths": ["..."],
  "gaps": ["..."],
  "rewrite_suggestions": {
    "portfolio_bullets": ["..."],
    "improved_memo": "..."
  },
  "next_actions": [
    {"effort": "10m", "task": "..."}
  ],
  "followup_questions": ["..."],
  "retrieval_evidence": [
    {"source": "tech_card", "id": "...", "snippet": "..."}
  ]
}
```

---

## 2) Related Roadmaps (로드맵 연관 추천)
### 파이프라인
- 후보 생성 4트랙: 행동 기반, 콘텐츠 기반, 구조 기반, 사회 기반
- 랭킹 피처: tag_overlap, creator_trust_score, completion_rate, freshness, popularity, difficulty_match
- 결과는 배치/스냅샷 중심

### 스키마
```json
{
  "roadmap_id": "...",
  "generated_at": "...",
  "candidates": [
    {
      "related_roadmap_id": "...",
      "score": 0.83,
      "reasons": [
        {"type": "co_complete", "value": 0.31},
        {"type": "tag_overlap", "value": 4}
      ]
    }
  ],
  "model_version": "ranker_v1",
  "evidence_snapshot": {"tracks": ["..."], "candidate_count": 3}
}
```

---

## 3) Tech Cards (기술 카드)
### 파이프라인
- Fetch → Chunk → Index → Compose → Snapshot
- 소스 해시 동일 시 재생성 금지

### 스키마
```json
{
  "tech_slug": "react",
  "version": "2025-12-xx",
  "summary": "...",
  "why_it_matters": ["..."],
  "when_to_use": ["..."],
  "alternatives": [{"slug": "...", "why": "..."}],
  "pitfalls": ["..."],
  "learning_path": [
    {"stage": "basic", "items": ["..."]}
  ],
  "sources": [
    {"title": "...", "url": "...", "fetched_at": "..."}
  ],
  "generated_by": {"model_version": "...", "prompt_version": "..."}
}
```

---

## 4) Tech Fingerprint (태그/기술 지문)
### 파이프라인
1. 룰 기반 alias 매칭
2. 경량 분류(타입/신뢰도)
3. 필요 시 rationale 생성

### 스키마
```json
{
  "roadmap_id": "...",
  "tags": [
    {"tech_slug": "zustand", "type": "alternative", "confidence": 0.72, "rationale": "..."}
  ],
  "generated_at": "...",
  "model_version": "tagger_v1"
}
```

---

## 5) Comment Intelligence (코멘트 인텔리전스)
### 기능
- Duplicate question suggest: 벡터 검색만 사용
- Comment digest: 클러스터링 + 대표 문장 추출 + 1회 compose
- Bottleneck score: 질문 수/부정 반응/해결률 기반

### 스키마
```json
{
  "roadmap_id": "...",
  "period": "last_14d",
  "highlights": ["..."],
  "bottlenecks": [{"node_id": "...", "score": 0.81, "top_topics": ["..."]}],
  "generated_by": {"model_version": "digest_v1"}
}
```

---

## 6) GraphRAG + 로드맵 생성
### GraphRAG 파이프라인
- Vector 검색으로 후보 노드 수집
- 그래프 인접 노드 확장으로 근거 강화
- 증거 스냅샷에 노드/엣지 포함

### 로드맵 생성 파이프라인
1. Retrieval: GraphRAG로 후보 노드 수집
2. Judge: 토큰/태그 유사도 기반 노드 정렬
3. Compose: LLM(선택) 또는 규칙 기반 구성

### 스키마
```json
{
  "roadmap_id": "generated",
  "title": "...",
  "description": "...",
  "nodes": [{"node_id": "...", "title": "...", "tags": ["..."]}],
  "edges": [{"source": "...", "target": "..."}],
  "tags": ["..."],
  "model_version": "...",
  "prompt_version": "...",
  "created_at": "...",
  "retrieval_evidence": [{"source": "graph", "id": "...", "snippet": "..."}]
}
```

---

## 7) 자료 추천
### 파이프라인
- BM25 + Vector 하이브리드 검색
- 근거 스냅샷으로 추천 이유 확인 가능

### 스키마
```json
{
  "query": "...",
  "generated_at": "...",
  "items": [
    {"title": "...", "url": "...", "source": "resource", "score": 0.82}
  ],
  "model_version": "retriever_v1",
  "retrieval_evidence": [{"source": "resource", "id": "...", "snippet": "..."}]
}
```

---

## 8) 학습 패턴 분석 및 추천
### 파이프라인
- 이벤트 로그 집계 → 패턴 계산 → 규칙 기반 추천
- 캐시/스냅샷으로 반복 계산 절감

### 스키마
```json
{
  "user_id": "...",
  "period": "last_30d",
  "patterns": {
    "active_days": 10,
    "avg_session_gap_days": 2.3,
    "completion_velocity": 0.4
  },
  "recommendations": ["..."],
  "model_version": "pattern_v1",
  "generated_at": "..."
}
```
