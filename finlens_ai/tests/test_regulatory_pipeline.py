"""Tests for regulatory endpoint and summary pipeline integration."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


def _valid_request() -> dict:
    return {
        "document_s3_key": "documents/abc/regulatory.pdf",
        "documents_bucket": "finlens-documents",
        "document_format": "pdf",
        "language": "auto",
        "outputs_bucket": "finlens-outputs",
        "output_s3_prefix": "analyses/abc/",
        "user_context": {"user_id": "u-1", "groups": ["PM"]},
        "analysis_id": "abc",
        "callback_url": "",
    }


def test_analyze_regulatory_success() -> None:
    client = TestClient(app)
    req = _valid_request()

    with patch("main.s3.download_to_tempfile") as dl, \
         patch("main.ingest_document") as ingest, \
         patch("main.run_regulatory_summary") as run_reg, \
         patch("main.s3.upload_bytes") as upload, \
         patch("main.generate_pdf") as gen_pdf:
        class _Path:
            def __str__(self) -> str:
                return "/tmp/r.pdf"
            def unlink(self, missing_ok: bool = False) -> None:
                return None

        dl.return_value = _Path()
        ingest.return_value = {"pages": [{"page_number": 1, "text": "MiFID II Art. 25"}], "language": "en"}

        class _Result:
            def model_dump(self) -> dict:
                return {
                    "executive_summary": "Summary",
                    "regulatory_references": ["MiFID II Art. 25"],
                    "required_actions": [{"description": "Submit report", "deadline": "2026-06-30", "source_page": 1}],
                }
            def model_dump_json(self, indent: int = 2) -> str:
                import json
                return json.dumps(self.model_dump(), indent=indent)

        run_reg.return_value = _Result()
        gen_pdf.return_value = __file__

        response = client.post("/analyze/regulatory", json=req, headers={"X-Internal-Api-Key": "test-key"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["result_s3_key"].endswith("/report.pdf")
    assert upload.call_count >= 2
