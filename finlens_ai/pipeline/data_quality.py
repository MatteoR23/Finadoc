"""DQ pipeline: data quality checks on a financial document.

Uses mistral-small-latest (simpler numeric reasoning than RM).
"""
from __future__ import annotations

import logging

from config import MISTRAL_MODEL_SMALL
from models.schemas import DQResult
from pipeline.llm import call_mistral, load_prompt
from pipeline.masking import mask_text

logger = logging.getLogger(__name__)

_DOCUMENT_TEXT_MARKER = "\nDocument text:\n{document_text}"


def run_dq_analysis(ingested_doc: dict) -> DQResult:
    """Run the full DQ data quality pipeline.

    Steps:
        1. Stitch all page texts together with page markers.
        2. Mask PII with Presidio.
        3. Call mistral-small-latest with the DQ prompt.
        4. Validate the response against DQResult.
    """
    full_text = "\n\n".join(
        f"[Page {p['page_number']}]\n{p['text']}"
        for p in ingested_doc["pages"]
    )

    masked_text, _mapping = mask_text(full_text)

    prompt_template = load_prompt("DQ/data_quality_v1.txt")
    system_prompt = prompt_template.replace(_DOCUMENT_TEXT_MARKER, "").rstrip()

    language = ingested_doc.get("language", "en")
    lang_name = "Italian" if language == "it" else "English"
    directive = (
        f"\n\nIMPORTANT: All free-text string values (description, detail, id text) "
        f"MUST be written in {lang_name}. "
        f"Do NOT translate enum values (severity levels), field names, or page numbers."
    )
    system_prompt = system_prompt + directive

    raw = call_mistral(MISTRAL_MODEL_SMALL, system_prompt, masked_text)
    logger.debug("Mistral DQ raw response: %s", raw)
    if not raw or raw == {}:
        logger.warning(
            "Mistral returned empty response for DQ analysis. Text length: %d",
            len(masked_text),
        )
    return DQResult.model_validate(raw)
