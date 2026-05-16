"""Tests for regulatory PDF generation."""
import os
import tempfile

from pipeline.pdf_output import generate_pdf


def test_generate_pdf_regulatory_produces_file() -> None:
    data = {
        "pipeline": "regulatory",
        "doc_name": "esma_communication.pdf",
        "analysis_date": "2026-05-16",
        "user_id": "user-test",
        "language": "en",
        "regulatory": {
            "executive_summary": "A concise summary.",
            "regulatory_references": ["MiFID II Art. 25", "AIFMD Art. 22"],
            "required_actions": [
                {"description": "Submit update", "deadline": "2026-06-30", "source_page": 2},
            ],
        },
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_pdf(data, tmp)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 1000
