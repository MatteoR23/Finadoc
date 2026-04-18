import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import config
from models.schemas import AnalyzeRequest, AnalyzeResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Finadoc AI Service", version="0.1.0")


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
    raise HTTPException(status_code=501, detail="PM pipeline not implemented yet (P4)")


@app.post("/analyze/rm", response_model=AnalyzeResponse)
async def analyze_rm(request: AnalyzeRequest) -> AnalyzeResponse:
    """RM pipeline: red flag detection in a financial report."""
    raise HTTPException(status_code=501, detail="RM pipeline not implemented yet (P6)")


@app.post("/analyze/regulatory", response_model=AnalyzeResponse)
async def analyze_regulatory(request: AnalyzeRequest) -> AnalyzeResponse:
    """Regulatory pipeline: summary of a regulatory communication."""
    raise HTTPException(status_code=501, detail="Regulatory pipeline not implemented yet (P7)")
