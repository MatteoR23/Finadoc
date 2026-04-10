# Finadoc — Functional Analysis

## 1. Product Vision

Finadoc is an AI tool for analyzing financial documents, built for an Italian SGR (*Società di Gestione del Risparmio*). The core problem it addresses is simple: reading fund documents carefully enough to catch every number, every inconsistency, every regulatory threshold breach — without making mistakes. That takes a lot of time and attention, and errors still happen.

The POC covers three use cases:
1. Structured extraction from fund factsheets — asset allocation, performance, transactions, ESG.
2. Red flag and anomaly detection on fund and target-company reports.
3. Summarization of regulatory communications (Consob, Bank of Italy, ESMA).

Output is always a PDF report in English. Every extracted value references the page it came from.

---

> **Formatting note**: Answers from MR are shown on dedicated lines prefixed with `▶ MR:`.

---

## 2. Open Questions (round 1)

### 2.1 Business context and users

1. **Type of SGR**: which kind of SGR are we talking about (UCITS open-ended funds, AIFs, real estate, private equity, private debt, mixed)?
   - **▶ MR:** mixed.

2. **End users**: who will use the app daily?
   - Portfolio managers / investment analysts → **▶ MR: YES**
   - Compliance / risk management → **▶ MR: YES**
   - Middle/back office → **▶ MR: NO**
   - Legal → **▶ MR: NO**
   - Sales / investor relations → **▶ MR: NO**

3. **Number of users** expected at launch and at full rollout?
   - **▶ MR:** initially just one (me), about a hundred at full rollout.

4. **Main pain point** to solve today?
   - **▶ MR:** reading the data without making mistakes.

5. **Success metrics**: how will we measure if Finadoc works?
   - **▶ MR:** both reduced errors and time saved.

### 2.2 Document types

6. **Which document types** should we analyze?
   - Prospectuses / KIID / KID PRIIPs → **▶ MR: NO**
   - Fund annual/semi-annual reports → **▶ MR: YES**
   - Factsheets and periodic reports → **▶ MR: YES**
   - Contracts (depositaries, delegated managers, counterparties) → **▶ MR: NO**
   - External research reports (brokers, rating agencies) → **▶ MR: NO**
   - Regulatory communications (Consob, Bank of Italy, ESMA) → **▶ MR: YES**
   - Term sheets / investment documentation (PE/PD/RE) → **▶ MR: YES**
   - Due diligence / data room → **▶ MR: NO**
   - Target/portfolio company financial statements → **▶ MR: YES**

7. **Formats**: PDF (native and scanned?), Word, Excel, email, images? Is OCR needed?
   - **▶ MR:** mainly Excel and PDF.

8. **Languages**: Italian, English, others? Multilingual documents?
   - **▶ MR:** English and Italian.

9. **Volumes**: how many documents per day/month? Average and maximum size (pages)?
   - **▶ MR:** about a hundred per user per month, max 10 pages per report.

10. **Document sources**: email, manual upload, network folders, external portals, provider APIs (Bloomberg, Morningstar)?
    - **▶ MR:** manual upload into the application.

### 2.3 AI analysis features

11. **What should the AI do on documents**?
    - **Summarization** (executive summary, section summaries) → **▶ MR: YES (summary)**
    - **Structured data extraction** (ISIN, fees, asset allocation, performance, contractual clauses) → **▶ MR: YES — Asset Allocation, Transactions, Performance, ESG**
    - **Conversational Q&A** on a document or corpus → **▶ MR: NO**
    - **Automatic classification** (document type, topic, relevance) → **▶ MR: NO**
    - **Document comparison** (different versions, similar funds) → **▶ MR: YES**
    - **Anomaly / red flag detection** (unusual clauses, inconsistencies, risks) → **▶ MR: YES**
    - **Translation** → *(not answered)*
    - **Semantic search** over a document archive → **▶ MR: NO**

12. **Expected output**: downloadable reports (PDF/Excel), web dashboard, email alerts, export to other systems?
    - **▶ MR:** PDF analysis.

13. **Automation level**: AI proposes and user validates, or fully automatic output? Review workflow needed?
    - **▶ MR:** fully automatic output.

14. **Source citation**: must the AI always cite the page/paragraph where information comes from?
    - **▶ MR:** yes.

15. **History and versioning**: do we need to keep track of previous analyses on the same document, compare versions, etc.?
    - **▶ MR:** no.

### 2.4 Integration with existing systems

16. **Existing systems** to integrate with? (PMS, DMS, CRM, data providers, compliance/risk)
    - **▶ MR:** no integration, documents are standalone. **Section skipped entirely.**

17. **Single Sign-On**: integration with Active Directory / Azure AD / other IdP? — *skipped*
18. **Data export/import**: required formats? (Excel, CSV, JSON, XBRL?) — *skipped*

### 2.5 Security, compliance and data

19. **Where can data reside**? Public cloud, private cloud, on-premise? Country constraints?
    - **▶ MR:** EU/Italy.

20. **LLM**: SaaS models (OpenAI, Anthropic, Google) or self-hosted/sovereign model required?
    - **▶ MR:** preferably European (Mistral).

21. **Sensitive data**: do documents contain personal data (GDPR), price sensitive / MNPI information, client data?
    - **▶ MR:** yes.

22. **Audit trail**: full log of who read/analyzed what, retained for how long?
    - **▶ MR:** yes, but retention is only 90 days.

23. **Applicable regulations**: MiFID II, AIFMD, UCITS, Consob, Bank of Italy, DORA, AI Act — specific requirements?
    - **▶ MR:** to be derived from the document, or if explicitly requested by the user.

24. **Retention**: how long should documents and analyses be kept?
    - **▶ MR:** 90 days.

25. **Roles and permissions**: do we need different profiles with visibility on subsets of documents (e.g. by fund, by team)?
    - **▶ MR:** yes, each group will use a different model context and training.

### 2.6 User experience

26. **Interface type**: desktop-first web app? Mobile needed? Use in meetings / client-facing?
    - **▶ MR:** web app, with possible future mobile implementation.

27. **Preferred interaction style**: conversational chat, structured forms, dashboards, or a mix?
    - **▶ MR:** a mix.

28. **Collaboration**: do multiple users need to comment/annotate the same document or share analyses?
    - **▶ MR:** no.

29. **Notifications**: alerts needed (e.g. "an updated prospectus for fund X has arrived")?
    - **▶ MR:** no.

### 2.7 Project constraints

30. **Timeline**: any deadline or expected MVP date?
    - **▶ MR:** no.

31. **Budget**: constraints affecting tech choices (e.g. LLM token costs)?
    - **▶ MR:** prefer the cheapest option that maintains sufficient quality.

32. **Team**: who will build and maintain the app? Internal skills available?
    - **▶ MR:** for now just me. Skills in .NET Core and Python.

33. **Approach**: MVP on a single high-value use case, or broader/shallower coverage?
    - **▶ MR:** for now we limit ourselves to a POC.

---

## 2bis. Follow-up Questions (round 2)

### A. Output trust (important tension)

The main pain point is *"reading the data without making mistakes"* and the success metrics are *"reduced errors + time saved"*. At the same time, the requested automation level is *"fully automatic output, no review workflow"*.

A1. **How do we reconcile "zero errors" with "zero review"?**
   - (a) Automatic output with **mandatory source citation** (page/paragraph), so the user can spot-check without a formal workflow.
     - **▶ MR:** YES
   - (b) Automatic output with **confidence flags**: below a certain threshold the data is marked as "to be verified".
     - **▶ MR:** YES
   - (c) Automatic output with **cross-source check**: the same data extracted from multiple parts of the document, flagged if inconsistent.
     - **▶ MR:** YES
   - (d) A combination.
     - **▶ MR:** NO

### B. Roles, permissions and "different model training"

B1. **What does "different training" mean**?
   - (a) **Different prompts/instructions** per group (simpler, no real training).
     - **▶ MR:** the model adapts to the group, so the context changes
   - (b) **Separate knowledge base / RAG** per group.
     - **▶ MR:** YES
   - (c) **Fine-tuning** of a model per group (complex and expensive).
     - **▶ MR:** NO, but possibly in the future
   - (d) **Different extraction templates** per group (e.g. PM extracts asset allocation, Compliance extracts regulatory references).
     - **▶ MR:** YES

B2. **How many groups** initially?
   - **▶ MR:** PM and Risk Management.

B3. **Can a user belong to multiple groups** or only one?
   - **▶ MR:** YES (multiple groups).

### C. AI use cases — details

C1. **Data extraction**: concrete fields per area for the POC?
   - **▶ MR:** we will create 3 fictitious documents of an imaginary balanced fund with exposures by country of risk, by rating, by security classification (Equity, Bond, Fund, Derivatives). I'll inject some criticalities.

C2. **Document comparison**: what kind?
   - (a) Same fund, different periods (e.g. Q1 vs Q2 factsheet) → **▶ MR: YES**
   - (b) Different funds, same period (peer comparison) → **▶ MR: YES**
   - (c) Different versions of the same document (e.g. draft vs final) → **▶ MR: NO**
   - (d) All of the above → **▶ MR: NO**

C3. **Red flags / anomalies**: what counts as a red flag?
   - Internal numerical inconsistencies (totals that don't add up) → **▶ MR: YES**
   - Significant deviations vs the previous period → **▶ MR: YES**
   - Breach of regulatory thresholds (concentration, leverage) → **▶ MR: YES**
   - Presence of specific terms/clauses → **▶ MR: NO**
   - Other → **▶ MR: NO**

### D. PDF output

D1. **Template**: must the output PDF follow a precise corporate template (header, footer, logo, fixed layout) or is it free-form?
   - **▶ MR:** free-form for the POC, a template will be provided in future.

D2. **Structure**: single PDF per analyzed document, or aggregated PDF combining multiple documents?
   - **▶ MR:** multi-page.

D3. **Output language**: Italian, English, or same as input?
   - **▶ MR:** English.

### E. Data and lifecycle

E1. **90-day retention**: after 90 days are we deleting **documents**, **analyses**, or **both**?
   - **▶ MR:** both.

E2. **Sensitive data (GDPR / MNPI)**: do we need **masking** or **pseudonymization** before sending content to the LLM (even if European)?
   - **▶ MR:** yes.

E3. **Audit trail**: which events to log? (login, upload, analysis generated, PDF download, deletion)
   - **▶ MR:** all of the above.

### F. Authentication and multi-tenancy

F1. No corporate SSO: do users authenticate with **username+password** internal to the app? MFA needed?
   - **▶ MR:** for the POC, username and password. On first run an admin user will be created (password set at setup, then changeable). It must support **LDAPs**.

F2. Are the 100 users at full rollout all from the **same SGR** (single-tenant) or will the app potentially serve **multiple SGRs** (multi-tenant)?
   - **▶ MR:** for the POC, only one (single-tenant).

### G. POC — priorities

G1. Which use case to focus on for the POC?
   - (a) **Structured extraction + PDF output** on factsheets/periodic reports → **▶ MR: YES (Factsheet)**
   - (b) **Document comparison** (same fund, different periods) → **▶ MR: NO, no history available**
   - (c) **Red flags / anomalies** on fund or target-company reports → **▶ MR: YES**
   - (d) **Summary** of regulatory communications → **▶ MR: YES**

G2. **How many real example documents** (anonymized or test) can you provide to tune the POC?
   - **▶ MR:** 2 or 3.

### H. Stack and deployment

H1. .NET Core + Python skills: backend preference for the POC?
   - **▶ MR:** .NET for API/webapp, Python for AI and pipeline.

H2. **Where will the POC run**? Local laptop, on-prem VM, EU cloud (OVHcloud, Scaleway, Azure EU)?
   - **▶ MR:** local laptop.

H3. **Mistral**: existing account / API key, or to be created? OK to use **Mistral SaaS API** (hosted in EU) or self-hosting required from POC?
   - **▶ MR:** no account yet, needs to be created. Include the instructions.

---

## 3. Functional Requirements

### 3.0 Scope

The POC is a web app that runs locally on a laptop. A logged-in user uploads a PDF or Excel file and receives a multi-page PDF report in English — automatically, without any review step in between. The analysis calls Mistral (EU-hosted SaaS API) and applies three quality checks: mandatory source citation, per-value confidence flags, and cross-source consistency verification.

Three use cases are in scope: structured extraction (PM group), red flag detection (RM group), and regulatory summarization.

### 3.1 Roles

| Role | Description |
|---|---|
| **Admin** | Created on first run. Manages users, groups, and application configuration. |
| **Portfolio Manager (PM)** | Analyzes factsheets: asset allocation, performance, ESG, transactions. |
| **Risk Manager (RM)** | Detects anomalies: flags numerical inconsistencies, threshold breaches, and deviations vs. prior period. |

Users can belong to both groups simultaneously. Each group has a distinct AI context: its own system prompts, knowledge base, and extraction templates. No fine-tuning in the POC.

### 3.2 Features

#### Authentication

On first startup, if no admin exists, a setup screen collects the initial admin password. After that, login is username + password. Users can change their own password; the admin manages accounts and group assignments.

LDAPs is part of the design — the auth layer uses an `IAuthProvider` interface, and the configuration model (host, port, base DN, bind credentials, TLS certificate) is fully defined. The actual directory binding is not implemented in the POC; the LDAPs provider stubs the interface methods.

#### Document upload

Manual upload via drag & drop or file picker. Accepted formats: PDF (native, text-based) and Excel (.xlsx). Documents can be Italian, English, or mixed. Hard limit: 10 pages per document. Re-uploading the same file creates a new analysis — no versioning.

#### AI analysis

After upload, the pipeline runs without user intervention: text extraction → PII masking → Mistral call → response parsing → consistency check → PDF generation.

Three quality mechanisms run on every analysis:
- Each extracted value cites its source page or section.
- Each value carries a confidence flag (high / medium / low); anything below threshold is marked "to be verified" in the report.
- Values that appear in more than one part of the document are compared; discrepancies surface as warnings.

**PM — Structured extraction**

Targets factsheets and periodic reports. Extracts:
- Asset allocation by country of risk, by rating, and by asset class (Equity / Bond / Fund / Derivatives)
- Fund performance: period return, benchmark return, risk indicators where present
- Transactions: type (buy/sell), instrument, ISIN, amount, currency, date
- ESG: rating, sustainable exposure %, any controversies mentioned

All fields are normalized into a shared internal data model.

**RM — Red flag detection**

Targets fund and target-company financial reports. Flags:
- Percentage breakdowns that don't sum to 100% (tolerance: ±0.1%)
- Values that appear inconsistently across sections of the same document
- Breaches of UCITS/AIFMD concentration or leverage thresholds, where derivable from the document text
- Material deviations vs. the prior period — requires two documents; treated as optional in the POC

Each flag carries a severity (info / warning / critical) and a source page reference.

**Regulatory summary**

For communications from Consob, Bank of Italy, or ESMA. Produces:
- Executive summary in English
- List of regulatory references explicitly cited in the text (MiFID II, AIFMD, UCITS, DORA, AI Act) — nothing inferred
- Any required actions or deadlines mentioned

#### Output: PDF report

Every analysis produces a multi-page PDF in English. Free-form layout in the POC (no corporate template). The PDF contains:
- Header: document name, analysis date, group context, user
- Extraction tables with source page and confidence badge on each row (PM)
- Red flags sorted by severity, critical first (RM)
- Executive summary, regulatory references, deadlines table (regulatory)
- Disclaimer: *"This report was generated automatically by an AI system. All data should be verified against the source document."*

The report is downloadable from the UI.

#### Audit trail

Events logged: login, document upload, analysis generated, PDF downloaded, document/analysis deleted, admin actions (user/group changes). Each record contains timestamp, user ID, action, target, and outcome. Retention: 90 days.

#### Data lifecycle

Documents and analyses are automatically deleted after 90 days — both the stored file and the database record. Users can delete their own data earlier. Cleanup runs as a daily background job.

#### PII masking

Before any text is sent to Mistral, the pipeline detects and replaces sensitive entities (names, IBANs, tax IDs, phone numbers, etc.) with indexed placeholders. The mapping lives in memory only — never written to disk or sent externally. For the final PDF, original values are restored where the user is authorized to see them. Full Presidio-based implementation, not a regex shortcut — the masking has to be reliable on real documents from day one.

### 3.3 User flows

**First startup — admin setup**
1. App starts; no users in DB → setup screen collects admin password.
2. Admin logs in, creates users, assigns groups, optionally configures the LDAPs connection.

**PM analysis on a factsheet**
1. User logs in, selects PM context (if member of both groups).
2. Uploads a PDF or Excel factsheet.
3. Pipeline runs; user waits for completion.
4. Report appears in the UI; user previews and downloads the PDF.

**RM analysis on a fund or target-company report**
1. User logs in, selects RM context.
2. Uploads the financial report.
3. Pipeline runs red flag analysis.
4. PDF output lists anomalies sorted by severity, each with source reference.

**Regulatory document summary**
1. User uploads a regulatory communication.
2. App returns a PDF with the executive summary, referenced regulatory provisions, and any deadlines found in the text.

### 3.4 Non-functional requirements

| | |
|---|---|
| **Stack** | .NET 10 (web app + API), Python 3.13 (AI pipeline), Mistral SaaS (EU) |
| **Deployment** | Local laptop, Linux or Windows. Docker Compose recommended. |
| **Data residency** | EU/Italy only. No non-EU external services. |
| **Tenancy** | Single-tenant (one SGR). |
| **UI** | Desktop-first web app. No mobile in the POC. |
| **Auth** | Local username/password. LDAPs interface defined, binding not implemented in POC. No MFA. |
| **Security** | PBKDF2 password hashing, TLS for LDAPs, secrets managed via `.env`. |
| **Cost** | Minimize token spend — `mistral-small` as default, `mistral-large` only where quality requires it. |
| **Retention** | 90 days for documents, analyses, and audit logs. |
| **Performance** | Analysis target: under 60 seconds for a 10-page document (indicative, to be validated). |
| **Compliance** | Audit trail for traceability. Source citation + confidence flags for explainability. AI Act: limited-risk classification assumed. |

### 3.5 Out of scope

- Conversational Q&A on documents
- Automatic document type classification
- Semantic search
- Document comparison across periods or across funds (no historical data available)
- Analysis versioning
- Human-in-the-loop review workflow
- Notifications
- Collaboration (comments, annotations, sharing)
- Integrations with PMS, DMS, CRM, data providers, or SSO
- Mobile app
- Multi-tenant
- Corporate PDF template
- Per-group model fine-tuning
- OCR (input PDFs assumed to be native/text-based)

### 3.6 Closed open points

1. **LDAPs**: architectural readiness only — stub implementation with full configuration model; actual directory binding deferred.
2. **Masking**: full Presidio-based implementation, not a simplified regex approach.
3. **Test documents**: 3 fictitious fund documents will be generated with deliberately injected criticalities to validate the POC end to end.
4. **POC scope**: all three use cases are in scope — extraction, red flags, and regulatory summary.
