from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class TechStack:
    """기술 스택 정의."""

    slug: str
    display_name: str
    aliases: List[str]
