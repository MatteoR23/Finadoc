"""PII masking via Microsoft Presidio.

Uses it_core_news_lg and en_core_web_lg spaCy models.
The placeholder mapping lives in memory only — never written to disk.

Implemented in P4.
"""
from __future__ import annotations


def mask_text(text: str) -> tuple[str, dict[str, str]]:
    """Detect and replace PII entities with indexed placeholders.

    Args:
        text: Raw document text (possibly containing PII).

    Returns:
        A tuple of (masked_text, mapping) where mapping is
        {placeholder: original_value} — kept in memory only.

    Raises:
        NotImplementedError: Until P4.
    """
    raise NotImplementedError("PII masking not implemented yet (P4)")


def restore_text(masked_text: str, mapping: dict[str, str]) -> str:
    """Restore original values in a masked string using the mapping.

    Raises:
        NotImplementedError: Until P4.
    """
    raise NotImplementedError("PII restoration not implemented yet (P4)")
