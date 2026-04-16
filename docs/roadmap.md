# Finadoc — Roadmap

> POC scope. Single developer (.NET + Python). Target: running locally on a laptop.

---

## Overview

Ten phases, each with a clear deliverable and acceptance criteria. Each phase builds on the previous one — there are no parallel tracks in a one-person project. The goal is a working end-to-end system by P10, validated against three fictitious fund documents with injected criticalities.

---

## Phase 1 — Infrastructure skeleton ✅

**Deliverable:** Both services start, talk to each other, and share a volume.

- `docker-compose.yml` with `app` (.NET) and `ai` (Python/FastAPI) services
- Shared `finadoc_data` volume mounted at `/data` in both containers
- Python service: `GET /health` returns `{"status": "ok"}`
- .NET app: calls `/health` on startup and logs the result
- `.env` file with `MISTRAL_API_KEY` placeholder (excluded from git)
- `without-Docker` instructions validated locally

**Acceptance:** `docker compose up --build` → `http://localhost:8080` returns a page; health check passes.

---

## Phase 2 — Authentication ✅

**Deliverable:** Users can log in; the admin account is created on first run.

- Custom PBKDF2-SHA512 (`PasswordHasher`) — no ASP.NET Identity dependency
- First-run setup page: if `Users` table is empty, prompt for admin password before anything else
- Login/logout via Razor Pages (required for HttpOnly cookie issuance); password change via Blazor
- `IAuthProvider` interface + `LocalAuthProvider` (active) + `LdapsAuthProvider` (stub — all methods throw `NotImplementedException`)
- `Auth:Provider` switch in `appsettings.json`; `CookieAuthStateProvider` bridges HTTP auth into Blazor Server
- Admin UI: create/deactivate users, assign groups (PM, RM, or both)
- Session: HttpOnly + SameSite=Strict cookie, 8-hour sliding expiration
- EF Core migrations, SQLite at `/data/finadoc.db`; auto-applied on startup
- Dark enterprise Bootstrap 5 UI applied to all auth pages

Tables created: `Users`, `Groups`, `UserGroups`, `Documents`, `Analyses`, `AuditEvents` (full schema migrated in one shot).

**Acceptance:** Admin setup on first run; login/logout works; admin can create a PM user and an RM user; sessions expire correctly.

---

## Phase 2bis — Unit tests

**Deliverable:** Core business logic is covered by automated tests; CI can run them in a clean environment.

### .NET — `Finadoc.Web.Tests` (xUnit)

New project: `Finadoc.Web.Tests/Finadoc.Web.Tests.csproj`
Dependencies: `xunit`, `xunit.runner.visualstudio`, `Moq`, `Microsoft.EntityFrameworkCore.InMemory`, `Microsoft.AspNetCore.Mvc.Testing`

| Suite | What to test |
|---|---|
| `PasswordHasherTests` | `HashPassword` produces a `salt:hash` string; `VerifyPassword` returns `true` for correct password, `false` for wrong password, `false` for tampered hash; timing-safe comparison (no early exit on wrong length) |
| `LocalAuthProviderTests` | Returns `false` for unknown user; returns `false` for inactive user; returns `false` for wrong password; returns `true` + logs `login/success` audit event for valid credentials; `GetUserInfoAsync` maps groups correctly |
| `UserServiceTests` | `CreateAdminAsync` creates user with `IsAdmin = true` and no groups; `CreateUserAsync` creates `UserGroup` rows; `DeleteUserAsync` throws/no-ops when `userId == currentUserId` (self-delete guard); `UpdatePasswordAsync` updates hash and logs `password_changed` |

Use the EF Core InMemory provider to avoid SQLite I/O. Mock `AuditService` with Moq.

### Python — `finadoc_ai/tests/` (pytest)

Dependencies: `pytest`, `httpx` (async test client for FastAPI)

| Suite | What to test |
|---|---|
| `test_health.py` | `GET /health` returns `200` and `{"status": "ok"}` |
| `test_masking.py` | A text containing a known Italian name + IBAN is masked before it reaches the Mistral call; the placeholder mapping is not empty after masking; re-running masking on the same text produces consistent placeholders |
| `test_extraction_schema.py` | Valid extraction JSON passes the Pydantic model; missing required fields raise `ValidationError`; `confidence` values outside `{high, medium, low}` raise `ValidationError` |

Use `pytest-asyncio` for the FastAPI tests. Mock the `MistralClient` to avoid live API calls — inject a fixture that returns a canned JSON response.

### Project structure

```
Finadoc.Web.Tests/
  Finadoc.Web.Tests.csproj
  Auth/
    PasswordHasherTests.cs
    LocalAuthProviderTests.cs
  Services/
    UserServiceTests.cs

finadoc_ai/
  tests/
    __init__.py
    conftest.py          # FastAPI TestClient fixture, Mistral mock
    test_health.py
    test_masking.py
    test_extraction_schema.py
```

**Acceptance:** `dotnet test` passes all .NET suites; `pytest finadoc_ai/tests/` passes all Python suites; both run without network access (no live Mistral calls, no SQLite file).

---

## Phase 3 — Document upload ✅

**Deliverable:** Users can upload files; the system stores them and records the event.

- `DocumentService`: validates extension (`.pdf`/`.xlsx`), reads up to 20 MB, counts PDF pages via regex on raw bytes — rejects with a clear error if >10; stores file at `/data/uploads/<document-uuid>/<original-filename>`; creates a `Documents` record with `ExpiresAt = now + 90 days`; logs `document_upload` audit event (success or failure with reason)
- `Upload.razor`: `[Authorize]`-gated page with a styled drop-zone (invisible `InputFile` overlay for both click-to-browse and native drag-and-drop); success/error alerts; table of the user's own recent documents with PDF/XLSX format badges
- `Storage:DataDir` config key (default `/data`; overridden via `Storage__DataDir` env var in VS Code launch config for local development)
- `DocumentService` registered in DI; "Upload" link added to the nav bar
- `_Imports.razor` extended with `System.Security.Claims`, `Finadoc.Web.Models`, `Finadoc.Web.Services`

Note: `Documents` and `AuditEvents` tables were already present from P2's `InitialCreate` migration — no new migration needed.

**Acceptance:** Upload a PDF and an Excel file; both appear in `Documents`; `/data/uploads/` contains the files; audit log has one entry per upload; uploading a PDF with >10 pages is rejected before any file is written.

---

## Phase 4 — PM pipeline (extraction)

**Deliverable:** The AI service can process a factsheet and return structured extraction JSON.

- Python ingestion: PyMuPDF for PDF text + page metadata; pdfplumber for tables; pandas/openpyxl for Excel
- Reject file if PyMuPDF finds no text layer (scanned PDF not supported)
- Presidio masking with `it_core_news_lg` + `en_core_web_lg`; placeholder mapping held in memory only
- Mistral call: `mistral-small-latest`, `response_format={"type": "json_object"}`, prompt from `prompts/PM/extraction_v1.txt`
- Response parsed and validated against the extraction Pydantic schema (asset allocation by country/rating/asset class, performance, transactions, ESG)
- Each field carries `source_page` and `confidence` (`high` / `medium` / `low`)
- POST `/analyze/pm` endpoint returns `{"status": "ok", "pdf_path": "...", "summary": {...}, "warnings": [...]}`
- .NET `AnalysisService` calls the endpoint, stores the result path in `Analyses`, notifies the Blazor component via SignalR

Table created: `Analyses`.

**Acceptance:** Upload a test factsheet PDF → AI service returns valid extraction JSON with source pages and confidence values; no masked values appear in the JSON.

---

## Phase 5 — PDF output (PM report)

**Deliverable:** A downloadable PDF report is generated from PM extraction JSON.

- ReportLab `platypus` engine, `pdf_output.py`
- Report structure:
  - Header: document name, analysis date, group context, user
  - Asset allocation tables (by country, by rating, by asset class) — one row per entry, source page + confidence badge
  - Performance section
  - Transactions table
  - ESG section
  - Disclaimer: *"This report was generated automatically by an AI system. All data should be verified against the source document."*
- Low-confidence rows rendered with a visible warning badge
- PDF stored at `/data/outputs/<analysis-uuid>/report.pdf`
- Download button in the Blazor UI; audit event logged on download

**Acceptance:** End-to-end flow works — upload factsheet → PDF appears in the UI → download it → open it and verify tables, badges, and disclaimer are correct.

---

## Phase 6 — RM pipeline (red flag detection)

**Deliverable:** The AI service can analyze a financial report and return a prioritized list of red flags.

- POST `/analyze/rm` endpoint
- Mistral call: `mistral-large-latest`, prompt from `prompts/RM/red_flags_v1.txt`
- Model checks:
  - Percentage arrays sum to 100% (±0.1% tolerance)
  - Figures repeated across sections are consistent
  - UCITS/AIFMD concentration thresholds derivable from the document text
- Response schema: list of `{id, severity, description, affected_fields, source_pages, detail}`
- Severity levels: `critical` / `warning` / `info`
- Red flags added to the PDF report: sorted critical → warning → info, source pages listed per flag
- .NET stores result; audit event logged

**Acceptance:** Upload a test report with injected inconsistencies → PDF lists the injected red flags in the correct severity order with correct source page references.

---

## Phase 7 — Regulatory summary

**Deliverable:** The AI service can summarize a regulatory communication.

- POST `/analyze/regulatory` endpoint
- Mistral call: `mistral-small-latest`, prompt from `prompts/regulatory/summary_v1.txt`
- Response schema: `{executive_summary, regulatory_references[], required_actions[]}`
- Regulatory references extracted from text only — nothing inferred
- PDF sections: executive summary, regulatory references table, deadlines table (description, deadline date, source page)
- .NET stores result; audit event logged

**Acceptance:** Upload a test regulatory PDF (Consob/ESMA style) → PDF report contains a correct executive summary, references only provisions cited in the text, and lists any deadlines found.

---

## Phase 8 — Retention and audit trail

**Deliverable:** 90-day cleanup runs automatically; full audit trail is in place.

- `RetentionCleanupWorker` (IHostedService): runs daily, deletes `Documents` and `Analyses` rows where `ExpiresAt <= now`, then removes the corresponding files from disk
- Audit events complete: login, upload, analysis generated, PDF downloaded, document/analysis deleted, admin actions (user create/deactivate, group assignment)
- Each audit record: `timestamp`, `user_id`, `action`, `target_type`, `target_id`, `outcome`, `details`
- Audit log is append-only — no delete endpoint; the cleanup worker removes records older than 90 days
- Admin UI: view recent audit events (read-only)

**Acceptance:** Set `ExpiresAt` to the past for a test document → run the cleanup worker manually → document and analysis are gone from DB and disk; audit log has a deletion entry.

---

## Phase 9 — Test documents

**Deliverable:** Three fictitious fund documents validate the full pipeline end to end.

Three documents for a fictitious balanced fund (mixed strategy):

| Document | Type | Injected criticalities |
|---|---|---|
| `fund_factsheet_Q1.pdf` | PM factsheet | Asset class percentages sum to 101.3%; ESG rating appears with two different values on different pages |
| `fund_report_annual.pdf` | RM financial report | Country allocation doesn't match asset class allocation totals; one issuer exceeds 10% UCITS concentration limit |
| `esma_communication.pdf` | Regulatory summary | Contains references to MiFID II, AIFMD, and one deadline; one reference is implicit (should NOT appear in the output) |

Each document is generated programmatically (ReportLab or similar) so criticalities are precisely controlled and reproducible.

**Acceptance:** Running all three documents through the pipeline surfaces exactly the injected issues — no more, no less.

---

## Phase 10 — Polish and hardening

**Deliverable:** The POC is complete and ready for a demo.

- Excel ingestion path tested end-to-end (pandas/openpyxl → same pipeline as PDF)
- Cross-source consistency check: deterministic Python check (no LLM) verifies percentage sums and repeated figures; discrepancies appended to red flag list with severity `warning`
- Confidence badges visible and correct in all PM report tables
- Disclaimer present in every generated PDF
- Context selector in the UI: if a user belongs to both PM and RM groups, they choose which context to use before uploading
- Error handling: clear user-facing messages for unsupported file types, text-free PDFs, Mistral API errors, and oversized documents
- `without-Docker` startup instructions tested on a clean environment
- Mistral account setup instructions validated (see technical analysis)

**Acceptance:** A complete demo run covers all three test documents, all three use cases, admin setup, user management, and PDF download — with no unhandled errors.

---

## Deferred (post-POC)

These items are out of scope for the POC but should be addressed before production:

| Item | Notes |
|---|---|
| LDAPs binding | Interface and config model are ready; implement with `Novell.Directory.Ldap.NETStandard`, port 636, TLS enforced |
| Corporate PDF template | Header, footer, logo — template to be provided by the SGR |
| MFA | Not in scope for POC |
| Mobile UI | Web app is desktop-first; mobile deferred |
| Multi-tenant | POC is single-tenant; architecture does not need to change significantly |
| Per-group fine-tuning | Possibly in the future; current approach is prompt/RAG per group |
| Document comparison across periods | Requires document history — deferred until history is available |
| OCR for scanned PDFs | Pipeline currently rejects text-free PDFs |
| Semantic search | Not in scope |
| Notifications | Not in scope |
| Collaboration features | Not in scope |
| External system integrations | PMS, DMS, CRM, data providers — not in scope |
