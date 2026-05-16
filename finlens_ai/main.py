import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import json

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import config
from models.schemas import AnalyzeRequest, AnalyzeResponse
from pipeline import s3
from pipeline.data_quality import run_dq_analysis
from pipeline.extraction import run_pm_extraction
from pipeline.ingestion import ingest_document
from pipeline.llm import call_mistral, load_prompt
from pipeline.masking import mask_text
from pipeline.pdf_output import generate_pdf
from pipeline.red_flags import run_rm_analysis
from pipeline.summary import run_regulatory_summary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FinLens AI Service", version="0.1.0")

ALLOWED_AGENTIC_TOOLS = {
    "pm_extract",
    "rm_red_flags",
    "dq_check",
    "regulatory_summary",
}
TOOL_TO_CONTEXT = {
    "pm_extract": "PM",
    "rm_red_flags": "RM",
    "dq_check": "DQ",
    "regulatory_summary": "Regulatory",
}


async def _report_progress(callback_url: str, step: str) -> None:
    if not callback_url:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                callback_url,
                json={"step": step},
                headers={"X-Internal-Api-Key": config.INTERNAL_API_KEY},
                timeout=5,
            )
    except Exception as exc:
        logger.warning("Progress callback failed: %s", exc)


def _build_agentic_plan(masked_text: str, allowed_contexts: list[str], goal: str | None) -> dict:
    prompt = load_prompt("agentic/planner_v1.txt")
    contexts = ", ".join(allowed_contexts) if allowed_contexts else "PM"
    user_objective = goal or "Run the best available analysis workflow."
    enabled_tools = [tool for tool, ctx in TOOL_TO_CONTEXT.items() if ctx in allowed_contexts]
    if not enabled_tools:
        enabled_tools = ["pm_extract"]
    user_text = (
        f"Allowed contexts: {contexts}\n"
        f"User goal: {user_objective}\n"
        f"Enabled tools: {', '.join(enabled_tools)}\n\n"
        f"Document text:\n{masked_text}"
    )
    raw = call_mistral(config.MISTRAL_MODEL_SMALL, prompt, user_text)
    if not isinstance(raw, dict):
        raise ValueError("Planner returned non-object JSON")
    return raw


def _validate_agentic_plan(plan: dict, allowed_contexts: list[str]) -> dict:
    steps = plan.get("steps", [])
    if not isinstance(steps, list) or len(steps) == 0:
        raise ValueError("Invalid plan: steps must be a non-empty list")
    if len(steps) > 6:
        raise ValueError("Invalid plan: too many steps")

    allowed_ctx = set(allowed_contexts)
    ids = set()
    for step in steps:
        step_id = str(step.get("id", "")).strip()
        if not step_id:
            raise ValueError("Invalid plan: step id is required")
        if step_id in ids:
            raise ValueError(f"Invalid plan: duplicate step id {step_id}")
        ids.add(step_id)

        tool = str(step.get("tool", "")).strip()
        if tool not in ALLOWED_AGENTIC_TOOLS:
            raise ValueError(f"Plan uses unknown or disabled tool: {tool}")
        deps = step.get("depends_on", [])
        if not isinstance(deps, list):
            raise ValueError("Invalid plan: depends_on must be a list")
        for dep in deps:
            if dep == step_id:
                raise ValueError("Invalid plan: self dependency not allowed")

        required_context = TOOL_TO_CONTEXT[tool]
        if required_context not in allowed_ctx:
            raise ValueError(f"Plan uses unauthorized tool for context {required_context}: {tool}")

    for step in steps:
        for dep in step.get("depends_on", []):
            if dep not in ids:
                raise ValueError(f"Invalid plan: unknown dependency {dep}")

    normalized = {
        "objective": str(plan.get("objective", "")).strip() or "Agentic document analysis",
        "selected_workflows": sorted({TOOL_TO_CONTEXT[str(s.get("tool", ""))] for s in steps if str(s.get("tool", "")) in TOOL_TO_CONTEXT}),
        "steps": [{
            "id": str(step.get("id", "")).strip(),
            "tool": str(step.get("tool", "")).strip(),
            "reason": str(step.get("reason", "Tool selected")).strip() or "Tool selected",
            "depends_on": step.get("depends_on", []),
            "expected_output": str(step.get("expected_output", "object")).strip() or "object",
        } for step in steps],
        "warnings": plan.get("warnings", []) if isinstance(plan.get("warnings"), list) else [],
    }
    return normalized


async def _call_mcp_tool(request: AnalyzeRequest, tool: str, allowed_contexts: list[str]) -> dict:
    if not config.MCP_CLIENT_ID or not config.MCP_SECRET_ID:
        raise RuntimeError("MCP credentials are not configured")

    payload = {
        "tool": tool,
        "analysis_id": request.analysis_id,
        "documents_bucket": request.documents_bucket,
        "document_s3_key": request.document_s3_key,
        "document_format": request.document_format,
        "context": {
            "user_id": request.user_context.user_id,
            "allowed_contexts": allowed_contexts,
        },
    }
    headers = {
        "X-MCP-Client-Id": config.MCP_CLIENT_ID,
        "X-MCP-Secret-Id": config.MCP_SECRET_ID,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(f"{config.MCP_BASE_URL}/mcp", json=payload, headers=headers)
        if response.status_code in (401, 403):
            raise PermissionError("MCP authentication failed")
        if response.status_code >= 400:
            raise RuntimeError(f"MCP error: {response.status_code} {response.text}")
        data = response.json()
        result = data.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("MCP returned invalid result payload")
        return result


@app.middleware("http")
async def verify_internal_api_key(request: Request, call_next):
    if request.method == "GET" and request.url.path == "/health":
        return await call_next(request)
    key = request.headers.get("X-Internal-Api-Key")
    if not key or key != config.INTERNAL_API_KEY:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    return await call_next(request)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze/pm", response_model=AnalyzeResponse)
async def analyze_pm(request: AnalyzeRequest) -> AnalyzeResponse:
    """PM pipeline: structured extraction from a fund factsheet."""
    warnings: list[str] = []

    await _report_progress(request.callback_url, "ingesting")
    try:
        local_path = s3.download_to_tempfile(request.documents_bucket, request.document_s3_key)
    except Exception as exc:
        logger.error("Failed to download %s/%s: %s", request.documents_bucket, request.document_s3_key, exc)
        raise HTTPException(status_code=422, detail=f"Could not retrieve document from storage: {exc}")

    try:
        ingested = ingest_document(str(local_path), request.document_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        local_path.unlink(missing_ok=True)

    await _report_progress(request.callback_url, "analyzing")
    result = run_pm_extraction(ingested)

    # Upload extraction JSON (kept for debugging)
    json_key = f"{request.output_s3_prefix}extraction.json"
    result_bytes = result.model_dump_json(indent=2).encode()
    try:
        s3.upload_bytes(request.outputs_bucket, json_key, result_bytes, "application/json")
    except Exception as exc:
        logger.error("Failed to upload JSON to %s/%s: %s", request.outputs_bucket, json_key, exc)
        warnings.append(f"JSON upload failed: {exc}")

    await _report_progress(request.callback_url, "generating")
    pdf_key = f"{request.output_s3_prefix}report.pdf"
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_data = {
            "pipeline": "pm",
            "doc_name": Path(request.document_s3_key).name,
            "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "user_id": request.user_context.user_id,
            "language": ingested.get("language", "en"),
            "extraction": result.model_dump(),
        }
        pdf_local = generate_pdf(pdf_data, tmp_dir)
        with open(pdf_local, "rb") as f:
            pdf_bytes = f.read()

    try:
        s3.upload_bytes(request.outputs_bucket, pdf_key, pdf_bytes, "application/pdf")
    except Exception as exc:
        logger.error("Failed to upload PDF to %s/%s: %s", request.outputs_bucket, pdf_key, exc)
        warnings.append(f"PDF upload failed: {exc}")

    return AnalyzeResponse(
        status="ok",
        result_s3_key=pdf_key,
        summary=result.model_dump(),
        warnings=warnings,
    )


@app.post("/analyze/rm", response_model=AnalyzeResponse)
async def analyze_rm(request: AnalyzeRequest) -> AnalyzeResponse:
    """RM pipeline: red flag detection in a financial report."""
    warnings: list[str] = []

    await _report_progress(request.callback_url, "ingesting")
    try:
        local_path = s3.download_to_tempfile(request.documents_bucket, request.document_s3_key)
    except Exception as exc:
        logger.error("Failed to download %s/%s: %s", request.documents_bucket, request.document_s3_key, exc)
        raise HTTPException(status_code=422, detail=f"Could not retrieve document from storage: {exc}")

    try:
        ingested = ingest_document(str(local_path), request.document_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        local_path.unlink(missing_ok=True)

    await _report_progress(request.callback_url, "analyzing")
    result = run_rm_analysis(ingested)

    # Upload red flags JSON (kept for debugging)
    json_key = f"{request.output_s3_prefix}red_flags.json"
    result_bytes = result.model_dump_json(indent=2).encode()
    try:
        s3.upload_bytes(request.outputs_bucket, json_key, result_bytes, "application/json")
    except Exception as exc:
        logger.error("Failed to upload JSON to %s/%s: %s", request.outputs_bucket, json_key, exc)
        warnings.append(f"JSON upload failed: {exc}")

    await _report_progress(request.callback_url, "generating")
    pdf_key = f"{request.output_s3_prefix}report.pdf"
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_data = {
            "pipeline": "rm",
            "doc_name": Path(request.document_s3_key).name,
            "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "user_id": request.user_context.user_id,
            "language": ingested.get("language", "en"),
            "red_flags": result.model_dump()["red_flags"],
        }
        pdf_local = generate_pdf(pdf_data, tmp_dir)
        with open(pdf_local, "rb") as f:
            pdf_bytes = f.read()

    try:
        s3.upload_bytes(request.outputs_bucket, pdf_key, pdf_bytes, "application/pdf")
    except Exception as exc:
        logger.error("Failed to upload PDF to %s/%s: %s", request.outputs_bucket, pdf_key, exc)
        warnings.append(f"PDF upload failed: {exc}")

    return AnalyzeResponse(
        status="ok",
        result_s3_key=pdf_key,
        summary=result.model_dump(),
        warnings=warnings,
    )


@app.post("/analyze/dq", response_model=AnalyzeResponse)
async def analyze_dq(request: AnalyzeRequest) -> AnalyzeResponse:
    """DQ pipeline: data quality checks on a financial document."""
    warnings: list[str] = []

    await _report_progress(request.callback_url, "ingesting")
    try:
        local_path = s3.download_to_tempfile(request.documents_bucket, request.document_s3_key)
    except Exception as exc:
        logger.error("Failed to download %s/%s: %s", request.documents_bucket, request.document_s3_key, exc)
        raise HTTPException(status_code=422, detail=f"Could not retrieve document from storage: {exc}")

    try:
        ingested = ingest_document(str(local_path), request.document_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        local_path.unlink(missing_ok=True)

    await _report_progress(request.callback_url, "analyzing")
    result = run_dq_analysis(ingested)

    json_key = f"{request.output_s3_prefix}data_quality.json"
    result_bytes = result.model_dump_json(indent=2).encode()
    try:
        s3.upload_bytes(request.outputs_bucket, json_key, result_bytes, "application/json")
    except Exception as exc:
        logger.error("Failed to upload JSON to %s/%s: %s", request.outputs_bucket, json_key, exc)
        warnings.append(f"JSON upload failed: {exc}")

    await _report_progress(request.callback_url, "generating")
    pdf_key = f"{request.output_s3_prefix}report.pdf"
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_data = {
            "pipeline": "dq",
            "doc_name": Path(request.document_s3_key).name,
            "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "user_id": request.user_context.user_id,
            "language": ingested.get("language", "en"),
            "data_quality_flags": result.model_dump()["data_quality_flags"],
        }
        pdf_local = generate_pdf(pdf_data, tmp_dir)
        with open(pdf_local, "rb") as f:
            pdf_bytes = f.read()

    try:
        s3.upload_bytes(request.outputs_bucket, pdf_key, pdf_bytes, "application/pdf")
    except Exception as exc:
        logger.error("Failed to upload PDF to %s/%s: %s", request.outputs_bucket, pdf_key, exc)
        warnings.append(f"PDF upload failed: {exc}")

    return AnalyzeResponse(
        status="ok",
        result_s3_key=pdf_key,
        summary=result.model_dump(),
        warnings=warnings,
    )


@app.post("/analyze/regulatory", response_model=AnalyzeResponse)
async def analyze_regulatory(request: AnalyzeRequest) -> AnalyzeResponse:
    """Regulatory pipeline: summary of a regulatory communication."""
    warnings: list[str] = []

    await _report_progress(request.callback_url, "ingesting")
    try:
        local_path = s3.download_to_tempfile(request.documents_bucket, request.document_s3_key)
    except Exception as exc:
        logger.error("Failed to download %s/%s: %s", request.documents_bucket, request.document_s3_key, exc)
        raise HTTPException(status_code=422, detail=f"Could not retrieve document from storage: {exc}")

    try:
        ingested = ingest_document(str(local_path), request.document_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        local_path.unlink(missing_ok=True)

    await _report_progress(request.callback_url, "analyzing")
    result = run_regulatory_summary(ingested)

    json_key = f"{request.output_s3_prefix}regulatory_summary.json"
    result_bytes = result.model_dump_json(indent=2).encode()
    try:
        s3.upload_bytes(request.outputs_bucket, json_key, result_bytes, "application/json")
    except Exception as exc:
        logger.error("Failed to upload JSON to %s/%s: %s", request.outputs_bucket, json_key, exc)
        warnings.append(f"JSON upload failed: {exc}")

    await _report_progress(request.callback_url, "generating")
    pdf_key = f"{request.output_s3_prefix}report.pdf"
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_data = {
            "pipeline": "regulatory",
            "doc_name": Path(request.document_s3_key).name,
            "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "user_id": request.user_context.user_id,
            "language": ingested.get("language", "en"),
            "regulatory": result.model_dump(),
        }
        pdf_local = generate_pdf(pdf_data, tmp_dir)
        with open(pdf_local, "rb") as f:
            pdf_bytes = f.read()
    try:
        s3.upload_bytes(request.outputs_bucket, pdf_key, pdf_bytes, "application/pdf")
    except Exception as exc:
        logger.error("Failed to upload PDF to %s/%s: %s", request.outputs_bucket, pdf_key, exc)
        warnings.append(f"PDF upload failed: {exc}")

    return AnalyzeResponse(
        status="ok",
        result_s3_key=pdf_key,
        summary=result.model_dump(),
        warnings=warnings,
    )


@app.post("/analyze/agentic", response_model=AnalyzeResponse)
async def analyze_agentic(request: AnalyzeRequest) -> AnalyzeResponse:
    """Bounded agentic pipeline: planner + policy gate + MCP tool execution."""
    warnings: list[str] = []
    allowed_contexts = request.agentic.allowed_contexts if request.agentic else request.user_context.groups
    allowed_contexts = [c for c in allowed_contexts if c in {"PM", "RM", "DQ", "Regulatory"}]
    if not allowed_contexts:
        allowed_contexts = ["PM"]

    await _report_progress(request.callback_url, "ingesting")
    try:
        local_path = s3.download_to_tempfile(request.documents_bucket, request.document_s3_key)
    except Exception as exc:
        logger.error("Failed to download %s/%s: %s", request.documents_bucket, request.document_s3_key, exc)
        raise HTTPException(status_code=422, detail=f"Could not retrieve document from storage: {exc}")

    try:
        ingested = ingest_document(str(local_path), request.document_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        local_path.unlink(missing_ok=True)

    full_text = "\n\n".join(
        f"[Page {p['page_number']}]\n{p['text']}"
        for p in ingested["pages"]
    )
    await _report_progress(request.callback_url, "masking")
    masked_text, _mapping = mask_text(full_text)

    await _report_progress(request.callback_url, "planning")
    try:
        raw_plan = _build_agentic_plan(masked_text, allowed_contexts, request.agentic.goal if request.agentic else None)
        plan = _validate_agentic_plan(raw_plan, allowed_contexts)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Plan rejected: {exc}")

    plan_key = f"{request.output_s3_prefix}plan.json"
    s3.upload_bytes(
        request.outputs_bucket,
        plan_key,
        json.dumps(plan, indent=2).encode(),
        "application/json",
    )

    await _report_progress(request.callback_url, "validating_plan")
    step_results: dict[str, dict] = {}
    step_artifacts: list[str] = []
    ordered_steps = plan["steps"]
    completed_ids: set[str] = set()

    while len(completed_ids) < len(ordered_steps):
        progress = False
        for step in ordered_steps:
            step_id = step["id"]
            if step_id in completed_ids:
                continue
            deps = step.get("depends_on", [])
            if any(dep not in completed_ids for dep in deps):
                continue

            tool = step["tool"]
            await _report_progress(request.callback_url, f"executing:{tool}")
            try:
                tool_result = await _call_mcp_tool(request, tool, allowed_contexts)
            except PermissionError as exc:
                raise HTTPException(status_code=503, detail=str(exc))
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"MCP execution failed for {tool}: {exc}")

            artifact_name = {
                "pm_extract": "pm_extraction.json",
                "rm_red_flags": "red_flags.json",
                "dq_check": "data_quality.json",
                "regulatory_summary": "regulatory_summary.json",
            }[tool]
            artifact_key = f"{request.output_s3_prefix}{artifact_name}"
            s3.upload_bytes(
                request.outputs_bucket,
                artifact_key,
                json.dumps(tool_result, indent=2).encode(),
                "application/json",
            )
            step_results[tool] = tool_result
            step_artifacts.append(artifact_key)
            completed_ids.add(step_id)
            progress = True
        if not progress:
            raise HTTPException(status_code=422, detail="Plan rejected: dependency cycle detected")

    trace = {
        "analysis_id": request.analysis_id,
        "mode": "Agentic",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "document": {
            "key": request.document_s3_key,
            "format": request.document_format,
            "page_count": len(ingested["pages"]),
            "language": ingested.get("language", "en"),
        },
        "plan_s3_key": plan_key,
        "steps": [
            {
                "id": step["id"],
                "tool": step["tool"],
                "status": "completed",
                "artifact_s3_key": {
                    "pm_extract": f"{request.output_s3_prefix}pm_extraction.json",
                    "rm_red_flags": f"{request.output_s3_prefix}red_flags.json",
                    "dq_check": f"{request.output_s3_prefix}data_quality.json",
                    "regulatory_summary": f"{request.output_s3_prefix}regulatory_summary.json",
                }[step["tool"]],
            }
            for step in ordered_steps
        ],
        "warnings": warnings,
    }
    trace_key = f"{request.output_s3_prefix}trace.json"
    s3.upload_bytes(
        request.outputs_bucket,
        trace_key,
        json.dumps(trace, indent=2).encode(),
        "application/json",
    )

    await _report_progress(request.callback_url, "generating")
    pdf_key = f"{request.output_s3_prefix}report.pdf"
    selected = [step["tool"] for step in ordered_steps]
    primary = selected[0]
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_data = {
            "doc_name": Path(request.document_s3_key).name,
            "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "user_id": request.user_context.user_id,
            "language": ingested.get("language", "en"),
        }
        if primary == "pm_extract":
            pdf_data["pipeline"] = "pm"
            pdf_data["extraction"] = step_results.get("pm_extract", {})
        elif primary == "rm_red_flags":
            pdf_data["pipeline"] = "rm"
            pdf_data["red_flags"] = step_results.get("rm_red_flags", {}).get("red_flags", [])
        elif primary == "dq_check":
            pdf_data["pipeline"] = "dq"
            pdf_data["data_quality_flags"] = step_results.get("dq_check", {}).get("data_quality_flags", [])
        else:
            pdf_data["pipeline"] = "regulatory"
            pdf_data["regulatory"] = step_results.get("regulatory_summary", {})
        pdf_local = generate_pdf(pdf_data, tmp_dir)
        with open(pdf_local, "rb") as f:
            pdf_bytes = f.read()
    s3.upload_bytes(request.outputs_bucket, pdf_key, pdf_bytes, "application/pdf")

    result_key = f"{request.output_s3_prefix}agentic_result.json"
    result_payload = {
        "mode": "Agentic",
        "selected_workflows": plan.get("selected_workflows", []),
        "plan_s3_key": plan_key,
        "trace_s3_key": trace_key,
        "tool_artifacts": step_artifacts,
        "report_s3_key": pdf_key,
    }
    s3.upload_bytes(
        request.outputs_bucket,
        result_key,
        json.dumps(result_payload, indent=2).encode(),
        "application/json",
    )

    return AnalyzeResponse(
        status="ok",
        result_s3_key=pdf_key,
        report_s3_key=pdf_key,
        summary=result_payload,
        warnings=warnings,
    )
