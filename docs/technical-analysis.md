# Finadoc — Technical Analysis

> **Status**: POC design — aligned with the functional analysis (`docs/functional-analysis.md`).

---

## 1. Architecture Overview

Finadoc POC is composed of two cooperating processes, orchestrated via Docker Compose on a local laptop:

```
┌──────────────────────────────────────────────────────────────────┐
│  Local laptop                                                    │
│                                                                  │
│  ┌─────────────────────────┐   HTTP    ┌──────────────────────┐ │
│  │  .NET Core App          │ ────────► │  Python AI Service   │ │
│  │  (ASP.NET Core / Blazor)│ ◄──────── │  (FastAPI)           │ │
│  │                         │           │                      │ │
│  │  - Web UI               │           │  - Pre-processing    │ │
│  │  - REST API             │           │  - Masking (Presidio)│ │
│  │  - Auth (local + LDAPs) │           │  - LLM calls (Mistral│ │
│  │  - Audit trail          │           │  - Extraction/Flags  │ │
│  │  - File management      │           │  - PDF generation    │ │
│  │  - EF Core + SQLite     │           │                      │ │
│  └─────────────┬───────────┘           └──────────┬───────────┘ │
│                │                                  │             │
│        ┌───────▼──────────────────────────────────▼───────┐    │
│        │            Shared volume (local filesystem)       │    │
│        │   /data/uploads/   /data/outputs/   /data/db/     │    │
│        └───────────────────────────────────────────────────┘    │
│                                                                  │
│                                          ▲  HTTPS               │
│                                          │                       │
└──────────────────────────────────────────┼───────────────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  Mistral SaaS   │
                                  │  API (EU)        │
                                  └─────────────────┘
```

**Key design principle**: the .NET app is the single entry point for the user (browser) and the system of record (auth, audit, data lifecycle). The Python service is a stateless internal worker, never exposed to the outside.

---

## 2. Tech Stack

| Layer | Technology | Version | Notes |
|---|---|---|---|
| **Web framework** | ASP.NET Core — Blazor Server | .NET 10 | Real-time UI updates useful for showing analysis progress |
| **Backend API** | ASP.NET Core Web API | .NET 10 | Internal endpoints consumed by Blazor and optionally by future clients |
| **ORM** | Entity Framework Core | 10.x | SQLite provider for POC |
| **Database** | SQLite | 3.x | File-based, no separate service needed on laptop |
| **AI service** | Python + FastAPI | Python 3.13 / FastAPI 0.135+ | Internal HTTP service, port 8000. Python 3.13 required: Presidio is not yet compatible with 3.14 |
| **LLM** | Mistral SaaS API | — | `mistral-small-latest` as baseline; `mistral-large-latest` for complex tasks |
| **PDF parsing** | PyMuPDF (`fitz`) + pdfplumber | PyMuPDF 1.27+ / pdfplumber 0.11+ | PyMuPDF for text/metadata, pdfplumber for tables |
| **Excel parsing** | pandas + openpyxl | latest | |
| **Masking / PII** | Microsoft Presidio | 2.2+ | NER-based entity detection; supports Italian and English. Requires Python 3.10–3.13 |
| **LLM orchestration** | `mistralai` Python SDK | 2.x | v2 has breaking changes vs v1 — use v2 from the start. Direct calls; no LangChain in POC |
| **PDF generation** | ReportLab | 4.4+ | Programmatic PDF output |
| **Containerization** | Docker + Docker Compose | Compose v2 | Optional but recommended for reproducibility |
| **Secret management** | `.env` file (POC) | — | Mistral API key and app secrets stored in `.env`, never committed |

### .NET 10 rationale
.NET 10 is the current LTS release (November 2025), supported until November 2028. It is the natural choice for a new project: LTS stability, long support window, and no forced migration in the short term.

### Blazor Server vs SPA
Blazor Server is chosen over a separate React/Angular SPA because:
- Single codebase, single developer.
- Real-time SignalR connection enables streaming status updates during LLM analysis (no polling required).
- No CORS configuration needed between frontend and API.

---

## 3. Component Design

### 3.1 ASP.NET Core Application

Responsibilities:
- Serve the Blazor Server UI.
- Expose internal REST endpoints (for health checks and future integrations).
- Handle authentication (local identity + LDAPs abstraction layer).
- Manage audit trail persistence.
- Trigger analysis jobs by calling the Python AI service.
- Manage document and analysis lifecycle (upload, storage, 90-day retention cleanup).

Project structure (suggested):

```
Finadoc.Web/
├── Pages/                   # Blazor pages (Login, Dashboard, Upload, Report, Admin)
├── Components/              # Shared UI components
├── Services/                # Application services (AnalysisService, AuditService, RetentionService, ...)
├── Auth/
│   ├── IAuthProvider.cs     # Abstraction for auth backends
│   ├── LocalAuthProvider.cs # username+password (ASP.NET Core Identity)
│   └── LdapsAuthProvider.cs # LDAPs binding — STUB in POC (throws NotImplementedException)
├── Data/
│   ├── AppDbContext.cs      # EF Core context
│   └── Migrations/
├── Models/                  # Domain entities (User, Group, Document, Analysis, AuditEvent)
├── Workers/                 # Background workers (RetentionCleanupWorker)
└── appsettings.json
```

### 3.2 Python AI Service

Responsibilities:
- Expose a small set of FastAPI endpoints called by the .NET app.
- Perform document pre-processing (text extraction).
- Apply masking / pseudonymization (Presidio).
- Orchestrate LLM calls to Mistral.
- Parse and validate LLM responses.
- Run cross-source consistency checks.
- Generate the PDF report (ReportLab).
- Return the PDF file path (shared volume) to the .NET caller.

API surface (internal, not exposed to the browser):

| Method | Path | Description |
|---|---|---|
| `POST` | `/analyze/pm` | Structured extraction for PM group |
| `POST` | `/analyze/rm` | Red flag detection for RM group |
| `POST` | `/analyze/regulatory` | Regulatory communication summary |
| `GET` | `/health` | Health check |

Each analysis endpoint accepts:
```json
{
  "document_path": "/data/uploads/<uuid>/<filename>",
  "document_format": "pdf" | "excel",
  "language": "it" | "en" | "auto",
  "output_path": "/data/outputs/<uuid>/",
  "user_context": { "user_id": "...", "groups": ["PM", "RM"] }
}
```

And returns:
```json
{
  "status": "ok" | "error",
  "pdf_path": "/data/outputs/<uuid>/report.pdf",
  "summary": { ... },   // machine-readable extraction for the .NET app to store
  "warnings": [ ... ]
}
```

Python project structure:

```
finadoc_ai/
├── main.py                  # FastAPI app, routes
├── pipeline/
│   ├── ingestion.py         # PDF / Excel text extraction
│   ├── masking.py           # Presidio integration
│   ├── llm.py               # Mistral API client wrapper
│   ├── extraction.py        # PM: structured extraction logic
│   ├── red_flags.py         # RM: anomaly detection logic
│   ├── summary.py           # Regulatory summary logic
│   ├── consistency.py       # Cross-source check
│   └── pdf_output.py        # ReportLab PDF generation
├── models/
│   └── schemas.py           # Pydantic request/response models
└── config.py                # Settings (API key, model names, thresholds)
```

### 3.3 Database (SQLite + EF Core)

SQLite is sufficient for a single-tenant POC on a local laptop. It avoids running a separate DB server.

Main tables:

| Table | Key columns |
|---|---|
| `Users` | `Id`, `Username`, `PasswordHash`, `IsAdmin`, `IsActive`, `CreatedAt` |
| `Groups` | `Id`, `Name` (`PM`, `RM`) |
| `UserGroups` | `UserId`, `GroupId` |
| `Documents` | `Id`, `UserId`, `OriginalFileName`, `StoragePath`, `Format`, `Language`, `UploadedAt`, `ExpiresAt` |
| `Analyses` | `Id`, `DocumentId`, `GroupContext`, `Status`, `PdfPath`, `StartedAt`, `CompletedAt`, `ExpiresAt` |
| `AuditEvents` | `Id`, `Timestamp`, `UserId`, `Action`, `TargetType`, `TargetId`, `Outcome`, `Details` |

All rows with `ExpiresAt <= now` are deleted by `RetentionCleanupWorker` (runs daily).

### 3.4 File Storage

All files are stored on the local filesystem under a single root directory (e.g., `/data/` in Docker or `%APPDATA%/Finadoc/` on Windows without Docker).

```
/data/
├── uploads/
│   └── <document-uuid>/
│       └── <original-filename>
├── outputs/
│   └── <analysis-uuid>/
│       └── report.pdf
└── finadoc.db               # SQLite database file
```

The `.NET` app writes uploaded files to `uploads/`. The Python service reads from `uploads/` and writes PDFs to `outputs/`. Both services mount the same Docker volume.

---

## 4. AI Pipeline — Detail

### 4.1 Document Pre-processing

**PDF (native/text-based — no OCR)**:
- Use `PyMuPDF` (`fitz`) to extract:
  - Text per page (preserving reading order).
  - Tables (via `pdfplumber` for structured tables).
  - Page metadata (page number, section headings detected via font size heuristics).
- Output: a structured representation `{ page: int, text: str, tables: [DataFrame] }` per page.

**Excel**:
- Use `pandas` + `openpyxl` to read all sheets.
- Output: a list of named DataFrames, one per sheet.

Scanned PDFs (image-based) are **out of scope for the POC** — the pipeline will raise an error if no text layer is detected.

### 4.2 Masking / Pseudonymization (Presidio)

**Library**: [Microsoft Presidio](https://microsoft.github.io/presidio/) — open-source NER-based PII detection, supports Italian and English via spaCy language models.

**Process**:
1. Run `presidio-analyzer` on the extracted text to detect entities:
   - PERSON, ORG, IBAN, PHONE_NUMBER, EMAIL, TAX_ID (Italian: codice fiscale), DATE_TIME, LOCATION.
2. Run `presidio-anonymizer` to replace detected entities with placeholders:
   - e.g., `Mario Rossi` → `<PERSON_1>`, `IT60X0542811101000000123456` → `<IBAN_1>`.
3. Keep a mapping `{ placeholder → original_value }` in application memory (never stored or sent externally).
4. The masked text is sent to Mistral. The LLM response references placeholders.
5. After the LLM response is received and parsed, re-apply the mapping to restore original values in the final PDF output (where the authorized user needs to see real data).

**Why full implementation even for the POC**: the masking component is architecturally critical (data protection layer between the application and the external LLM). A simplified regex approach would be unreliable and would need to be replaced before any real document is processed.

### 4.3 LLM Orchestration (Mistral)

**SDK**: official `mistralai` Python package.

**Models**:

| Task | Recommended model | Rationale |
|---|---|---|
| Structured extraction (PM) | `mistral-small-latest` | High-throughput, structured JSON output, low cost |
| Red flag detection (RM) | `mistral-large-latest` | Requires reasoning across multiple data points |
| Regulatory summary | `mistral-small-latest` | Summarization is straightforward |

**Prompt design**:
- Each analysis type uses a **system prompt** that defines the task, output format (JSON schema), and quality constraints (mandatory citation, confidence flag).
- The **user message** contains the masked document text (chunked if needed to fit context).
- Responses are requested in **JSON mode** (`response_format={"type": "json_object"}`) to guarantee parseable output.

**Per-group context**:
- System prompts are stored as versioned template files per group (`prompts/PM/extraction_v1.txt`, `prompts/RM/red_flags_v1.txt`).
- RAG knowledge bases per group: in the POC this is a simple set of static reference documents (e.g., regulatory threshold tables for UCITS concentration limits) embedded at prompt time.

**Chunking**: documents ≤ 10 pages fit comfortably in Mistral's context window (32K tokens for `mistral-small`). No chunking strategy required in the POC.

### 4.4 Structured Extraction (PM group)

The extraction prompt instructs the model to return a JSON object with the following top-level keys:

```json
{
  "asset_allocation": {
    "by_country_of_risk": [{ "country": "...", "pct": 0.0, "source_page": 0, "confidence": "high|medium|low" }],
    "by_rating":         [{ "rating": "...", "pct": 0.0, "source_page": 0, "confidence": "..." }],
    "by_asset_class":    [{ "class": "Equity|Bond|Fund|Derivatives|Other", "pct": 0.0, "source_page": 0, "confidence": "..." }]
  },
  "performance": {
    "period_return_pct": 0.0,
    "benchmark_return_pct": 0.0,
    "source_page": 0,
    "confidence": "..."
  },
  "transactions": [
    { "type": "buy|sell", "instrument": "...", "isin": "...", "amount": 0.0, "currency": "...", "date": "...", "source_page": 0, "confidence": "..." }
  ],
  "esg": {
    "rating": "...",
    "sustainable_exposure_pct": 0.0,
    "controversies": "...",
    "source_page": 0,
    "confidence": "..."
  }
}
```

After parsing the LLM response:
- **Confidence flag** (`high` / `medium` / `low`) is preserved from the model's self-assessment.
- Any field with confidence `low` is rendered with a visual warning in the PDF.

### 4.5 Red Flag Detection (RM group)

The red flag prompt instructs the model to:
1. Verify that all percentage breakdowns sum to 100% (±0.1% rounding tolerance).
2. Identify any allocation figure that appears inconsistently across different sections of the document (cross-source check).
3. Check known UCITS concentration thresholds (max 10% in a single issuer, max 35% in government bonds of a single issuer, etc.) against the extracted allocation data.
4. Flag significant deviations vs prior period **only if two documents are provided** (optional in POC).

Response format:

```json
{
  "red_flags": [
    {
      "id": "RF-001",
      "severity": "critical|warning|info",
      "description": "...",
      "affected_fields": ["asset_allocation.by_asset_class"],
      "source_pages": [3, 7],
      "detail": "Sum of asset class percentages is 101.3%, expected 100%."
    }
  ]
}
```

### 4.6 Regulatory Communication Summary

The summary prompt instructs the model to return:

```json
{
  "executive_summary": "...",
  "regulatory_references": ["MiFID II Art. 25", "AIFMD Art. 22"],
  "required_actions": [
    { "description": "...", "deadline": "2025-06-30", "source_page": 2 }
  ]
}
```

`regulatory_references` are extracted **only if explicitly mentioned** in the document (F3.C.2 constraint).

### 4.7 Cross-Source Consistency Check

After structured extraction, a deterministic Python check (no LLM needed) verifies:
- All percentage arrays sum to 100% (±tolerance).
- Figures that appear in multiple places in the document (e.g., total net assets on page 1 and in the allocation table on page 4) are consistent.
- Detected inconsistencies are added to the red flag list with severity `warning`.

### 4.8 PDF Report Generation (ReportLab)

The PDF report is generated by `pdf_output.py` using ReportLab's `platypus` layout engine.

Structure of the generated PDF:

| Section | Content |
|---|---|
| **Cover / header** | Document name, analysis date, group context, user ID |
| **Extraction results** (PM) | Tables per category (country, rating, asset class, performance, transactions, ESG) with source page and confidence badge |
| **Red flags** (RM) | Sorted by severity (critical first), each with description, affected fields, source pages |
| **Regulatory summary** | Executive summary, regulatory references list, actions/deadlines table |
| **Disclaimer** | Standard text: "This report is generated automatically by an AI system. All data must be verified against the source document." |

Confidence badges: `[HIGH]` / `[MEDIUM]` / `[LOW — TO VERIFY]` — rendered inline next to each data point.

---

## 5. Authentication Design

### 5.1 Local authentication (POC implementation)

- **ASP.NET Core Identity** stores users and hashed passwords (bcrypt via Identity's default PBKDF2 or swapped for BCrypt.Net).
- On first run, if no admin user exists, the app presents a setup screen to create the initial admin (username + password).
- Session cookie, 8-hour sliding expiration.

### 5.2 LDAPs abstraction (POC: stub)

An `IAuthProvider` interface defines:
```csharp
Task<AuthResult> AuthenticateAsync(string username, string password);
Task<UserInfo?> GetUserInfoAsync(string username);
```

Two implementations:
- `LocalAuthProvider` — uses ASP.NET Core Identity. Active in POC.
- `LdapsAuthProvider` — stub in POC (`throw new NotImplementedException("LDAPs not implemented in POC")`). The constructor accepts `LdapsSettings` (host, port, base DN, bind DN, bind password, TLS cert path) to prove the configuration model is defined. Full implementation in a later version using `Novell.Directory.Ldap.NETStandard` or `System.DirectoryServices.Protocols`.

Switching between providers is controlled by `appsettings.json`:
```json
"Auth": {
  "Provider": "Local",   // or "Ldaps"
  "Ldaps": {
    "Host": "",
    "Port": 636,
    "BaseDn": "",
    ...
  }
}
```

---

## 6. Security Design

| Concern | Approach |
|---|---|
| **Password storage** | PBKDF2-SHA512 (ASP.NET Core Identity default) |
| **Session** | HttpOnly, Secure cookie; 8-hour sliding expiration |
| **Mistral API key** | Stored in `.env` (Docker) or `appsettings.Development.json` (local run); never committed to git (`.gitignore`) |
| **Internal Python service** | Not exposed on the host network; reachable only via the Docker internal network (`ai:8000`) |
| **TLS for LDAPs** | `LdapsAuthProvider` enforces TLS (port 636); certificate validation configurable |
| **Audit trail** | Append-only `AuditEvents` table; no delete API exposed (only the retention cleanup worker purges rows older than 90 days) |
| **Sensitive data in transit** | Masked text sent to Mistral SaaS over HTTPS (TLS 1.2+) |
| **Data residency** | Mistral SaaS endpoints are EU-hosted (`api.mistral.ai` — data processed in EU). Verify on [Mistral's data processing agreement](https://mistral.ai/terms) before production use |

---

## 7. Deployment

### 7.1 Docker Compose (recommended)

`docker-compose.yml`:

```yaml
version: "3.9"

services:
  app:
    build: ./Finadoc.Web
    ports:
      - "8080:8080"
    environment:
      - ASPNETCORE_ENVIRONMENT=Production
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - AI_SERVICE_URL=http://ai:8000
    volumes:
      - finadoc_data:/data
    depends_on:
      - ai

  ai:
    build: ./finadoc_ai
    expose:
      - "8000"
    environment:
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
    volumes:
      - finadoc_data:/data

volumes:
  finadoc_data:
```

`.env` file (never committed):
```
MISTRAL_API_KEY=your_key_here
```

Start:
```bash
docker compose up --build
```

Access the app at `http://localhost:8080`.

### 7.2 Local run without Docker

For development, both processes can be run locally:

```bash
# Terminal 1 — Python AI service
cd finadoc_ai
pip install -r requirements.txt
python -m spacy download it_core_news_lg   # Italian NER model for Presidio
python -m spacy download en_core_web_lg    # English NER model
uvicorn main:app --port 8000

# Terminal 2 — .NET app
cd Finadoc.Web
dotnet run
```

Access at `https://localhost:5001` (or the port shown in the dotnet output).

---

## 8. Mistral Account Setup

### 8.1 Create a Mistral account

1. Go to [https://console.mistral.ai](https://console.mistral.ai).
2. Click **Sign up** and register with an email address.
3. Verify your email.

### 8.2 Create an API key

1. In the Mistral console, navigate to **API Keys** (left sidebar).
2. Click **Create new key**.
3. Give it a name (e.g., `finadoc-poc`).
4. Copy the key immediately — it is only shown once.
5. Store it in the `.env` file:
   ```
   MISTRAL_API_KEY=<your key here>
   ```

### 8.3 Verify data residency

Mistral processes data in the EU. Before using real documents:
- Review the [Mistral Data Processing Agreement](https://mistral.ai/terms).
- Confirm the `api.mistral.ai` endpoint routes to EU infrastructure.
- Optionally, request a signed DPA from Mistral for GDPR compliance.

### 8.4 Choose a model

For the POC, use:

| Model ID | Use case | Price (indicative, April 2025) |
|---|---|---|
| `mistral-small-latest` | PM extraction, regulatory summary | ~$0.10 / 1M input tokens |
| `mistral-large-latest` | RM red flag detection | ~$2.00 / 1M input tokens |

Start with `mistral-small-latest` for all tasks, then upgrade to `mistral-large-latest` for red flag detection if quality is insufficient.

### 8.5 Install the Python SDK

```bash
pip install "mistralai>=2.0"
```

> **Note**: SDK v2 has breaking changes vs v1. Start from v2 directly to avoid a migration.

Minimal usage example (SDK v2):
```python
from mistralai import Mistral

client = Mistral(api_key="your_key")
response = client.chat.complete(
    model="mistral-small-latest",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

---

## 9. Development Roadmap (suggested order)

The POC implementation is suggested in the following order to maximize early testability:

| Phase | Deliverable | Key items |
|---|---|---|
| **P1 — Skeleton** | Running Docker Compose with both services, health checks passing | Blazor shell, FastAPI `/health`, shared volume |
| **P2 — Auth** | Login form, local user creation, admin setup flow | ASP.NET Core Identity, `IAuthProvider`, user/group CRUD |
| **P3 — Upload** | File upload, storage, DB record, audit event | F2, F5 (upload event), retention metadata |
| **P4 — AI pipeline (PM)** | PDF ingestion → masking → Mistral call → extraction JSON | `ingestion.py`, `masking.py`, `llm.py`, `extraction.py` |
| **P5 — PDF output** | ReportLab PDF generated from extraction JSON, downloadable | `pdf_output.py`, F4 |
| **P6 — Red flags (RM)** | Red flag analysis, severity classification, added to PDF | `red_flags.py`, F3.B |
| **P7 — Regulatory summary** | Summary analysis endpoint, added to PDF | `summary.py`, F3.C |
| **P8 — Retention & audit** | 90-day cleanup worker, full audit event logging | `RetentionCleanupWorker`, F5, F6 |
| **P9 — Test documents** | 3 fictitious fund documents with injected criticalities | Used to validate P4-P7 end to end |
| **P10 — Polish** | Excel ingestion, confidence badges, cross-source check, disclaimers | F2.2, F3.3, F4.3 |

---

