"""PDF report generation via ReportLab platypus.

Report structure:
  - Header (document name, analysis date, group, user)
  - Asset allocation tables with source page + confidence badge (PM)
  - Red flags sorted critical → warning → info (RM)
  - Executive summary + regulatory references + deadlines table (regulatory)
  - Disclaimer

Low-confidence rows are rendered with a visible warning badge.

Implemented in P5.
"""
from __future__ import annotations

from typing import Any


def generate_pdf(data: dict[str, Any], output_path: str) -> str:
    """Generate a PDF report and write it to output_path/report.pdf.

    Args:
        data: Combined analysis data (PM extraction, RM flags, regulatory
              summary — whichever are present).
        output_path: Directory path where report.pdf will be written.

    Returns:
        Absolute path to the generated report.pdf.

    Raises:
        NotImplementedError: Until P5.
    """
    raise NotImplementedError("PDF generation not implemented yet (P5)")
