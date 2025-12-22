from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

try:
    from google import genai
except ImportError:  # pragma: no cover - optional dependency
    genai = None

from jagalchi_ai.ai_core.client.gemini_response import GeminiResponse


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class GeminiClient:
    """Gemini API 클라이언트."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash") -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._model = model
        self._client = None
        self._disabled = os.getenv("AI_DISABLE_LLM") == "true" or os.getenv("AI_DISABLE_EXTERNAL") == "true"
        if self._api_key and genai is not None:
            self._client = genai.Client(api_key=self._api_key)

    @property
    def model_name(self) -> str:
        return self._model

    def available(self) -> bool:
        return self._client is not None and not self._disabled

    def generate_text(self, contents: str) -> str:
        if not self.available():
            return ""
        try:
            response = self._client.models.generate_content(model=self._model, contents=contents)
        except Exception:
            return ""
        return getattr(response, "text", "") or ""

    def generate_json(self, contents: str) -> GeminiResponse:
        raw = self.generate_text(contents)
        if not raw:
            return GeminiResponse(data=None, raw_text="")
        data = _safe_json_parse(raw)
        return GeminiResponse(data=data, raw_text=raw)


def _safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_RE.search(text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
