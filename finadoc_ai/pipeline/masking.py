"""PII masking via Microsoft Presidio.

Configured for Italian + English spaCy models when available.
The placeholder mapping lives in memory only — never written to disk.
"""
from __future__ import annotations

import logging

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

logger = logging.getLogger(__name__)

_analyzer: AnalyzerEngine | None = None
_languages: list[str] = []


def _get_analyzer() -> tuple[AnalyzerEngine, list[str]]:
    global _analyzer, _languages
    if _analyzer is not None:
        return _analyzer, _languages

    try:
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "en", "model_name": "en_core_web_lg"},
                {"lang_code": "it", "model_name": "it_core_news_lg"},
            ],
        })
        nlp_engine = provider.create_engine()
        _analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en", "it"])
        _languages = ["en", "it"]
        logger.info("Presidio: Italian + English recognizers loaded.")
    except Exception:
        _analyzer = AnalyzerEngine()
        _languages = ["en"]
        logger.warning("Presidio: it_core_news_lg not found, falling back to English-only analysis.")

    return _analyzer, _languages


def mask_text(text: str) -> tuple[str, dict[str, str]]:
    """Detect and replace PII entities with indexed placeholders.

    Same entity value always gets the same placeholder (idempotent within the call).

    Returns:
        (masked_text, mapping) where mapping is {placeholder: original_value}.
    """
    analyzer, langs = _get_analyzer()

    all_results = []
    for lang in langs:
        all_results.extend(analyzer.analyze(text=text, language=lang))

    # Deduplicate overlapping spans globally: keep highest-confidence entity per span.
    # Sort by score descending so that higher-confidence entities are added first.
    all_results.sort(key=lambda r: (-r.score, r.start))
    deduped: list = []
    for result in all_results:
        overlaps = any(
            max(r.start, result.start) < min(r.end, result.end)
            for r in deduped
        )
        if not overlaps:
            deduped.append(result)

    # Process in reverse start order so replacements don't shift earlier indices
    deduped.sort(key=lambda r: r.start, reverse=True)

    mapping: dict[str, str] = {}
    counter: dict[str, int] = {}
    masked = text

    for result in deduped:
        original = masked[result.start:result.end]

        existing = next((k for k, v in mapping.items() if v == original), None)
        if existing:
            placeholder = existing
        else:
            entity_type = result.entity_type
            counter[entity_type] = counter.get(entity_type, 0) + 1
            placeholder = f"<{entity_type}_{counter[entity_type]}>"
            mapping[placeholder] = original

        masked = masked[: result.start] + placeholder + masked[result.end :]

    return masked, mapping


def restore_text(masked_text: str, mapping: dict[str, str]) -> str:
    """Restore original values in a masked string using the placeholder mapping."""
    result = masked_text
    for placeholder, original in mapping.items():
        result = result.replace(placeholder, original)
    return result
