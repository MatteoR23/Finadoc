"""Cross-source consistency checks (deterministic, no LLM).

Verifies:
- All percentage arrays sum to 100% (±0.1% tolerance).
- Figures repeated across pages are consistent.

Discrepancies are returned as red flag dicts with severity "warning".

Implemented in P10.
"""
from __future__ import annotations

from models.schemas import PMExtractionResult, RedFlag


def check_consistency(extraction: PMExtractionResult) -> list[RedFlag]:
    """Run deterministic consistency checks on a PM extraction result.

    Returns a (possibly empty) list of RedFlag objects to be appended
    to the RM red flag list.

    Raises:
        NotImplementedError: Until P10.
    """
    raise NotImplementedError("Consistency checks not implemented yet (P10)")
