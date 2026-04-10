# Finadoc — Functional Analysis

## 1. Product Vision

Finadoc is an AI-powered application for analyzing financial documents, designed for an Italian asset management company (SGR — *Società di Gestione del Risparmio*). Its goal is to support internal users in extracting, interpreting, and managing the information contained in complex financial documents, reducing manual work and increasing the reliability of analyses.

The POC focuses on three core use cases:
1. **Structured extraction** of fund factsheet data (asset allocation, performance, transactions, ESG).
2. **Red flag / anomaly detection** on fund and target-company financial reports.
3. **Summarization** of regulatory communications.

The output is always a **PDF report in English**, with mandatory citation of every extracted data point back to its source page.

---

> **Formatting note**: User answers (collected from MR — the user's initials) are reported in dedicated lines prefixed with `▶ MR:` in bold, to visually distinguish them from the questions.

---

## 2. Open Questions (round 1)

The questions below were used to define functional requirements. They are grouped by topic.

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

Based on the first round of answers, additional clarification was needed on a few points.

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

This section is consolidated based on the answers in sections 2 and 2bis. It describes the **POC scope**.

### 3.0 POC scope

Finadoc POC is a **web application installable locally (laptop)** that lets an authenticated user upload financial documents (PDF, Excel) of a fund, analyze them automatically through a European LLM (Mistral, in SaaS mode), and obtain as output a **PDF report in English** containing:

1. **Structured extraction** of fund factsheet data (asset allocation by country of risk, by rating, by security classification — Equity/Bond/Fund/Derivatives).
2. **Red flag / anomaly detection** on the extracted data (numerical inconsistencies, deviations vs prior period, breach of regulatory thresholds).
3. **Summarization** of regulatory communications.

Every extracted data point is **cited with reference to the source document page/paragraph**.

### 3.1 Actors and roles

| Actor | Description | Main use cases |
|---|---|---|
| **Admin** | Administrative user created on first run. Manages users, groups, configuration. | Login, user/group management, password change, LDAPs configuration. |
| **Portfolio Manager / Analyst (PM)** | User who analyzes factsheets and extracts asset allocation, performance, ESG, transactions. | Document upload, PM analysis, PDF report download. |
| **Risk Manager (RM)** | User who detects anomalies, red flags, deviations, threshold breaches. | Document upload, Risk analysis, PDF report download. |

**Notes on roles**:
- A user can belong to **multiple groups** (e.g. PM + RM).
- Each group has a **dedicated AI context**: specific prompts, separate knowledge base/RAG, own extraction templates. **No fine-tuning** in the POC (possible future evolution).
- Initial groups for the POC: **2** — PM and RM.

### 3.2 Main features

#### F1 — Authentication and user management
- F1.1 On first application start, an **admin user** is created with a password set during setup; the password can be changed later.
- F1.2 Login with **username + password** (internal form).
- F1.3 Support for **LDAPs** authentication against an external directory (configurable).
- F1.4 User and group management by the admin (CRUD).
- F1.5 A user can be assigned to **one or more groups** (PM, RM).
- F1.6 User password change.

> **Decision (§3.6)**: LDAPs is architecturally prepared in the POC — an abstraction layer/interface is defined, but the concrete LDAPs binding is deferred to a later version.

#### F2 — Document upload and management
- F2.1 Manual upload from the web UI (drag & drop or file picker).
- F2.2 Supported formats: **PDF** (native) and **Excel** (.xlsx).
- F2.3 Document languages: **Italian and English** (also multilingual within the same document).
- F2.4 Maximum size per document: **10 pages** (assumed limit ~10 MB).
- F2.5 No versioning: a re-uploaded document is treated as a new analysis.
- F2.6 Expected volumes at full rollout: **~100 documents / user / month**.

#### F3 — AI analysis
The analysis is **fully automatic** (no human review workflow), but quality is ensured by three parallel mechanisms:
- F3.1 **Mandatory source citation** for every extracted data point (page/section number of the source).
- F3.2 **Confidence flag** for each data point: below a configurable threshold the data is marked as *"to be verified"*.
- F3.3 **Cross-source check**: the same data extracted from multiple points in the document is compared; inconsistencies are flagged.

##### F3.A — Structured extraction (PM group)
- F3.A.1 Extraction of **asset allocation** by:
  - country of risk
  - rating
  - security classification: Equity / Bond / Fund / Derivatives
- F3.A.2 Extraction of **fund performance** (period return, benchmark, risk indicators if available).
- F3.A.3 Extraction of **transactions** for the period (purchases/sales, amounts).
- F3.A.4 Extraction of **ESG data** (rating, sustainable exposure, controversies if any).
- F3.A.5 Each extracted data point is normalized into a **common internal data model** (to enable comparisons and validations).

##### F3.B — Red flag / anomaly detection (RM group)
- F3.B.1 **Internal numerical inconsistencies** (totals that don't reconcile, percentages that don't sum to 100%, etc.).
- F3.B.2 **Significant deviations vs prior period** (requires at least two documents of the same fund to be meaningful; optional in the POC).
- F3.B.3 **Breach of regulatory thresholds** (concentration, leverage, UCITS/AIFMD limits where applicable and derivable from the document).
- F3.B.4 Each red flag is classified by **severity** (info / warning / critical) and accompanied by the source reference.

##### F3.C — Regulatory communication summarization
- F3.C.1 Generation of an **executive summary in English** of a regulatory communication (Consob, Bank of Italy, ESMA).
- F3.C.2 Identification of any **regulatory references** mentioned in the document (MiFID II, AIFMD, UCITS, DORA, AI Act) **only if explicitly present**.
- F3.C.3 Identification of **required actions** or **deadlines** mentioned, if any.

#### F4 — Output: PDF report
- F4.1 The output of every analysis is a **multi-page PDF** in **English**.
- F4.2 For the POC the **template is free-form** (no corporate header/footer). A formal template will be provided in a later version.
- F4.3 The PDF contains at least:
  - Header with metadata (source document name, analysis date, group/context used, user)
  - Extracted data section (with source citation and confidence flags)
  - Red flags section (for RM analyses)
  - Summary section (for analyses on regulatory communications)
  - Disclaimer
- F4.4 The PDF report is **downloadable** from the UI.

#### F5 — Audit trail
- F5.1 Tracking of all the following events: **login**, **document upload**, **analysis generated**, **PDF download**, **document/analysis deletion**, **administrative events** (user/group create/update).
- F5.2 Each event records: timestamp, user, action, target object, outcome.
- F5.3 Audit log retention: **90 days**.

#### F6 — Retention and data lifecycle
- F6.1 Uploaded documents and generated analyses are kept for **90 days**, then automatically deleted (both documents and analyses).
- F6.2 Users can manually delete their own documents/analyses earlier.

#### F7 — Privacy and protection of sensitive data
- F7.1 Before content is sent to the external LLM (Mistral SaaS), a **masking/pseudonymization** step is applied to personal and potentially sensitive data (client names, tax IDs, IBANs, etc.).
- F7.2 Masking is reversible on the application side for final presentation to the authorized user (where applicable).

### 3.3 User flows

#### Flow A — First start (Admin)
1. The admin starts the application for the first time.
2. A setup screen prompts to set the admin password.
3. The admin logs in and configures: users, groups (PM, RM), assignments, optional LDAPs connection.

#### Flow B — PM analysis on a factsheet
1. The PM user logs in.
2. Selects the **PM** context (if member of multiple groups).
3. Uploads a factsheet PDF/Excel.
4. The app runs: pre-processing → masking → call to Mistral → structured extraction → cross-source check → PDF generation.
5. The user previews and downloads the PDF.

#### Flow C — Risk analysis on a fund or target-company report
1. The RM user logs in.
2. Selects the **RM** context.
3. Uploads a financial report.
4. The app runs red flag analysis.
5. PDF output with anomalies classified by severity and source citation.

#### Flow D — Regulatory communication summary
1. The user uploads a regulatory document.
2. The app generates an English summary, with the list of cited regulatory references and any deadlines.
3. PDF output.

### 3.4 Non-functional requirements

| Category | Requirement |
|---|---|
| **Architecture** | Backend API in **.NET Core**; AI pipeline / LLM orchestration in **Python**; desktop-first web app. |
| **LLM** | **Mistral** in **SaaS API** mode (hosted in EU). Account to be created; setup instructions included in the technical documentation. |
| **Localization** | Bilingual UI IT/EN (at least EN guaranteed in the POC); output always in English. |
| **Tenancy** | Single-tenant in the POC (one SGR only). |
| **POC deployment** | Runnable on a **local laptop** (Linux/Windows). Containerization optional but recommended (Docker Compose). |
| **Data residency** | All data stays in EU/Italy. No external non-EU services. |
| **Security** | Standard password hashing (bcrypt/argon2), TLS for LDAPs, secret management for the Mistral API key. |
| **Cost** | Minimize LLM cost (pick the cheapest Mistral model compatible with sufficient quality — e.g. `mistral-small`/`mistral-medium`). |
| **Compliance** | Traceability via audit trail (90 days). Explainability via source citation and confidence flags. AI Act: likely classified as a limited-risk system. |
| **Accessibility** | Not a constraint for the POC. |
| **Mobile** | Out of scope for the POC, planned as a future evolution. |
| **Performance** | Average analysis time target < 60 seconds per document ≤ 10 pages (indicative, to be validated in POC). |

### 3.5 Out of scope (POC)

Features **excluded** from the POC, that may be reconsidered in later phases:

- Conversational Q&A on documents.
- Automatic document type classification.
- Semantic search over document archive.
- Comparison of the **same fund across different periods** (excluded because *"no history available"*) and **peer comparison** of different funds → **deferred to post-POC**.
- Comparison of different versions of the same document (draft vs final).
- Analysis versioning.
- Human-in-the-loop review/approval workflow.
- Notifications / alerts.
- Collaboration (comments, annotations, sharing).
- Integrations with external systems (PMS, DMS, CRM, data providers, corporate SSO).
- Mobile app.
- Multi-tenant.
- Corporate PDF template.
- Per-group model fine-tuning.
- OCR for scanned documents (assumption: input PDFs are native/text-based).

### 3.6 Closed open points

All points resolved before the technical analysis.

1. **LDAPs in the POC**: full implementation already in the POC, or only architectural readiness?
   **▶ MR: Architectural readiness** → F1.3 implemented as an abstraction layer/interface; concrete LDAPs binding deferred to a later version.
2. **Masking/pseudonymization**: full or simplified implementation?
   **▶ MR: Full implementation** → even though test documents are fictitious, the masking component must be production-ready.
3. **Fictitious test documents**: Claude will generate 3 documents of a fictitious balanced fund with exposure by country of risk / rating / asset class, with deliberately injected criticalities to test red flag detection.
   **▶ MR: YES**
4. **POC scope**: the POC covers **all three use cases** (factsheet PM extraction, red flag RM detection, regulatory summary) — not only the factsheet.
   **▶ MR: all three**
