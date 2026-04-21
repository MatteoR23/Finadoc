import logging
import tempfile
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pathlib import Path

import config
from models.schemas import AnalyzeRequest, AnalyzeResponse
from pipeline import s3
from pipeline.extraction import run_pm_extraction
from pipeline.ingestion import ingest_document
from pipeline.pdf_output import generate_pdf
from pipeline.red_flags import run_rm_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FinLens AI Service", version="0.1.0")


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

    result = run_pm_extraction(ingested)

    # Upload extraction JSON (kept for debugging)
    json_key = f"{request.output_s3_prefix}extraction.json"
    result_bytes = result.model_dump_json(indent=2).encode()
    try:
        s3.upload_bytes(request.outputs_bucket, json_key, result_bytes, "application/json")
    except Exception as exc:
        logger.error("Failed to upload JSON to %s/%s: %s", request.outputs_bucket, json_key, exc)
        warnings.append(f"JSON upload failed: {exc}")

    # Generate and upload PDF report
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

    result = run_rm_analysis(ingested)

    # Upload red flags JSON (kept for debugging)
    json_key = f"{request.output_s3_prefix}red_flags.json"
    result_bytes = result.model_dump_json(indent=2).encode()
    try:
        s3.upload_bytes(request.outputs_bucket, json_key, result_bytes, "application/json")
    except Exception as exc:
        logger.error("Failed to upload JSON to %s/%s: %s", request.outputs_bucket, json_key, exc)
        warnings.append(f"JSON upload failed: {exc}")

    # Generate and upload PDF report
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


@app.post("/analyze/regulatory", response_model=AnalyzeResponse)
async def analyze_regulatory(request: AnalyzeRequest) -> AnalyzeResponse:
    """Regulatory pipeline: summary of a regulatory communication."""
    raise HTTPException(status_code=501, detail="Regulatory pipeline not implemented yet (P6)")
