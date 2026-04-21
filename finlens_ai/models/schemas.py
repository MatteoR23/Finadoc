from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator

import config


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UserContext(BaseModel):
    user_id: str
    groups: list[str]


class AnalyzeRequest(BaseModel):
    document_s3_key: str
    documents_bucket: str
    document_format: str  # "pdf" | "xlsx"
    language: str = "auto"
    outputs_bucket: str
    output_s3_prefix: str
    user_context: UserContext

    @field_validator("document_s3_key")
    @classmethod
    def validate_document_s3_key(cls, v: str) -> str:
        if ".." in v or v.startswith("/"):
            raise ValueError("document_s3_key must not contain path traversal sequences")
        if not v.startswith("documents/"):
            raise ValueError("document_s3_key must be within the documents/ prefix")
        return v

    @field_validator("output_s3_prefix")
    @classmethod
    def validate_output_s3_prefix(cls, v: str) -> str:
        if ".." in v or v.startswith("/"):
            raise ValueError("output_s3_prefix must not contain path traversal sequences")
        if not v.startswith("analyses/"):
            raise ValueError("output_s3_prefix must be within the analyses/ prefix")
        return v

    @field_validator("documents_bucket")
    @classmethod
    def validate_documents_bucket(cls, v: str) -> str:
        if v != config.S3_DOCUMENTS_BUCKET:
            raise ValueError(f"documents_bucket must be {config.S3_DOCUMENTS_BUCKET!r}")
        return v

    @field_validator("outputs_bucket")
    @classmethod
    def validate_outputs_bucket(cls, v: str) -> str:
        if v != config.S3_OUTPUTS_BUCKET:
            raise ValueError(f"outputs_bucket must be {config.S3_OUTPUTS_BUCKET!r}")
        return v


class AnalyzeResponse(BaseModel):
    status: str
    result_s3_key: str
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
    source_page: int | None = None
    confidence: ConfidenceLevel


class AssetAllocation(BaseModel):
    by_country_of_risk: list[AllocationEntry] = []
    by_rating: list[AllocationEntry] = []
    by_asset_class: list[AllocationEntry] = []


class PMExtractionResult(BaseModel):
    asset_allocation: AssetAllocation = AssetAllocation()
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
