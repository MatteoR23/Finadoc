# Finadoc

AI-powered application for analyzing financial documents, designed for an Italian asset management company (SGR — *Società di Gestione del Risparmio*).

## Status

**Proof of Concept (POC)** — in active development. Phases P1–P4 complete (infra, auth, upload, PM pipeline). P5 (PDF output) is next.

## Goal

Help portfolio managers and risk managers extract, validate and summarize information from fund documents (factsheets, periodic reports, regulatory communications) without making mistakes — reducing manual reading and increasing reliability.

## POC scope

The POC is a locally installable web application that lets an authenticated user upload a PDF or Excel document and automatically obtain a **PDF report in English** containing:

1. **Structured extraction** of fund factsheet data (asset allocation by country of risk, by rating, by security classification — Equity / Bond / Fund / Derivatives), performance, transactions, ESG.
2. **Red flag / anomaly detection** (numerical inconsistencies, deviations vs prior period, breach of regulatory thresholds).
3. **Summarization** of regulatory communications (Consob, Bank of Italy, ESMA).

Every extracted data point is **cited** with a reference to the source page/paragraph. Quality is enforced via **mandatory source citation**, **per-data-point confidence flags** and **cross-source consistency checks** — no human review workflow in the POC.

## Key choices

| Area | Choice |
|---|---|
| **LLM** | [Mistral](https://mistral.ai/) (European, SaaS API hosted in EU) |
| **Backend / API** | .NET Core |
| **AI pipeline** | Python |
| **Frontend** | Web app, desktop-first |
| **Auth** | Username + password (admin created on first run), LDAPs support |
| **Tenancy** | Single-tenant |
| **Deployment (POC)** | Local laptop |
| **Data residency** | EU / Italy only |
| **Retention** | 90 days (documents, analyses, audit logs) |

## User groups

The POC supports two roles, each with its own AI context (prompts, RAG, extraction templates — no fine-tuning):

- **Portfolio Manager (PM)** — focused on data extraction (asset allocation, performance, ESG, transactions).
- **Risk Manager (RM)** — focused on red flag and anomaly detection.

A single user can belong to both groups.

## Out of scope (POC)

Conversational Q&A, automatic classification, semantic search, document comparison (no historical data available), versioning, human-in-the-loop review, notifications, collaboration, integrations with external systems (PMS, DMS, CRM, data providers, corporate SSO), mobile app, multi-tenancy, corporate PDF templates, model fine-tuning, OCR for scanned documents.

## Repository layout

```
.
├── README.md
├── CLAUDE.md                       # Claude Code context (architecture, constraints, build order)
├── AGENTS.md                       # AI agent context (same, more structured)
├── Finadoc.Web/                    # .NET 10 Blazor Server app
├── Finadoc.Web.Tests/              # xUnit test project
├── finadoc_ai/                     # Python 3.14 FastAPI AI service
│   ├── pipeline/                   # ingestion, masking, llm, extraction, pdf_output, s3, …
│   ├── models/schemas.py
│   ├── prompts/                    # PM/, RM/, regulatory/
│   └── tests/
├── docker-compose.yml              # app + ai + postgres + minio + minio-init
└── docs/
    ├── functional-analysis.md
    ├── technical-analysis.md
    └── roadmap.md
```

## Documentation

- [Functional analysis](docs/functional-analysis.md) — requirements, actors, use cases, user flows, NFRs, scope.
- [Technical analysis](docs/technical-analysis.md) — architecture, tech stack, AI pipeline, security, deployment, Mistral setup.
- [Roadmap](docs/roadmap.md) — build order, phase deliverables, acceptance criteria.

## Tech stack

| Layer | Technology |
|---|---|
| Web + API | .NET 10, ASP.NET Core, Blazor Server |
| Database | PostgreSQL 16 (EF Core) |
| Object storage | MinIO (S3-compatible) |
| AI pipeline | Python 3.14, FastAPI |
| LLM | Mistral SaaS API (EU) |
| Orchestration | Docker Compose |

## Getting started

```bash
cp .env.example .env
# Fill in MISTRAL_API_KEY and INTERNAL_API_KEY in .env
docker compose up --build
# → http://localhost:8080 (first run prompts for admin password)
```
