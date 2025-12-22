from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class Document:
    """검색용 문서 단위."""

    doc_id: str
    text: str
    metadata: Dict[str, str]
