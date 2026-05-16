from __future__ import annotations

import hmac
import logging

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

import config
from pipeline.data_quality import run_dq_analysis
from pipeline import s3
from pipeline.extraction import run_pm_extraction
from pipeline.ingestion import ingest_document
from pipeline.red_flags import run_rm_analysis
from pipeline.summary import run_regulatory_summary

logger = logging.getLogger(__name__)

app = FastAPI(title="FinLens MCP Server", version="0.1.0")


class MCPContext(BaseModel):
    user_id: str
    allowed_contexts: list[str] = []


class MCPToolRequest(BaseModel):
    tool: str = Field(min_length=1, max_length=64)
    analysis_id: str = ""
    documents_bucket: str
    document_s3_key: str
    document_format: str
    context: MCPContext


def _verify_credentials(client_id: str | None, secret_id: str | None) -> None:
    if not client_id or not secret_id:
        raise HTTPException(status_code=401, detail="Missing MCP credentials")
    if not config.MCP_CLIENT_ID or not config.MCP_SECRET_ID:
        raise HTTPException(status_code=503, detail="MCP credentials are not configured")
    if not hmac.compare_digest(client_id, config.MCP_CLIENT_ID):
        raise HTTPException(status_code=403, detail="Invalid MCP credentials")
    if not hmac.compare_digest(secret_id, config.MCP_SECRET_ID):
        raise HTTPException(status_code=403, detail="Invalid MCP credentials")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/mcp")
async def call_tool(
    request: MCPToolRequest,
    x_mcp_client_id: str | None = Header(default=None),
    x_mcp_secret_id: str | None = Header(default=None),
) -> dict:
    _verify_credentials(x_mcp_client_id, x_mcp_secret_id)

    allowed_contexts = {c.upper() for c in request.context.allowed_contexts}
    tool_context = {
        "pm_extract": "PM",
        "rm_red_flags": "RM",
        "dq_check": "DQ",
        "regulatory_summary": "REGULATORY",
    }.get(request.tool)
    if tool_context is None:
        raise HTTPException(status_code=404, detail="Unknown or disabled tool")
    if tool_context not in allowed_contexts:
        raise HTTPException(status_code=403, detail="Tool not authorized")

    if request.documents_bucket != config.S3_DOCUMENTS_BUCKET:
        raise HTTPException(status_code=422, detail="Invalid documents bucket")
    if ".." in request.document_s3_key or request.document_s3_key.startswith("/"):
        raise HTTPException(status_code=422, detail="Invalid document key")

    try:
        local_path = s3.download_to_tempfile(request.documents_bucket, request.document_s3_key)
        try:
            ingested = ingest_document(str(local_path), request.document_format)
        finally:
            local_path.unlink(missing_ok=True)

        if request.tool == "pm_extract":
            result = run_pm_extraction(ingested).model_dump()
        elif request.tool == "rm_red_flags":
            result = run_rm_analysis(ingested).model_dump()
        elif request.tool == "dq_check":
            result = run_dq_analysis(ingested).model_dump()
        else:
            result = run_regulatory_summary(ingested).model_dump()
        return {
            "status": "ok",
            "tool": request.tool,
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("MCP tool execution failed")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {exc}")
