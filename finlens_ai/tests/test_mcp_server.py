"""Tests for internal MCP server auth and tool routing."""
from unittest.mock import patch

from fastapi.testclient import TestClient

import config
from mcp_server import app


def _payload(tool: str = "pm_extract") -> dict:
    return {
        "tool": tool,
        "analysis_id": "a-1",
        "documents_bucket": "finlens-documents",
        "document_s3_key": "documents/doc-1/report.pdf",
        "document_format": "pdf",
        "context": {"user_id": "u-1", "allowed_contexts": ["PM", "RM", "DQ", "Regulatory"]},
    }


def test_mcp_missing_credentials_returns_401(monkeypatch) -> None:
    monkeypatch.setattr(config, "MCP_CLIENT_ID", "client-a")
    monkeypatch.setattr(config, "MCP_SECRET_ID", "secret-a")
    client = TestClient(app)

    response = client.post("/mcp", json=_payload())
    assert response.status_code == 401


def test_mcp_invalid_credentials_returns_403(monkeypatch) -> None:
    monkeypatch.setattr(config, "MCP_CLIENT_ID", "client-a")
    monkeypatch.setattr(config, "MCP_SECRET_ID", "secret-a")
    client = TestClient(app)

    response = client.post(
        "/mcp",
        json=_payload(),
        headers={"X-MCP-Client-Id": "client-a", "X-MCP-Secret-Id": "wrong"},
    )
    assert response.status_code == 403


def test_mcp_unknown_tool_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(config, "MCP_CLIENT_ID", "client-a")
    monkeypatch.setattr(config, "MCP_SECRET_ID", "secret-a")
    client = TestClient(app)

    response = client.post(
        "/mcp",
        json=_payload("unknown_tool"),
        headers={"X-MCP-Client-Id": "client-a", "X-MCP-Secret-Id": "secret-a"},
    )
    assert response.status_code == 404


def test_mcp_pm_extract_success(monkeypatch) -> None:
    monkeypatch.setattr(config, "MCP_CLIENT_ID", "client-a")
    monkeypatch.setattr(config, "MCP_SECRET_ID", "secret-a")
    client = TestClient(app)

    with patch("mcp_server.s3.download_to_tempfile") as dl, \
         patch("mcp_server.ingest_document") as ingest, \
         patch("mcp_server.run_pm_extraction") as run_pm:
        class _Path:
            def __str__(self) -> str:
                return "/tmp/f.pdf"
            def unlink(self, missing_ok: bool = False) -> None:
                return None

        dl.return_value = _Path()
        ingest.return_value = {"pages": [{"page_number": 1, "text": "x"}], "language": "en"}

        class _Result:
            def model_dump(self) -> dict:
                return {"asset_allocation": {}, "transactions": []}

        run_pm.return_value = _Result()
        response = client.post(
            "/mcp",
            json=_payload("pm_extract"),
            headers={"X-MCP-Client-Id": "client-a", "X-MCP-Secret-Id": "secret-a"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["tool"] == "pm_extract"
    assert isinstance(body["result"], dict)
