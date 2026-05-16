"""Tests for /analyze/agentic endpoint with multi-tool MCP execution."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


def _request() -> dict:
    return {
        "document_s3_key": "documents/abc/factsheet.pdf",
        "documents_bucket": "finlens-documents",
        "document_format": "pdf",
        "language": "auto",
        "outputs_bucket": "finlens-outputs",
        "output_s3_prefix": "analyses/abc/",
        "user_context": {"user_id": "u-1", "groups": ["PM", "RM", "DQ"]},
        "analysis_id": "abc",
        "callback_url": "",
        "agentic": {
            "goal": "Find risks and inconsistencies",
            "allowed_contexts": ["PM", "RM", "DQ", "Regulatory"],
            "requested_output": "pdf",
        },
    }


def test_analyze_agentic_executes_multiple_tools() -> None:
    client = TestClient(app)
    req = _request()

    with patch("main.s3.download_to_tempfile") as dl, \
         patch("main.ingest_document") as ingest, \
         patch("main.mask_text") as mask, \
         patch("main.call_mistral") as call_mistral, \
         patch("main._call_mcp_tool") as call_tool, \
         patch("main.s3.upload_bytes") as upload, \
         patch("main.generate_pdf") as gen_pdf:
        class _Path:
            def __str__(self) -> str:
                return "/tmp/a.pdf"
            def unlink(self, missing_ok: bool = False) -> None:
                return None

        dl.return_value = _Path()
        ingest.return_value = {"pages": [{"page_number": 1, "text": "Text"}], "language": "en"}
        mask.return_value = ("masked text", {"<PERSON_1>": "Mario Rossi"})
        call_mistral.return_value = {
            "objective": "Analyze",
            "selected_workflows": ["PM", "RM"],
            "steps": [
                {"id": "S1", "tool": "pm_extract", "reason": "Extract", "depends_on": [], "expected_output": "PMExtractionResult"},
                {"id": "S2", "tool": "rm_red_flags", "reason": "Risk checks", "depends_on": ["S1"], "expected_output": "RMResult"},
            ],
            "warnings": [],
        }

        def _tool_result(_request_obj, tool: str, _allowed: list[str]) -> dict:
            if tool == "pm_extract":
                return {"asset_allocation": {}, "transactions": []}
            if tool == "rm_red_flags":
                return {"red_flags": [{"id": "RF-1", "severity": "warning", "description": "x", "affected_fields": [], "source_pages": [1], "detail": "x"}]}
            raise AssertionError(f"unexpected tool {tool}")

        call_tool.side_effect = _tool_result
        gen_pdf.return_value = __file__

        response = client.post("/analyze/agentic", json=req, headers={"X-Internal-Api-Key": "test-key"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["summary"]["mode"] == "Agentic"
    assert "plan_s3_key" in body["summary"]
    assert "trace_s3_key" in body["summary"]
    assert len(body["summary"]["tool_artifacts"]) == 2
    assert upload.call_count >= 5


def test_analyze_agentic_rejects_unauthorized_tool() -> None:
    client = TestClient(app)
    req = _request()
    req["agentic"]["allowed_contexts"] = ["PM"]

    with patch("main.s3.download_to_tempfile") as dl, \
         patch("main.ingest_document") as ingest, \
         patch("main.mask_text") as mask, \
         patch("main.call_mistral") as call_mistral:
        class _Path:
            def __str__(self) -> str:
                return "/tmp/a.pdf"
            def unlink(self, missing_ok: bool = False) -> None:
                return None

        dl.return_value = _Path()
        ingest.return_value = {"pages": [{"page_number": 1, "text": "Text"}], "language": "en"}
        mask.return_value = ("masked text", {})
        call_mistral.return_value = {
            "objective": "Analyze",
            "selected_workflows": ["RM"],
            "steps": [{"id": "S1", "tool": "rm_red_flags", "reason": "Risk checks", "depends_on": [], "expected_output": "RMResult"}],
            "warnings": [],
        }

        response = client.post("/analyze/agentic", json=req, headers={"X-Internal-Api-Key": "test-key"})

    assert response.status_code == 422
    assert "Plan rejected" in response.json()["detail"]
