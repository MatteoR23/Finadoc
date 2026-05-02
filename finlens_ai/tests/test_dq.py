"""Tests for the DQ (Data Quality) pipeline.

Covers: DQFlag/DQResult schema validation, run_dq_analysis (mocked Mistral),
prompt loading, and PDF output for the DQ pipeline.
"""
import tempfile
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from models.schemas import DQFlag, DQResult
from pipeline.llm import load_prompt
from pipeline.pdf_output import generate_pdf


# ── DQFlag schema ─────────────────────────────────────────────────────────────

def test_dq_flag_valid() -> None:
    flag = DQFlag(
        id="DQ-001",
        severity="critical",
        description="Asset allocation percentages sum to 101.3%",
        affected_fields=["asset_allocation.by_asset_class"],
        source_pages=[3],
        detail="Expected 100.0%, found 101.3%. Equity=50%, Bond=40%, Fund=11.3%.",
    )
    assert flag.id == "DQ-001"
    assert flag.severity == "critical"
    assert 3 in flag.source_pages


def test_dq_flag_missing_id_raises() -> None:
    with pytest.raises(ValidationError):
        DQFlag(
            severity="warning",
            description="NAV mismatch",
            affected_fields=["nav"],
            source_pages=[1],
            detail="Detail text",
            # missing 'id'
        )


def test_dq_flag_all_severity_values() -> None:
    for sev in ("critical", "warning", "info"):
        flag = DQFlag(id="DQ-X", severity=sev, description="x", affected_fields=[], source_pages=[], detail="x")
        assert flag.severity == sev


# ── DQResult schema ───────────────────────────────────────────────────────────

def test_dq_result_empty_is_valid() -> None:
    result = DQResult()
    assert result.data_quality_flags == []


def test_dq_result_with_flags() -> None:
    result = DQResult(data_quality_flags=[
        {
            "id": "DQ-001",
            "severity": "critical",
            "description": "Percentages sum to 101.3%",
            "affected_fields": ["asset_allocation.by_asset_class"],
            "source_pages": [3],
            "detail": "Sum is 101.3%, expected 100.0%.",
        },
        {
            "id": "DQ-002",
            "severity": "warning",
            "description": "NAV figure inconsistency",
            "affected_fields": ["nav"],
            "source_pages": [1, 5],
            "detail": "Page 1 states NAV=100.5M, page 5 states NAV=100.2M.",
        },
    ])
    assert len(result.data_quality_flags) == 2
    assert result.data_quality_flags[0].id == "DQ-001"
    assert result.data_quality_flags[1].severity == "warning"


def test_dq_result_from_model_validate() -> None:
    raw = {
        "data_quality_flags": [
            {
                "id": "DQ-001",
                "severity": "info",
                "description": "Minor rounding",
                "affected_fields": [],
                "source_pages": [2],
                "detail": "0.05% rounding difference.",
            }
        ]
    }
    result = DQResult.model_validate(raw)
    assert len(result.data_quality_flags) == 1


def test_dq_result_empty_flags_from_raw() -> None:
    result = DQResult.model_validate({"data_quality_flags": []})
    assert result.data_quality_flags == []


# ── Prompt loading ────────────────────────────────────────────────────────────

def test_dq_prompt_loads_and_contains_marker() -> None:
    prompt = load_prompt("DQ/data_quality_v1.txt")
    assert "{document_text}" in prompt
    assert "data_quality_flags" in prompt


def test_dq_prompt_contains_key_checks() -> None:
    prompt = load_prompt("DQ/data_quality_v1.txt")
    assert "100%" in prompt
    assert "DQ-" in prompt  # id prefix example in JSON structure


# ── run_dq_analysis (Mistral mocked) ─────────────────────────────────────────

_SAMPLE_INGESTED = {
    "pages": [
        {"page_number": 1, "text": "Fund allocation: Equity 50%, Bond 40%, Fund 11.3%. Total: 101.3%."},
        {"page_number": 2, "text": "NAV as of 31 Dec: 100.5M EUR."},
        {"page_number": 5, "text": "NAV restated: 100.2M EUR."},
    ],
    "language": "en",
}

_CANNED_RESPONSE = {
    "data_quality_flags": [
        {
            "id": "DQ-001",
            "severity": "critical",
            "description": "Asset class allocation sums to 101.3%",
            "affected_fields": ["asset_allocation.by_asset_class"],
            "source_pages": [1],
            "detail": "Equity 50% + Bond 40% + Fund 11.3% = 101.3%, expected 100%.",
        }
    ]
}


def test_run_dq_analysis_returns_dq_result() -> None:
    with patch("pipeline.data_quality.call_mistral", return_value=_CANNED_RESPONSE):
        from pipeline.data_quality import run_dq_analysis
        result = run_dq_analysis(_SAMPLE_INGESTED)

    assert isinstance(result, DQResult)
    assert len(result.data_quality_flags) == 1
    assert result.data_quality_flags[0].severity == "critical"


def test_run_dq_analysis_empty_response_returns_empty_result() -> None:
    with patch("pipeline.data_quality.call_mistral", return_value={"data_quality_flags": []}):
        from pipeline.data_quality import run_dq_analysis
        result = run_dq_analysis(_SAMPLE_INGESTED)

    assert result.data_quality_flags == []


def test_run_dq_analysis_uses_small_model() -> None:
    """DQ uses mistral-small-latest, not large."""
    calls: list[str] = []

    def fake_mistral(*args: str) -> dict:
        calls.append(args[0])
        return _CANNED_RESPONSE

    with patch("pipeline.data_quality.call_mistral", side_effect=fake_mistral):
        from pipeline.data_quality import run_dq_analysis
        run_dq_analysis(_SAMPLE_INGESTED)

    assert calls == ["mistral-small-latest"]


def test_run_dq_analysis_italian_doc_uses_italian_directive() -> None:
    """Language directive is injected into the system prompt."""
    prompts_seen: list[str] = []

    def fake_mistral(*args: str) -> dict:
        prompts_seen.append(args[1])
        return _CANNED_RESPONSE

    ingested_it = {**_SAMPLE_INGESTED, "language": "it"}
    with patch("pipeline.data_quality.call_mistral", side_effect=fake_mistral):
        from pipeline.data_quality import run_dq_analysis
        run_dq_analysis(ingested_it)

    assert "Italian" in prompts_seen[0]


# ── PDF output — DQ pipeline ──────────────────────────────────────────────────

def _make_pdf_data(flags: list[dict], lang: str = "en") -> dict:
    return {
        "pipeline": "dq",
        "doc_name": "test_report.pdf",
        "analysis_date": "2026-04-22",
        "user_id": "user-test",
        "language": lang,
        "data_quality_flags": flags,
    }


def test_generate_pdf_dq_no_flags() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_pdf(_make_pdf_data([]), tmp)
    assert path.endswith("report.pdf")


def test_generate_pdf_dq_with_flags_produces_file() -> None:
    import os
    flags = [
        {
            "id": "DQ-001",
            "severity": "critical",
            "description": "Percentages sum to 101.3%",
            "affected_fields": ["asset_allocation.by_asset_class"],
            "source_pages": [3],
            "detail": "Sum is 101.3%.",
        },
        {
            "id": "DQ-002",
            "severity": "warning",
            "description": "NAV inconsistency",
            "affected_fields": ["nav"],
            "source_pages": [1, 5],
            "detail": "NAV differs between pages.",
        },
        {
            "id": "DQ-003",
            "severity": "info",
            "description": "Minor rounding",
            "affected_fields": [],
            "source_pages": [2],
            "detail": "0.05% rounding.",
        },
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_pdf(_make_pdf_data(flags), tmp)
        assert os.path.getsize(path) > 1000  # non-empty PDF


def test_generate_pdf_dq_italian() -> None:
    import os
    flags = [{
        "id": "DQ-001",
        "severity": "warning",
        "description": "Percentuali non sommano a 100%",
        "affected_fields": ["allocazione"],
        "source_pages": [2],
        "detail": "Somma trovata: 99.5%.",
    }]
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_pdf(_make_pdf_data(flags, lang="it"), tmp)
        assert os.path.exists(path)


def test_generate_pdf_dq_flags_sorted_by_severity() -> None:
    """Flags should be sorted critical → warning → info in the PDF (no crash)."""
    import os
    flags = [
        {"id": "DQ-A", "severity": "info", "description": "Info", "affected_fields": [], "source_pages": [], "detail": "d"},
        {"id": "DQ-B", "severity": "critical", "description": "Critical", "affected_fields": [], "source_pages": [1], "detail": "d"},
        {"id": "DQ-C", "severity": "warning", "description": "Warning", "affected_fields": [], "source_pages": [2], "detail": "d"},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_pdf(_make_pdf_data(flags), tmp)
        assert os.path.exists(path)
