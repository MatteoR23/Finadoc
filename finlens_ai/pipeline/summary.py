"""Regulatory pipeline: summary of a regulatory communication."""
from __future__ import annotations

import logging

from config import MISTRAL_MODEL_SMALL
from models.schemas import RegulatoryResult
from pipeline.llm import call_mistral, load_prompt
from pipeline.masking import mask_text

logger = logging.getLogger(__name__)

_DOCUMENT_TEXT_MARKER = "\nDocument text:\n{document_text}"


def run_regulatory_summary(ingested_doc: dict) -> RegulatoryResult:
    """Run regulatory summary pipeline with masked text and schema validation."""
    full_text = "\n\n".join(
        f"[Page {p['page_number']}]\n{p['text']}"
        for p in ingested_doc["pages"]
    )
    masked_text, _mapping = mask_text(full_text)

    prompt_template = load_prompt("regulatory/summary_v1.txt")
    system_prompt = prompt_template.replace(_DOCUMENT_TEXT_MARKER, "").rstrip()

    language = ingested_doc.get("language", "en")
    lang_name = "Italian" if language == "it" else "English"
    directive = (
        f"\n\nIMPORTANT: All free-text string values (executive_summary, reference text, action description) "
        f"MUST be written in {lang_name}. "
        f"Do NOT invent references or deadlines not explicitly stated in the document."
    )
    system_prompt = system_prompt + directive

    raw = call_mistral(MISTRAL_MODEL_SMALL, system_prompt, masked_text)
    logger.debug("Mistral regulatory summary raw response: %s", raw)
    if not raw or raw == {}:
        logger.warning("Mistral returned empty response for regulatory summary.")
    return RegulatoryResult.model_validate(raw)
