from datetime import datetime, timedelta

from .types import Comment, EventLog, LearningRecord, LinkMeta, Roadmap, RoadmapNode, TechStack


ROADMAPS = {
    "rm_frontend": Roadmap(
        roadmap_id="rm_frontend",
        title="Frontend 기본",
        description="HTML/CSS/JS를 기반으로 프론트엔드 기초를 학습하는 로드맵",
        nodes=[
            RoadmapNode(node_id="node_html", title="HTML 구조", tags=["html"]),
            RoadmapNode(node_id="node_css", title="CSS 레이아웃", tags=["css", "flexbox"]),
            RoadmapNode(node_id="node_js", title="JavaScript 기초", tags=["javascript"]),
        ],
        edges=[("node_html", "node_css"), ("node_css", "node_js")],
        tags=["frontend", "html", "css", "javascript"],
        creator_id="user_a",
        updated_at=datetime.utcnow() - timedelta(days=2),
        difficulty=0.4,
    ),
    "rm_backend": Roadmap(
        roadmap_id="rm_backend",
        title="Backend 기본",
        description="API 설계와 데이터베이스, 서버 운영을 다루는 로드맵",
        nodes=[
            RoadmapNode(node_id="node_api", title="REST API", tags=["api", "rest"]),
            RoadmapNode(node_id="node_db", title="Database", tags=["database", "sql"]),
        ],
        edges=[("node_api", "node_db")],
        tags=["backend", "api", "database"],
        creator_id="user_b",
        updated_at=datetime.utcnow() - timedelta(days=5),
        difficulty=0.6,
    ),
    "rm_react": Roadmap(
        roadmap_id="rm_react",
        title="React 심화",
        description="React와 상태관리, 성능 최적화를 다루는 로드맵",
        nodes=[
            RoadmapNode(node_id="node_hooks", title="Hooks", tags=["react", "hooks"]),
            RoadmapNode(node_id="node_state", title="상태관리", tags=["redux", "zustand"]),
        ],
        edges=[("node_hooks", "node_state")],
        tags=["react", "frontend", "state-management"],
        creator_id="user_c",
        updated_at=datetime.utcnow() - timedelta(days=1),
        difficulty=0.7,
    ),
}

TECH_STACKS = {
    "react": TechStack(slug="react", display_name="React", aliases=["react", "jsx"]),
    "vue": TechStack(slug="vue", display_name="Vue", aliases=["vue", "vue.js"]),
    "django": TechStack(slug="django", display_name="Django", aliases=["django", "drf"]),
    "zustand": TechStack(slug="zustand", display_name="Zustand", aliases=["zustand"]),
    "redux": TechStack(slug="redux", display_name="Redux", aliases=["redux", "redux-toolkit"]),
}

COMMON_PITFALLS = {
    "react": [
        "의존성 배열을 누락해 무한 렌더가 발생하는 케이스가 많다.",
        "상태 업데이트가 비동기라서 최신 값이 반영되지 않는 경우가 있다.",
    ],
    "database": [
        "인덱스 없이 대량 조회를 해서 응답이 느려지는 문제가 자주 발생한다.",
    ],
}

GOOD_RECORD_EXAMPLES = [
    "목표: React useEffect 동작을 정확히 이해한다. 문제: 의존성 배열 누락으로 렌더 루프 발생. 해결: lint 규칙 추가 및 의존성 배열 수정. 다음: custom hook으로 공통 로직 분리.",
    "목표: REST API 페이징 구현. 문제: 대용량 목록 조회에서 응답 지연. 해결: cursor 기반 페이징 도입, 쿼리 인덱스 추가. 다음: 캐시 레이어 도입 검토.",
]

TECH_SOURCES = {
    "react": [
        {
            "title": "React 공식 문서",
            "url": "https://react.dev",
            "content": "React는 UI를 만들기 위한 JavaScript 라이브러리다. 컴포넌트 기반 설계와 선언형 UI가 핵심이다.",
            "fetched_at": "2025-01-02",
        },
        {
            "title": "React Release Notes",
            "url": "https://react.dev/learn",
            "content": "Hooks를 통해 컴포넌트 로직을 재사용할 수 있다. 성능 최적화를 위해 memoization 전략을 제공한다.",
            "fetched_at": "2025-01-05",
        },
    ],
    "django": [
        {
            "title": "Django Docs",
            "url": "https://docs.djangoproject.com",
            "content": "Django는 안정적인 웹 개발을 위해 MTV 구조와 풍부한 ORM 기능을 제공한다.",
            "fetched_at": "2025-01-03",
        },
    ],
}

COMMENTS = [
    Comment(
        comment_id="c1",
        roadmap_id="rm_frontend",
        node_id="node_js",
        body="useEffect에서 의존성 배열을 비우면 렌더가 반복돼요",
        reactions_helpful=3,
        reactions_negative=1,
        resolved=False,
        created_at=datetime.utcnow() - timedelta(days=3),
    ),
    Comment(
        comment_id="c2",
        roadmap_id="rm_frontend",
        node_id="node_js",
        body="JS async/await 에러 처리를 어떻게 정리하나요?",
        reactions_helpful=5,
        reactions_negative=0,
        resolved=False,
        created_at=datetime.utcnow() - timedelta(days=5),
    ),
    Comment(
        comment_id="c3",
        roadmap_id="rm_backend",
        node_id="node_db",
        body="인덱스를 추가했는데도 느려요. explain 보는 법?",
        reactions_helpful=2,
        reactions_negative=2,
        resolved=False,
        created_at=datetime.utcnow() - timedelta(days=7),
    ),
]

LEARNING_RECORDS = [
    LearningRecord(
        record_id="rec1",
        memo="React useEffect 무한 렌더 이슈를 해결했다. 의존성 배열을 추가했고 lint를 설정함. 다음은 custom hook으로 분리할 예정.",
        links=[LinkMeta(url="https://example.com/demo", title="Demo", is_public=True, status_code=200)],
        node_id="node_js",
        roadmap_id="rm_frontend",
    )
]

EVENT_LOGS = [
    EventLog(
        event_type="record_feedback_view",
        user_id="user_1",
        roadmap_id="rm_frontend",
        node_id="node_js",
        created_at=datetime.utcnow() - timedelta(days=1),
    ),
    EventLog(
        event_type="rec_click",
        user_id="user_1",
        roadmap_id="rm_frontend",
        node_id="node_css",
        created_at=datetime.utcnow() - timedelta(days=2),
    ),
    EventLog(
        event_type="rec_impression",
        user_id="user_1",
        roadmap_id="rm_backend",
        node_id=None,
        created_at=datetime.utcnow() - timedelta(days=4),
    ),
    EventLog(
        event_type="record_feedback_view",
        user_id="user_1",
        roadmap_id="rm_frontend",
        node_id="node_html",
        created_at=datetime.utcnow() - timedelta(days=6),
    ),
    EventLog(
        event_type="rec_click",
        user_id="user_1",
        roadmap_id="rm_react",
        node_id="node_hooks",
        created_at=datetime.utcnow() - timedelta(days=8),
    ),
]

CO_FOLLOW = {
    "rm_frontend": {"rm_react": 0.32, "rm_backend": 0.18},
    "rm_backend": {"rm_frontend": 0.22},
}

CO_COMPLETE = {
    "rm_frontend": {"rm_react": 0.41, "rm_backend": 0.15},
    "rm_backend": {"rm_frontend": 0.27},
}

SIMILAR_USER = {
    "rm_frontend": {"rm_react": 0.25},
}

POPULARITY = {
    "rm_frontend": 1200,
    "rm_backend": 800,
    "rm_react": 900,
}

CREATOR_TRUST = {
    "user_a": 0.7,
    "user_b": 0.65,
    "user_c": 0.82,
}
