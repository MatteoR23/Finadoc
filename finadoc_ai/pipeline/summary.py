"""Regulatory pipeline: summary of a regulatory communication.

Implemented in P7.
"""
from __future__ import annotations

from models.schemas import RegulatoryResult


def run_regulatory_summary(ingested_doc: dict) -> RegulatoryResult:
    """Run the regulatory summary pipeline.

    Steps (P7):
        1. Mask PII with Presidio.
        2. Call mistral-small-latest with prompts/regulatory/summary_v1.txt.
        3. Parse and validate response against RegulatoryResult.
        4. References extracted from text only — nothing inferred.

    Raises:
        NotImplementedError: Until P7.
    """
    raise NotImplementedError("Regulatory summary pipeline not implemented yet (P7)")
