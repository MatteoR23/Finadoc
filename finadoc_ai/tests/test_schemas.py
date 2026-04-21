"""Tests for Pydantic schema validation (models/schemas.py).

These run without any network calls or ML models.
"""
import pytest
from pydantic import ValidationError

from models.schemas import (
    AllocationEntry,
    AnalyzeRequest,
    ConfidenceLevel,
    ESGData,
    PMExtractionResult,
    PerformanceData,
    RedFlag,
    RegulatoryResult,
    RequiredAction,
    Transaction,
    UserContext,
)


# ── ConfidenceLevel ───────────────────────────────────────────────────────────

def test_confidence_level_valid_values() -> None:
    assert ConfidenceLevel("high") == ConfidenceLevel.HIGH
    assert ConfidenceLevel("medium") == ConfidenceLevel.MEDIUM
    assert ConfidenceLevel("low") == ConfidenceLevel.LOW


def test_confidence_level_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        ConfidenceLevel("unknown")


# ── AllocationEntry ───────────────────────────────────────────────────────────

def test_allocation_entry_valid() -> None:
    entry = AllocationEntry(label="Italy", pct=45.5, source_page=3, confidence="high")
    assert entry.label == "Italy"
    assert entry.pct == 45.5
    assert entry.confidence == ConfidenceLevel.HIGH


def test_allocation_entry_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        AllocationEntry(pct=10.0, source_page=1, confidence="low")  # missing label


def test_allocation_entry_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        AllocationEntry(label="Italy", pct=10.0, source_page=1, confidence="very_high")


# ── PMExtractionResult ────────────────────────────────────────────────────────

def test_pm_extraction_result_empty_is_valid() -> None:
    result = PMExtractionResult(asset_allocation={})
    assert result.transactions == []
    assert result.performance is None
    assert result.esg is None


def test_pm_extraction_result_full() -> None:
    result = PMExtractionResult(
        asset_allocation={
            "by_country_of_risk": [
                {"label": "Italy", "pct": 60.0, "source_page": 2, "confidence": "high"}
            ],
            "by_rating": [],
            "by_asset_class": [],
        },
        performance={
            "period_return_pct": 3.2,
            "benchmark_return_pct": 2.8,
            "source_page": 5,
            "confidence": "medium",
        },
        transactions=[
            {
                "type": "buy",
                "instrument": "BTP 2030",
                "isin": "IT0005386777",
                "amount": 500_000.0,
                "currency": "EUR",
                "date": "2024-01-15",
                "source_page": 7,
                "confidence": "high",
            }
        ],
    )
    assert result.performance is not None
    assert result.performance.period_return_pct == pytest.approx(3.2)
    assert len(result.transactions) == 1
    assert result.transactions[0].isin == "IT0005386777"


# ── RedFlag ───────────────────────────────────────────────────────────────────

def test_red_flag_valid() -> None:
    flag = RedFlag(
        id="RF-001",
        severity="critical",
        description="Asset class percentages sum to 101.3%",
        affected_fields=["asset_allocation.by_asset_class"],
        source_pages=[3, 4],
        detail="Expected 100%, found 101.3%",
    )
    assert flag.severity == "critical"
    assert 3 in flag.source_pages


def test_red_flag_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        RedFlag(
            severity="warning",
            description="Some issue",
            affected_fields=[],
            source_pages=[1],
            detail="Detail",
            # missing 'id'
        )


# ── RegulatoryResult ──────────────────────────────────────────────────────────

def test_regulatory_result_defaults() -> None:
    result = RegulatoryResult(executive_summary="Summary text.")
    assert result.regulatory_references == []
    assert result.required_actions == []


def test_regulatory_result_with_actions() -> None:
    result = RegulatoryResult(
        executive_summary="ESMA requires reporting by Q2.",
        regulatory_references=["MiFID II Art. 25", "AIFMD Art. 22"],
        required_actions=[
            {"description": "Submit LEI report", "deadline": "2024-06-30", "source_page": 3}
        ],
    )
    assert len(result.regulatory_references) == 2
    assert result.required_actions[0].deadline == "2024-06-30"


# ── AnalyzeRequest ────────────────────────────────────────────────────────────

_VALID_REQUEST = {
    "document_s3_key": "uploads/abc/doc.pdf",
    "documents_bucket": "finadoc-documents",
    "document_format": "pdf",
    "outputs_bucket": "finadoc-outputs",
    "output_s3_prefix": "analyses/abc/",
    "user_context": {"user_id": "user-123", "groups": ["PM"]},
}


def test_analyze_request_valid() -> None:
    req = AnalyzeRequest(**_VALID_REQUEST)
    assert req.language == "auto"  # default
    assert req.user_context.groups == ["PM"]


def test_analyze_request_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            document_format="pdf",
            outputs_bucket="finadoc-outputs",
            output_s3_prefix="analyses/x/",
            user_context={"user_id": "u1", "groups": []},
            # missing document_s3_key and documents_bucket
        )


# ── Endpoints: rm and regulatory still return 501; pm is implemented (P4) ────

def test_analyze_rm_returns_501(client) -> None:
    response = client.post("/analyze/rm", json=_VALID_REQUEST, headers={"X-Internal-Api-Key": "test-key"})
    assert response.status_code == 501


def test_analyze_regulatory_returns_501(client) -> None:
    response = client.post("/analyze/regulatory", json=_VALID_REQUEST, headers={"X-Internal-Api-Key": "test-key"})
    assert response.status_code == 501
