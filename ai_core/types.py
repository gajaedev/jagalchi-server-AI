from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class LinkMeta:
    url: str
    title: str = ""
    is_public: bool = False
    status_code: Optional[int] = None


@dataclass
class RoadmapNode:
    node_id: str
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class Roadmap:
    roadmap_id: str
    title: str
    description: str
    nodes: List[RoadmapNode]
    edges: List[tuple[str, str]]
    tags: List[str]
    creator_id: str = ""
    updated_at: Optional[datetime] = None
    difficulty: float = 0.5


@dataclass
class LearningRecord:
    record_id: str
    memo: str
    links: List[LinkMeta]
    node_id: str
    roadmap_id: str


@dataclass
class Comment:
    comment_id: str
    roadmap_id: str
    node_id: Optional[str]
    body: str
    reactions_helpful: int = 0
    reactions_negative: int = 0
    resolved: bool = False
    created_at: Optional[datetime] = None


@dataclass
class TechStack:
    slug: str
    display_name: str
    aliases: List[str]


@dataclass
class RetrievalItem:
    source: str
    item_id: str
    score: float
    snippet: str
    metadata: Dict[str, str] = field(default_factory=dict)
