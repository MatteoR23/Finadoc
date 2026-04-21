"""RM pipeline: red flag detection in a financial report.

Uses mistral-large-latest for multi-step numeric reasoning.
"""
from __future__ import annotations

import logging

from config import MISTRAL_MODEL_LARGE
from models.schemas import RMResult
from pipeline.llm import call_mistral, load_prompt
from pipeline.masking import mask_text

logger = logging.getLogger(__name__)

_DOCUMENT_TEXT_MARKER = "\nDocument text:\n{document_text}"


def run_rm_analysis(ingested_doc: dict) -> RMResult:
    """Run the full RM red flag detection pipeline.

    Steps:
        1. Stitch all page texts together with page markers.
        2. Mask PII with Presidio.
        3. Call mistral-large-latest with the RM red flags prompt.
        4. Validate the response against RMResult.

    Note: deterministic consistency checks (consistency.py) are deferred to P9.
    """
    full_text = "\n\n".join(
        f"[Page {p['page_number']}]\n{p['text']}"
        for p in ingested_doc["pages"]
    )

    masked_text, _mapping = mask_text(full_text)

    prompt_template = load_prompt("RM/red_flags_v1.txt")
    system_prompt = prompt_template.replace(_DOCUMENT_TEXT_MARKER, "").rstrip()

    # Append language directive to LLM
    language = ingested_doc.get("language", "en")
    lang_name = "Italian" if language == "it" else "English"
    directive = (
        f"\n\nIMPORTANT: All free-text string values (description, detail, id text) "
        f"MUST be written in {lang_name}. "
        f"Do NOT translate enum values (severity levels), field names, or page numbers."
    )
    system_prompt = system_prompt + directive

    raw = call_mistral(MISTRAL_MODEL_LARGE, system_prompt, masked_text)
    logger.debug("Mistral RM red flags raw response: %s", raw)
    if not raw or raw == {}:
        logger.warning(
            "Mistral returned empty response for RM analysis. Text length: %d",
            len(masked_text),
        )
    return RMResult.model_validate(raw)
