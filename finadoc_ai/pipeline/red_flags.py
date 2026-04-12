"""RM pipeline: red flag detection in a financial report.

Uses mistral-large-latest for multi-step numeric reasoning.

Implemented in P6.
"""
from __future__ import annotations

from models.schemas import RMResult


def run_rm_analysis(ingested_doc: dict) -> RMResult:
    """Run the full RM red flag detection pipeline.

    Steps (P6):
        1. Mask PII with Presidio.
        2. Call mistral-large-latest with prompts/RM/red_flags_v1.txt.
        3. Parse and validate response against RMResult.
        4. Append deterministic consistency warnings from consistency.py.

    Raises:
        NotImplementedError: Until P6.
    """
    raise NotImplementedError("RM red flag pipeline not implemented yet (P6)")
