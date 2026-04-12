"""PM pipeline: structured extraction from a fund factsheet.

Implemented in P4.
"""
from __future__ import annotations

from models.schemas import PMExtractionResult


def run_pm_extraction(ingested_doc: dict) -> PMExtractionResult:
    """Run the full PM extraction pipeline on an ingested document.

    Steps (P4):
        1. Mask PII with Presidio.
        2. Call mistral-small-latest with prompts/PM/extraction_v1.txt.
        3. Parse and validate response against PMExtractionResult.
        4. Restore original values where needed.

    Raises:
        NotImplementedError: Until P4.
    """
    raise NotImplementedError("PM extraction pipeline not implemented yet (P4)")
