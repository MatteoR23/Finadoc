"""Mistral API client wrapper.

Uses mistralai SDK v2. Always requests JSON mode.
Prompt templates are loaded from finadoc_ai/prompts/.
"""
from __future__ import annotations

import json
import os

from mistralai.client import Mistral

from config import MISTRAL_API_KEY, PROMPTS_DIR

_client: Mistral | None = None


def _get_client() -> Mistral:
    global _client
    if _client is None:
        _client = Mistral(api_key=MISTRAL_API_KEY)
    return _client


def load_prompt(relative_path: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = os.path.join(PROMPTS_DIR, relative_path)
    with open(path, encoding="utf-8") as f:
        return f.read()


def call_mistral(model: str, system_prompt: str, user_text: str) -> dict:
    """Call the Mistral API and return the parsed JSON response.

    Args:
        model: Mistral model ID (e.g. "mistral-small-latest").
        system_prompt: System prompt string.
        user_text: Document text to analyse (already PII-masked).

    Returns:
        Parsed JSON dict from the model response.
    """
    client = _get_client()
    response = client.chat.complete(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return json.loads(content)
