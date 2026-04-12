"""Mistral API client wrapper.

Uses mistralai SDK v2. Always requests JSON mode.
Prompt templates are loaded from finadoc_ai/prompts/.

Implemented in P4.
"""
from __future__ import annotations


def call_mistral(model: str, system_prompt: str, user_text: str) -> dict:
    """Call the Mistral API and return the parsed JSON response.

    Args:
        model: Mistral model ID (e.g. "mistral-small-latest").
        system_prompt: System prompt string (already loaded from template).
        user_text: Masked document text to analyse.

    Returns:
        Parsed JSON dict from the model response.

    Raises:
        NotImplementedError: Until P4.
    """
    raise NotImplementedError("Mistral LLM client not implemented yet (P4)")


def load_prompt(relative_path: str) -> str:
    """Load a prompt template from the prompts/ directory.

    Args:
        relative_path: Path relative to finadoc_ai/prompts/,
            e.g. "PM/extraction_v1.txt".

    Raises:
        NotImplementedError: Until P4.
    """
    raise NotImplementedError("Prompt loading not implemented yet (P4)")
