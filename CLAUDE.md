# FinLens — Claude Code context

## Project

FinLens is a POC web app for an Italian SGR. Users upload financial documents (PDF/Excel) and receive an automatically generated PDF report in English. Phases P1–P4 are complete; P5 (PDF output) is next.

## Documentation — read these before writing any code

| Document | What it covers |
|---|---|
| [docs/functional-analysis.md](docs/functional-analysis.md) | Requirements, roles (Admin/PM/RM), use cases, user flows, NFRs, scope, out-of-scope |
| [docs/technical-analysis.md](docs/technical-analysis.md) | Architecture, stack, AI pipeline, database schema, security, deployment, Mistral setup |
| [docs/roadmap.md](docs/roadmap.md) | Build order — 10 phases with deliverables and acceptance criteria |

## Architecture in one paragraph

Four Docker services collaborate. The **.NET 10 / Blazor Server app** serves the UI, owns auth (custom PBKDF2-SHA512, no ASP.NET Identity), manages the document lifecycle, writes the audit trail, and calls the Python service over HTTP (authenticated via `X-Internal-Api-Key`). The **Python 3.14 / FastAPI service** handles everything AI: PDF/Excel ingestion (PyMuPDF, pdfplumber, pandas), PII masking (Microsoft Presidio), Mistral API calls, extraction/flag logic, and PDF generation (ReportLab). **PostgreSQL 16** is the database; the .NET app owns the schema via EF Core migrations. **MinIO** (S3-compatible) stores uploaded documents and generated outputs — both services read/write via the S3 API.

## Stack

- .NET 10, ASP.NET Core, Blazor Server, EF Core, PostgreSQL 16
- Python 3.14, FastAPI, PyMuPDF, pdfplumber, pandas, Presidio, mistralai v2, ReportLab
- MinIO (S3-compatible object store) for document and output storage
- Mistral SaaS (EU): `mistral-small-latest` for PM extraction and regulatory summary, `mistral-large-latest` for RM red flag detection
- Docker Compose for local orchestration

## Key constraints

- **Data residency**: EU/Italy only. No non-EU external services.
- **PII masking**: Presidio-based, not a regex shortcut. Masking happens before any text reaches Mistral. The placeholder mapping lives in memory only — never written to disk.
- **Retention**: documents, analyses, and audit logs are deleted after 90 days. Cleanup runs daily as a background worker.
- **Mistral models**: use `mistral-small-latest` by default (PM extraction, DQ data quality); switch to `mistral-large-latest` only for RM risk management analysis (complex financial risk reasoning).
- **No chunking**: documents are capped at 10 pages — they fit within the 32K-token context window.
- **LDAPs**: interface and config model are defined; actual directory binding is NOT implemented in the POC (stub throws `NotImplementedException`).
- **Scanned PDFs**: rejected — pipeline requires a text layer.

## Project layout

```
FinLens.Web/          # .NET app
FinLens.Web.Tests/    # xUnit test project
finlens_ai/           # Python AI service
  pipeline/           # ingestion, masking, llm, extraction, red_flags, summary, pdf_output, s3
  models/schemas.py
  prompts/PM/ RM/ regulatory/
  tests/
docker-compose.yml
.env                  # MISTRAL_API_KEY, INTERNAL_API_KEY (excluded from git)
docs/
```

## Build order

Follow the phases in [docs/roadmap.md](docs/roadmap.md): P1 (infra) → P2 (auth) → P3 (upload) → P4 (PM pipeline) → P5 (PDF output) → P6 (RM pipeline) → P7 (regulatory summary) → P8 (retention + audit) → P9 (test documents) → P10 (polish).

Do not skip phases — each one provides the foundation for the next.
