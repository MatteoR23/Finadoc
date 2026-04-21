"""PM pipeline: structured extraction from a fund factsheet."""
from __future__ import annotations

import logging

from config import MISTRAL_MODEL_SMALL
from models.schemas import PMExtractionResult
from pipeline.llm import call_mistral, load_prompt
from pipeline.masking import mask_text

logger = logging.getLogger(__name__)

_DOCUMENT_TEXT_MARKER = "\nDocument text:\n{document_text}"


def run_pm_extraction(ingested_doc: dict) -> PMExtractionResult:
    """Run the full PM extraction pipeline on an ingested document.

    Steps:
        1. Stitch all page texts together with page markers.
        2. Mask PII with Presidio.
        3. Call mistral-small-latest with the PM extraction prompt.
        4. Validate the response against PMExtractionResult.
    """
    full_text = "\n\n".join(
        f"[Page {p['page_number']}]\n{p['text']}"
        for p in ingested_doc["pages"]
    )

    masked_text, _mapping = mask_text(full_text)

    prompt_template = load_prompt("PM/extraction_v1.txt")
    # Strip the "{document_text}" placeholder section — document goes as user message
    system_prompt = prompt_template.replace(_DOCUMENT_TEXT_MARKER, "").rstrip()

    # Append language directive to LLM
    language = ingested_doc.get("language", "en")
    lang_name = "Italian" if language == "it" else "English"
    directive = (
        f"\n\nIMPORTANT: All free-text string values (label, description, detail, "
        f"controversies, rating, instrument names) MUST be written in {lang_name}. "
        f"Do NOT translate enum values (severity, confidence levels), field names, "
        f"currency codes, ISIN codes, or dates."
    )
    system_prompt = system_prompt + directive

    raw = call_mistral(MISTRAL_MODEL_SMALL, system_prompt, masked_text)
    logger.debug("Mistral PM extraction raw response: %s", raw)
    if not raw or raw == {}:
        logger.warning("Mistral returned empty response — document may have no extractable data. Text length: %d", len(masked_text))
    return PMExtractionResult.model_validate(raw)
