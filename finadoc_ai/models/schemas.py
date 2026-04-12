from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UserContext(BaseModel):
    user_id: str
    groups: list[str]


class AnalyzeRequest(BaseModel):
    document_path: str
    document_format: str  # "pdf" | "xlsx"
    language: str = "auto"
    output_path: str
    user_context: UserContext


class AnalyzeResponse(BaseModel):
    status: str
    pdf_path: str
    summary: dict[str, Any]
    warnings: list[str]


# --- PM extraction ---

class AllocationEntry(BaseModel):
    label: str
    pct: float
    source_page: int
    confidence: ConfidenceLevel


class PerformanceData(BaseModel):
    period_return_pct: float
    benchmark_return_pct: float | None = None
    source_page: int
    confidence: ConfidenceLevel


class Transaction(BaseModel):
    type: str  # "buy" | "sell"
    instrument: str
    isin: str | None = None
    amount: float
    currency: str
    date: str
    source_page: int
    confidence: ConfidenceLevel


class ESGData(BaseModel):
    rating: str | None = None
    sustainable_exposure_pct: float | None = None
    controversies: str | None = None
    source_page: int
    confidence: ConfidenceLevel


class AssetAllocation(BaseModel):
    by_country_of_risk: list[AllocationEntry] = []
    by_rating: list[AllocationEntry] = []
    by_asset_class: list[AllocationEntry] = []


class PMExtractionResult(BaseModel):
    asset_allocation: AssetAllocation
    performance: PerformanceData | None = None
    transactions: list[Transaction] = []
    esg: ESGData | None = None


# --- RM red flags ---

class RedFlag(BaseModel):
    id: str
    severity: str  # "critical" | "warning" | "info"
    description: str
    affected_fields: list[str]
    source_pages: list[int]
    detail: str


class RMResult(BaseModel):
    red_flags: list[RedFlag] = []


# --- Regulatory summary ---

class RequiredAction(BaseModel):
    description: str
    deadline: str | None = None
    source_page: int


class RegulatoryResult(BaseModel):
    executive_summary: str
    regulatory_references: list[str] = []
    required_actions: list[RequiredAction] = []
