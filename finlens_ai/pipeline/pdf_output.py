"""PDF report generation via ReportLab platypus.

Report structure:
  - Header (document name, analysis date, pipeline context, user)
  - PM: asset allocation tables, performance, transactions, ESG
  - RM: red flags sorted critical → warning → info
  - Disclaimer
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Colour constants
# ---------------------------------------------------------------------------

_CONFIDENCE_COLORS: dict[str, colors.HexColor] = {
    "high":   colors.HexColor("#28a745"),
    "medium": colors.HexColor("#ffc107"),
    "low":    colors.HexColor("#dc3545"),
}

_SEVERITY_COLORS: dict[str, colors.HexColor] = {
    "critical": colors.HexColor("#dc3545"),
    "warning":  colors.HexColor("#ffc107"),
    "info":     colors.HexColor("#17a2b8"),
}

_SEVERITY_ORDER: dict[str, int] = {"critical": 0, "warning": 1, "info": 2}

_LOW_CONF_BG = colors.HexColor("#fff3cd")
_HEADER_BG   = colors.HexColor("#343a40")
_BORDER      = colors.HexColor("#dee2e6")

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

_I18N: dict[str, dict[str, str]] = {
    "en": {
        "analysis_date": "Analysis date:",
        "pipeline": "Pipeline:",
        "user": "User:",
        "allocation_country": "Asset Allocation by Country of Risk",
        "allocation_rating": "Asset Allocation by Rating",
        "allocation_asset_class": "Asset Allocation by Asset Class",
        "allocation_label": "Label",
        "allocation_pct": "Allocation %",
        "page_short": "Page",
        "confidence_short": "Confidence",
        "performance": "Performance",
        "period_return": "Period return",
        "benchmark_return": "Benchmark return",
        "source_page": "Source page",
        "confidence": "Confidence",
        "transactions": "Transactions",
        "txn_type": "Type",
        "txn_instrument": "Instrument",
        "txn_isin": "ISIN",
        "txn_amount": "Amount",
        "txn_currency": "Ccy",
        "txn_date": "Date",
        "esg": "ESG",
        "esg_rating": "Rating",
        "esg_sustainable": "Sustainable exposure",
        "esg_controversies": "Controversies",
        "red_flags": "Red Flags",
        "no_red_flags": "No red flags detected.",
        "data_quality": "Data Quality Checks",
        "no_dq_flags": "No data quality issues detected.",
        "regulatory_summary": "Regulatory Summary",
        "regulatory_references": "Regulatory References",
        "required_actions": "Required Actions",
        "action_description": "Description",
        "action_deadline": "Deadline",
        "pages_label": "Pages:",
        "fields_label": "Fields:",
        "disclaimer": "This report was generated automatically by an AI system. All data should be verified against the source document.",
        "fallback_title": "Report",
    },
    "it": {
        "analysis_date": "Data analisi:",
        "pipeline": "Pipeline:",
        "user": "Utente:",
        "allocation_country": "Allocazione per paese di rischio",
        "allocation_rating": "Allocazione per rating",
        "allocation_asset_class": "Allocazione per asset class",
        "allocation_label": "Etichetta",
        "allocation_pct": "Allocazione %",
        "page_short": "Pag.",
        "confidence_short": "Aff.",
        "performance": "Performance",
        "period_return": "Rendimento di periodo",
        "benchmark_return": "Rendimento benchmark",
        "source_page": "Pagina di origine",
        "confidence": "Affidabilità",
        "transactions": "Transazioni",
        "txn_type": "Tipo",
        "txn_instrument": "Strumento",
        "txn_isin": "ISIN",
        "txn_amount": "Importo",
        "txn_currency": "Valuta",
        "txn_date": "Data",
        "esg": "ESG",
        "esg_rating": "Rating",
        "esg_sustainable": "Esposizione sostenibile",
        "esg_controversies": "Controversie",
        "red_flags": "Segnalazioni di Rischio",
        "no_red_flags": "Nessuna segnalazione rilevata.",
        "data_quality": "Controlli di Qualità dei Dati",
        "no_dq_flags": "Nessun problema di qualità dei dati rilevato.",
        "regulatory_summary": "Sintesi Regolamentare",
        "regulatory_references": "Riferimenti Regolamentari",
        "required_actions": "Azioni Richieste",
        "action_description": "Descrizione",
        "action_deadline": "Scadenza",
        "pages_label": "Pagine:",
        "fields_label": "Campi:",
        "disclaimer": "Questo report è stato generato automaticamente da un sistema di IA. Tutti i dati devono essere verificati rispetto al documento originale.",
        "fallback_title": "Report",
    }
}


def _t(lang: str, key: str) -> str:
    """Translate a key to the given language, with fallback to English."""
    return _I18N.get(lang, _I18N["en"]).get(key, _I18N["en"][key])

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

_BASE = getSampleStyleSheet()

_STYLE_TITLE = ParagraphStyle(
    "FinTitle", parent=_BASE["Title"], fontSize=18, spaceAfter=4
)
_STYLE_META = ParagraphStyle(
    "FinMeta", parent=_BASE["Normal"], fontSize=9, textColor=colors.HexColor("#6c757d"), spaceAfter=6
)
_STYLE_HEADING = ParagraphStyle(
    "FinHeading", parent=_BASE["Heading2"], fontSize=12, spaceBefore=14, spaceAfter=4
)
_STYLE_BODY = ParagraphStyle(
    "FinBody", parent=_BASE["Normal"], fontSize=9, leading=13
)
_STYLE_BADGE = ParagraphStyle(
    "FinBadge", parent=_BASE["Normal"], fontSize=8,
    textColor=colors.white, alignment=TA_CENTER, leading=10
)
_STYLE_DISCLAIMER = ParagraphStyle(
    "FinDiscl", parent=_BASE["Normal"], fontSize=7,
    textColor=colors.HexColor("#6c757d"), spaceBefore=16, leading=11
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _badge(label: str, bg: colors.HexColor, width: int = 60) -> Table:
    """Return a small coloured pill Table suitable as a cell value."""
    inner = Table([[Paragraph(label, _STYLE_BADGE)]], colWidths=[width])
    inner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    return inner


def _allocation_table(title: str, entries: list[dict], lang: str = "en") -> list:
    """Build a Paragraph heading + Table for one allocation breakdown."""
    if not entries:
        return []

    rows = [[_t(lang, "allocation_label"), _t(lang, "allocation_pct"), _t(lang, "page_short"), _t(lang, "confidence_short")]]
    row_styles: list[tuple] = []

    for i, entry in enumerate(entries, start=1):
        conf = entry.get("confidence", "medium")
        badge = _badge(conf.upper(), _CONFIDENCE_COLORS.get(conf, colors.grey), width=60)
        rows.append([
            entry.get("label", ""),
            f'{entry.get("pct", 0):.1f}%',
            str(entry.get("source_page", "")),
            badge,
        ])
        if conf == "low":
            row_styles.append(("BACKGROUND", (0, i), (2, i), _LOW_CONF_BG))

    t = Table(rows, colWidths=[185, 80, 45, 70])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("GRID",          (0, 0), (-1, -1), 0.25, _BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        *row_styles,
    ]))
    return [Paragraph(title, _STYLE_HEADING), t, Spacer(1, 8)]


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    """Two-column key/value table."""
    t = Table(rows, colWidths=[160, 220])
    t.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.25, _BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_header(data: dict, lang: str = "en") -> list:
    pipeline_label = data.get("pipeline", "").upper()
    return [
        Paragraph(data.get("doc_name", _t(lang, "fallback_title")), _STYLE_TITLE),
        Paragraph(
            f"{_t(lang, 'analysis_date')} {data.get('analysis_date', '')} &nbsp;|&nbsp; "
            f"{_t(lang, 'pipeline')} {pipeline_label} &nbsp;|&nbsp; "
            f"{_t(lang, 'user')} {data.get('user_id', '')}",
            _STYLE_META,
        ),
        HRFlowable(width="100%", thickness=1, color=_BORDER),
        Spacer(1, 10),
    ]


def _build_pm_sections(extraction: dict, lang: str = "en") -> list:
    flowables: list = []

    # --- Asset allocation ---
    alloc = extraction.get("asset_allocation", {})
    flowables += _allocation_table(_t(lang, "allocation_country"),
                                   alloc.get("by_country_of_risk", []), lang)
    flowables += _allocation_table(_t(lang, "allocation_rating"),
                                   alloc.get("by_rating", []), lang)
    flowables += _allocation_table(_t(lang, "allocation_asset_class"),
                                   alloc.get("by_asset_class", []), lang)

    # --- Performance ---
    perf = extraction.get("performance")
    if perf:
        flowables.append(Paragraph(_t(lang, "performance"), _STYLE_HEADING))
        kv_rows = [
            (_t(lang, "period_return"), f'{perf.get("period_return_pct", 0):.2f}%'),
        ]
        if perf.get("benchmark_return_pct") is not None:
            kv_rows.append((_t(lang, "benchmark_return"), f'{perf["benchmark_return_pct"]:.2f}%'))
        kv_rows.append((_t(lang, "source_page"), str(perf.get("source_page", ""))))
        conf = perf.get("confidence", "medium")
        kv_rows.append((_t(lang, "confidence"), conf.upper()))
        flowables.append(_kv_table(kv_rows))
        flowables.append(Spacer(1, 8))

    # --- Transactions ---
    txns = extraction.get("transactions", [])
    if txns:
        flowables.append(Paragraph(_t(lang, "transactions"), _STYLE_HEADING))
        rows = [[_t(lang, "txn_type"), _t(lang, "txn_instrument"), _t(lang, "txn_isin"), _t(lang, "txn_amount"), _t(lang, "txn_currency"), _t(lang, "txn_date"), _t(lang, "page_short"), _t(lang, "confidence_short")]]
        row_styles: list[tuple] = []
        for i, tx in enumerate(txns, start=1):
            conf = tx.get("confidence", "medium")
            badge = _badge(conf.upper(), _CONFIDENCE_COLORS.get(conf, colors.grey), width=45)
            rows.append([
                tx.get("type", ""),
                Paragraph(tx.get("instrument", ""), _STYLE_BODY),
                tx.get("isin") or "—",
                f'{tx.get("amount", 0):,.0f}',
                tx.get("currency", ""),
                tx.get("date", ""),
                str(tx.get("source_page", "")),
                badge,
            ])
            if conf == "low":
                row_styles.append(("BACKGROUND", (0, i), (6, i), _LOW_CONF_BG))

        t = Table(rows, colWidths=[35, 120, 70, 55, 30, 55, 20, 50])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), _HEADER_BG),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.25, _BORDER),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            *row_styles,
        ]))
        flowables += [t, Spacer(1, 8)]

    # --- ESG ---
    esg = extraction.get("esg")
    if esg:
        flowables.append(Paragraph(_t(lang, "esg"), _STYLE_HEADING))
        kv_rows = []
        if esg.get("rating"):
            kv_rows.append((_t(lang, "esg_rating"), esg["rating"]))
        if esg.get("sustainable_exposure_pct") is not None:
            kv_rows.append((_t(lang, "esg_sustainable"), f'{esg["sustainable_exposure_pct"]:.1f}%'))
        if esg.get("controversies"):
            kv_rows.append((_t(lang, "esg_controversies"), esg["controversies"]))
        if esg.get("source_page"):
            kv_rows.append((_t(lang, "source_page"), str(esg["source_page"])))
        kv_rows.append((_t(lang, "confidence"), esg.get("confidence", "medium").upper()))
        if kv_rows:
            flowables.append(_kv_table(kv_rows))
            flowables.append(Spacer(1, 8))

    return flowables


def _build_rm_sections(red_flags: list[dict], lang: str = "en") -> list:
    flowables: list = []
    flowables.append(Paragraph(_t(lang, "red_flags"), _STYLE_HEADING))

    if not red_flags:
        flowables.append(Paragraph(_t(lang, "no_red_flags"), _STYLE_BODY))
        flowables.append(Spacer(1, 8))
        return flowables

    sorted_flags = sorted(red_flags, key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "info"), 99))

    for flag in sorted_flags:
        sev = flag.get("severity", "info")
        badge_cell = _badge(sev.upper(), _SEVERITY_COLORS.get(sev, colors.grey), width=58)

        pages_str = ", ".join(str(p) for p in flag.get("source_pages", []))
        fields_str = ", ".join(flag.get("affected_fields", []))
        detail_html = (
            f'<b>{flag.get("id", "")}: {flag.get("description", "")}</b><br/>'
            f'{flag.get("detail", "")}<br/>'
            f'<font color="#6c757d">{_t(lang, "pages_label")} {pages_str or "—"} &nbsp;|&nbsp; {_t(lang, "fields_label")} {fields_str or "—"}</font>'
        )
        detail_cell = Paragraph(detail_html, _STYLE_BODY)

        row_table = Table([[badge_cell, detail_cell]], colWidths=[65, 390])
        row_table.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",  (1, 0), (1, 0), 10),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))

        flowables.append(KeepTogether([row_table, Spacer(1, 6)]))

    return flowables


def _build_dq_sections(data_quality_flags: list[dict], lang: str = "en") -> list:
    flowables: list = []
    flowables.append(Paragraph(_t(lang, "data_quality"), _STYLE_HEADING))

    if not data_quality_flags:
        flowables.append(Paragraph(_t(lang, "no_dq_flags"), _STYLE_BODY))
        flowables.append(Spacer(1, 8))
        return flowables

    sorted_flags = sorted(data_quality_flags, key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "info"), 99))

    for flag in sorted_flags:
        sev = flag.get("severity", "info")
        badge_cell = _badge(sev.upper(), _SEVERITY_COLORS.get(sev, colors.grey), width=58)

        pages_str = ", ".join(str(p) for p in flag.get("source_pages", []))
        fields_str = ", ".join(flag.get("affected_fields", []))
        detail_html = (
            f'<b>{flag.get("id", "")}: {flag.get("description", "")}</b><br/>'
            f'{flag.get("detail", "")}<br/>'
            f'<font color="#6c757d">{_t(lang, "pages_label")} {pages_str or "—"} &nbsp;|&nbsp; {_t(lang, "fields_label")} {fields_str or "—"}</font>'
        )
        detail_cell = Paragraph(detail_html, _STYLE_BODY)

        row_table = Table([[badge_cell, detail_cell]], colWidths=[65, 390])
        row_table.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",  (1, 0), (1, 0), 10),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))

        flowables.append(KeepTogether([row_table, Spacer(1, 6)]))

    return flowables


def _build_disclaimer(lang: str = "en") -> list:
    return [
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=0.5, color=_BORDER),
        Paragraph(_t(lang, "disclaimer"), _STYLE_DISCLAIMER),
    ]


def _build_regulatory_sections(summary: dict, lang: str = "en") -> list:
    flowables: list = []
    flowables.append(Paragraph(_t(lang, "regulatory_summary"), _STYLE_HEADING))
    flowables.append(Paragraph(summary.get("executive_summary", "—"), _STYLE_BODY))
    flowables.append(Spacer(1, 8))

    refs = summary.get("regulatory_references", [])
    flowables.append(Paragraph(_t(lang, "regulatory_references"), _STYLE_HEADING))
    if refs:
        rows = [[Paragraph(ref, _STYLE_BODY)] for ref in refs]
        t = Table(rows, colWidths=[455])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, _BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        flowables.append(t)
    else:
        flowables.append(Paragraph("—", _STYLE_BODY))
    flowables.append(Spacer(1, 8))

    actions = summary.get("required_actions", [])
    flowables.append(Paragraph(_t(lang, "required_actions"), _STYLE_HEADING))
    if actions:
        rows = [[_t(lang, "action_description"), _t(lang, "action_deadline"), _t(lang, "page_short")]]
        for action in actions:
            rows.append([
                Paragraph(action.get("description", "—"), _STYLE_BODY),
                action.get("deadline") or "—",
                str(action.get("source_page", "—")),
            ])
        t = Table(rows, colWidths=[315, 90, 50])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, _BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        flowables.append(t)
    else:
        flowables.append(Paragraph("—", _STYLE_BODY))
    flowables.append(Spacer(1, 8))
    return flowables


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pdf(data: dict[str, Any], output_path: str) -> str:
    """Generate a PDF report and write it to output_path/report.pdf.

    Args:
        data: Dict with keys: pipeline ("pm"|"rm"|"dq"|"regulatory"), doc_name, analysis_date,
              user_id, language ("en"|"it"), and pipeline-specific payload.
        output_path: Directory where report.pdf will be written.

    Returns:
        Absolute path to the generated report.pdf.
    """
    out_dir = Path(output_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "report.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=50,
    )

    lang = data.get("language", "en")
    flowables = _build_header(data, lang)

    pipeline = data.get("pipeline", "")
    if pipeline == "pm":
        flowables += _build_pm_sections(data.get("extraction", {}), lang)
    elif pipeline == "rm":
        flowables += _build_rm_sections(data.get("red_flags", []), lang)
    elif pipeline == "dq":
        flowables += _build_dq_sections(data.get("data_quality_flags", []), lang)
    elif pipeline == "regulatory":
        flowables += _build_regulatory_sections(data.get("regulatory", {}), lang)

    flowables += _build_disclaimer(lang)
    doc.build(flowables)
    return str(pdf_path)
