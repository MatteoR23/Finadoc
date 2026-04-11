# Finadoc — Agent context

## Project

Finadoc is a POC web app for an Italian asset management company (SGR). Users upload financial documents (PDF/Excel) and receive an automatically generated PDF report in English. The project is currently in the design phase — no application code exists yet.

## Documentation — read these first

| Document | What it covers |
|---|---|
| [docs/functional-analysis.md](docs/functional-analysis.md) | Requirements, roles, use cases, user flows, NFRs, scope |
| [docs/technical-analysis.md](docs/technical-analysis.md) | Architecture, stack, AI pipeline, database schema, security, deployment |
| [docs/roadmap.md](docs/roadmap.md) | 10 build phases with deliverables and acceptance criteria |

## System architecture

```
Browser
  │  HTTP
  ▼
.NET 10 / Blazor Server app   ──HTTP──►  Python 3.13 / FastAPI service
  │  (UI, auth, audit, DB)                 (ingestion, masking, LLM, PDF)
  │                                                  │
  └────────────── shared Docker volume ──────────────┘
                    /data/uploads/
                    /data/outputs/
                    /data/finadoc.db

                                   Python service ──HTTPS──► Mistral SaaS (EU)
```

The .NET app is the only entry point — the Python service is internal and unreachable from outside the Docker network.

## Roles

| Role | AI context |
|---|---|
| **Admin** | Manages users, groups, configuration. No AI features. |
| **Portfolio Manager (PM)** | Structured extraction: asset allocation, performance, transactions, ESG. Uses `mistral-small-latest`. |
| **Risk Manager (RM)** | Red flag detection: numerical inconsistencies, threshold breaches, deviations. Uses `mistral-large-latest`. |

A user can belong to both PM and RM simultaneously.

## Python AI pipeline (per analysis)

1. Ingest document (PyMuPDF / pdfplumber for PDF; pandas/openpyxl for Excel)
2. Mask PII with Presidio — placeholder mapping in memory only, never written to disk
3. Call Mistral in JSON mode — prompt template from `prompts/<group>/<task>_v1.txt`
4. Parse and validate response against Pydantic schema
5. Run cross-source consistency check (deterministic Python, no LLM)
6. Generate PDF report with ReportLab
7. Return `{status, pdf_path, summary, warnings}` to the .NET app

## API endpoints (Python service)

| Method | Path | Group |
|---|---|---|
| POST | `/analyze/pm` | PM — structured extraction |
| POST | `/analyze/rm` | RM — red flag detection |
| POST | `/analyze/regulatory` | Both — regulatory summary |
| GET | `/health` | — |

Request body: `{document_path, document_format, language, output_path, user_context}`.

## Database tables (SQLite, owned by .NET)

`Users`, `Groups`, `UserGroups`, `Documents`, `Analyses`, `AuditEvents`.

Schema details in [docs/technical-analysis.md](docs/technical-analysis.md).

## Hard constraints for any agent working on this project

- **Never send unmasked text to Mistral.** Masking runs before every LLM call, without exception.
- **EU data residency.** Do not introduce any non-EU external service or API call.
- **Presidio for masking** — not regex. The masking must be reliable on real financial documents.
- **mistralai SDK v2** — do not use v1; there are breaking changes between the two.
- **Python 3.13** — do not use 3.14; Presidio does not support it yet.
- **No chunking** — documents are capped at 10 pages and fit within the model's context window.
- **LDAPs stub** — the interface and config are defined; do not implement the actual directory binding in the POC.
- **Audit trail** — every user-visible action must produce an `AuditEvent` record.
- **Retention** — all `Document` and `Analysis` records must have an `ExpiresAt = now + 90 days`; the cleanup worker removes them automatically.

## Build order

Follow [docs/roadmap.md](docs/roadmap.md) phase by phase. Each phase has explicit acceptance criteria — verify them before starting the next.

P1 → infra skeleton  
P2 → auth  
P3 → upload  
P4 → PM pipeline  
P5 → PDF output  
P6 → RM pipeline  
P7 → regulatory summary  
P8 → retention + audit  
P9 → test documents  
P10 → polish  
