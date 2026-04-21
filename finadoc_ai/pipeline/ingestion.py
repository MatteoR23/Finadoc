"""Document ingestion: PDF (PyMuPDF + pdfplumber) and Excel (pandas/openpyxl)."""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd
import pdfplumber


def ingest_document(path: str, fmt: str) -> dict:
    """Ingest a document and return structured text + metadata.

    Args:
        path: Absolute local path to the file.
        fmt: "pdf" or "xlsx".

    Returns:
        dict with keys: "pages" (list of {text, tables, page_number}),
        "format", "language_hint".

    Raises:
        ValueError: If the PDF has no text layer (scanned PDF).
    """
    if fmt == "pdf":
        return _ingest_pdf(path)
    elif fmt == "xlsx":
        return _ingest_excel(path)
    else:
        raise ValueError(f"Unsupported format: {fmt!r}")


def _ingest_pdf(path: str) -> dict:
    doc = fitz.open(path)
    pages: list[dict] = []
    has_text = False

    for page in doc:
        text = page.get_text()
        if text.strip():
            has_text = True
        pages.append({"page_number": page.number + 1, "text": text, "tables": []})

    doc.close()

    if not has_text:
        raise ValueError("PDF has no text layer — scanned PDFs are not supported.")

    # Overlay table data from pdfplumber
    with pdfplumber.open(path) as plumb:
        for i, page in enumerate(plumb.pages):
            tables = page.extract_tables()
            if tables:
                pages[i]["tables"] = tables

    return {"pages": pages, "format": "pdf", "language_hint": "auto"}


def _ingest_excel(path: str) -> dict:
    xl = pd.ExcelFile(path)
    pages: list[dict] = []

    for i, sheet_name in enumerate(xl.sheet_names):
        df = xl.parse(sheet_name)
        text = f"Sheet: {sheet_name}\n{df.to_string()}"
        pages.append({
            "page_number": i + 1,
            "text": text,
            "tables": [df.values.tolist()],
        })

    return {"pages": pages, "format": "xlsx", "language_hint": "auto"}
