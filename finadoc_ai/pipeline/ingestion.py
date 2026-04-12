"""Document ingestion: PDF (PyMuPDF + pdfplumber) and Excel (pandas/openpyxl).

Implemented in P4.
"""
from __future__ import annotations


def ingest_document(path: str, fmt: str) -> dict:
    """Ingest a document and return structured text + metadata.

    Args:
        path: Absolute path to the file on the shared volume.
        fmt: "pdf" or "xlsx".

    Returns:
        dict with keys: "pages" (list of {text, tables, page_number}),
        "format", "language_hint".

    Raises:
        ValueError: If the PDF has no text layer (scanned PDF).
        NotImplementedError: Until P4.
    """
    raise NotImplementedError("Document ingestion not implemented yet (P4)")
