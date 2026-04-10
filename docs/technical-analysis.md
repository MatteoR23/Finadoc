# Finadoc — Technical Analysis

> Aligned with `docs/functional-analysis.md`. POC scope only.

---

## Architecture

Two processes, one shared volume, one external API call:

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

The .NET app is the entry point for everything: it serves the UI, owns auth and session, writes the audit trail, and manages the document lifecycle. The Python service handles the AI work — it never talks to the browser directly and is not reachable from outside the Docker network.

---

## Stack

| | Technology | Version |
|---|---|---|
| Web + API | ASP.NET Core / Blazor Server | .NET 10 |
| ORM | Entity Framework Core | 10.x |
| Database | SQLite | 3.x |
| AI service | Python + FastAPI | 3.13 / 0.135+ |
| PDF parsing | PyMuPDF + pdfplumber | 1.27+ / 0.11+ |
| Excel parsing | pandas + openpyxl | latest |
| PII masking | Microsoft Presidio | 2.2+ |
| LLM | Mistral SaaS | — |
| LLM SDK | mistralai Python | 2.x |
| PDF output | ReportLab | 4.4+ |
| Containers | Docker + Compose | Compose v2 |

**Blazor Server** over a separate SPA: single developer, one codebase, and the SignalR connection gives real-time progress updates during analysis without any polling.

**.NET 10** is the current LTS (November 2025, supported to 2028).

**Python 3.13**: Presidio requires Python 3.10–3.13. Don't use 3.14 until Presidio adds support.

**mistralai SDK v2** has breaking changes vs v1 — start on v2 directly to avoid a migration later.

---

## Components

### .NET app

Serves the Blazor UI and a lightweight REST API on the same process. When a user triggers an analysis, `AnalysisService` calls the Python service over HTTP, stores the result in SQLite, and notifies the Blazor component via SignalR.

Suggested project layout:

```
Finadoc.Web/
├── Pages/                   # Blazor pages (Login, Dashboard, Upload, Report, Admin)
├── Components/
├── Services/                # AnalysisService, AuditService, RetentionService, ...
├── Auth/
│   ├── IAuthProvider.cs
│   ├── LocalAuthProvider.cs
│   └── LdapsAuthProvider.cs # stub — throws NotImplementedException
├── Data/
│   ├── AppDbContext.cs
│   └── Migrations/
├── Models/                  # User, Group, Document, Analysis, AuditEvent
├── Workers/                 # RetentionCleanupWorker
└── appsettings.json
```

### Python AI service

FastAPI app — internal only. Four endpoints:

| Method | Path | |
|---|---|---|
| POST | `/analyze/pm` | Structured extraction |
| POST | `/analyze/rm` | Red flag detection |
| POST | `/analyze/regulatory` | Regulatory summary |
| GET | `/health` | Health check |

Each analysis endpoint receives a document path on the shared volume, the format, and some user context. It returns the path to the generated PDF and a machine-readable summary for the .NET app to store.

```json
// request
{
  "document_path": "/data/uploads/<uuid>/<filename>",
  "document_format": "pdf",
  "language": "auto",
  "output_path": "/data/outputs/<uuid>/",
  "user_context": { "user_id": "...", "groups": ["PM"] }
}

// response
{
  "status": "ok",
  "pdf_path": "/data/outputs/<uuid>/report.pdf",
  "summary": { ... },
  "warnings": [ ... ]
}
```

Project layout:

```
finadoc_ai/
├── main.py
├── pipeline/
│   ├── ingestion.py       # PDF / Excel → structured text
│   ├── masking.py         # Presidio
│   ├── llm.py             # Mistral client wrapper
│   ├── extraction.py      # PM logic
│   ├── red_flags.py       # RM logic
│   ├── summary.py         # Regulatory summary
│   ├── consistency.py     # Cross-source checks
│   └── pdf_output.py      # ReportLab
├── models/
│   └── schemas.py         # Pydantic models
└── config.py
```

### Database

SQLite — no separate service, just a file on disk, EF Core migrations handle the schema. Works fine for a single-tenant POC on a laptop.

| Table | Key columns |
|---|---|
| `Users` | `Id`, `Username`, `PasswordHash`, `IsAdmin`, `IsActive`, `CreatedAt` |
| `Groups` | `Id`, `Name` |
| `UserGroups` | `UserId`, `GroupId` |
| `Documents` | `Id`, `UserId`, `OriginalFileName`, `StoragePath`, `Format`, `Language`, `UploadedAt`, `ExpiresAt` |
| `Analyses` | `Id`, `DocumentId`, `GroupContext`, `Status`, `PdfPath`, `StartedAt`, `CompletedAt`, `ExpiresAt` |
| `AuditEvents` | `Id`, `Timestamp`, `UserId`, `Action`, `TargetType`, `TargetId`, `Outcome`, `Details` |

`RetentionCleanupWorker` runs daily and deletes rows where `ExpiresAt <= now`, then removes the corresponding files.

### File storage

```
/data/
├── uploads/<document-uuid>/<original-filename>
├── outputs/<analysis-uuid>/report.pdf
└── finadoc.db
```

Both services mount the same Docker volume. Without Docker on Windows, the root maps to `%APPDATA%\Finadoc\`.

---

## AI Pipeline

### Document ingestion

PyMuPDF (`fitz`) extracts text and page metadata from PDFs; pdfplumber handles structured tables. Output per page: text, any tables as DataFrames, page number. Excel files are read with pandas/openpyxl — one DataFrame per sheet.

If PyMuPDF finds no text layer, the pipeline rejects the file. Scanned PDFs are not supported.

### PII masking

[Microsoft Presidio](https://microsoft.github.io/presidio/) with spaCy NER models for Italian (`it_core_news_lg`) and English (`en_core_web_lg`).

1. `presidio-analyzer` detects entities: PERSON, ORG, IBAN, TAX_ID (codice fiscale), PHONE_NUMBER, EMAIL, LOCATION, DATE_TIME.
2. `presidio-anonymizer` replaces them with indexed placeholders — `Mario Rossi` → `<PERSON_1>`, `IT60X...` → `<IBAN_1>`.
3. The mapping lives in memory for the duration of the request, never written anywhere.
4. Masked text goes to Mistral.
5. After parsing the response, original values are restored for the final PDF.

A regex list would miss too much — Presidio is the right call here, and the masking needs to work reliably on real documents from day one.

### LLM calls

SDK: `mistralai` v2. Responses are requested in JSON mode (`response_format={"type": "json_object"}`).

| Task | Model |
|---|---|
| PM extraction | `mistral-small-latest` |
| RM red flags | `mistral-large-latest` |
| Regulatory summary | `mistral-small-latest` |

Red flag detection gets `mistral-large` because it involves multi-step numeric reasoning across different parts of the document. Extraction and summarization are well within `mistral-small`'s range.

System prompts are versioned template files per group (`prompts/PM/extraction_v1.txt`, `prompts/RM/red_flags_v1.txt`). Static reference documents — UCITS concentration limits, etc. — are embedded directly in the prompt. No vector DB in the POC.

Documents up to 10 pages fit comfortably within `mistral-small`'s 32K-token context. No chunking needed.

### Structured extraction (PM)

The prompt asks the model to return:

```json
{
  "asset_allocation": {
    "by_country_of_risk": [{ "country": "...", "pct": 0.0, "source_page": 0, "confidence": "high|medium|low" }],
    "by_rating":          [{ "rating": "...",   "pct": 0.0, "source_page": 0, "confidence": "..." }],
    "by_asset_class":     [{ "class": "Equity|Bond|Fund|Derivatives|Other", "pct": 0.0, "source_page": 0, "confidence": "..." }]
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

Fields with `confidence: "low"` are rendered with a warning badge in the PDF.

### Red flag detection (RM)

The model checks:
1. All percentage arrays sum to 100% (±0.1% tolerance).
2. Figures appearing in multiple sections are consistent.
3. UCITS/AIFMD concentration thresholds (e.g. max 10% per issuer) against the extracted data.
4. Deviations vs. prior period — only if a second document is provided (optional in the POC).

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

### Regulatory summary

```json
{
  "executive_summary": "...",
  "regulatory_references": ["MiFID II Art. 25", "AIFMD Art. 22"],
  "required_actions": [
    { "description": "...", "deadline": "2026-06-30", "source_page": 2 }
  ]
}
```

References are extracted from the text only — nothing inferred.

### Cross-source consistency check

After extraction, a deterministic Python check (no LLM) verifies that percentage arrays sum to 100% and that repeated figures across pages are consistent. Discrepancies are appended to the red flag list with severity `warning`.

### PDF output

ReportLab `platypus` engine.

| Section | Content |
|---|---|
| Header | Document name, analysis date, group, user |
| Extraction (PM) | Tables by category — source page and confidence badge per row |
| Red flags (RM) | Sorted critical → warning → info; source pages listed |
| Summary (regulatory) | Executive summary, regulatory references, deadlines table |
| Disclaimer | *"Generated automatically. Verify all data against the source document."* |

---

## Authentication

Local auth uses ASP.NET Core Identity (PBKDF2-SHA512). On first startup, if the `Users` table is empty, the app redirects to a setup page to create the initial admin.

The auth layer sits behind an `IAuthProvider` interface:

```csharp
Task<AuthResult> AuthenticateAsync(string username, string password);
Task<UserInfo?> GetUserInfoAsync(string username);
```

`LocalAuthProvider` wraps ASP.NET Core Identity and is the active implementation. `LdapsAuthProvider` takes a fully-typed `LdapsSettings` object (host, port, base DN, bind DN, TLS cert path) but stubs all methods with `NotImplementedException`. The switch lives in `appsettings.json` under `Auth:Provider` (`"Local"` or `"Ldaps"`).

When the LDAPs binding is eventually implemented, the library to use is `Novell.Directory.Ldap.NETStandard`, port 636, TLS enforced.

Session: HttpOnly, Secure cookie, 8-hour sliding expiration.

---

## Security

| | |
|---|---|
| **Password storage** | PBKDF2-SHA512 (ASP.NET Core Identity default) |
| **Session** | HttpOnly + Secure cookie, 8h sliding expiration |
| **Mistral API key** | `.env` (Docker) or `appsettings.Development.json`; excluded from git |
| **Python service** | Internal Docker network only — port 8000 not mapped to the host |
| **Data sent to Mistral** | Masked text only, over HTTPS (TLS 1.2+) |
| **Audit log** | Append-only; no delete endpoint exposed. Cleanup worker removes records older than 90 days. |
| **Data residency** | `api.mistral.ai` is EU-hosted. Verify Mistral's DPA before running on real documents. |

---

## Deployment

### Docker Compose (recommended)

```yaml
# docker-compose.yml
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

`.env` (not committed):
```
MISTRAL_API_KEY=your_key_here
```

```bash
docker compose up --build
# → http://localhost:8080
```

### Without Docker

```bash
# Terminal 1 — AI service
cd finadoc_ai
pip install -r requirements.txt
python -m spacy download it_core_news_lg
python -m spacy download en_core_web_lg
uvicorn main:app --port 8000

# Terminal 2 — .NET app
cd Finadoc.Web
dotnet run
```

---

## Mistral setup

### Account and API key

1. Go to [https://console.mistral.ai](https://console.mistral.ai) → Sign up → verify email.
2. Navigate to **API Keys** → **Create new key** → give it a name (e.g. `finadoc-poc`).
3. Copy the key immediately — it's only shown once.
4. Add it to `.env`:
   ```
   MISTRAL_API_KEY=<key>
   ```

### Data residency

Mistral processes data in the EU. Before using real documents, review [Mistral's data processing agreement](https://mistral.ai/terms) and confirm that `api.mistral.ai` routes to EU infrastructure. Request a signed DPA if needed for GDPR.

### Models

| Model | Use | Price (indicative, April 2026) |
|---|---|---|
| `mistral-small-latest` | PM extraction, regulatory summary | ~$0.10 / 1M input tokens |
| `mistral-large-latest` | RM red flag detection | ~$2.00 / 1M input tokens |

Start with `mistral-small` for all tasks, then switch red flag detection to `mistral-large` if the output quality isn't good enough.

### Python SDK

```bash
pip install "mistralai>=2.0"
```

SDK v2 has breaking changes vs v1. Start on v2.

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

## Build order

| Phase | Deliverable |
|---|---|
| P1 | Docker Compose skeleton — both services up, health check passing, shared volume mounted |
| P2 | Auth — login form, admin setup on first run, user/group CRUD |
| P3 | Upload — file storage, DB record, audit event |
| P4 | PM pipeline — PDF/Excel ingestion → masking → Mistral call → extraction JSON |
| P5 | PDF output — ReportLab report from extraction JSON, downloadable from the UI |
| P6 | RM pipeline — red flag analysis, severity classification, flags added to PDF |
| P7 | Regulatory summary — summary endpoint, output added to PDF |
| P8 | Retention & audit — 90-day cleanup worker, full event logging |
| P9 | Test documents — 3 fictitious fund documents with injected criticalities |
| P10 | Polish — Excel ingestion, confidence badges, cross-source check, disclaimer |
