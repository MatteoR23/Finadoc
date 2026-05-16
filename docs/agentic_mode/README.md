# FinLens Agentic Mode Plan

> Scope: POC extension. Agentic mode must remain bounded, auditable, and compliant with the existing FinLens constraints.

---

## 1. Goal

Agentic mode should make FinLens proactive inside a controlled analysis workflow:

- decide which approved analysis tools are useful for the uploaded document;
- create a short, explicit execution plan;
- run the selected tools in dependency order;
- keep an execution trace that a user or auditor can inspect;
- produce the same trusted outputs FinLens already targets: validated JSON and, from P5 onward, an English PDF report.

This is not an open-ended autonomous agent. It must not browse the web, call non-EU services, execute arbitrary code, write outside the configured storage buckets, or send unmasked document text to an LLM.

---

## 2. Functional Analysis

### Users

| User | Agentic benefit |
|---|---|
| Portfolio Manager | The system chooses PM extraction and relevant data quality checks from the document content. |
| Risk Manager | The system can combine red flag detection, data quality checks, and supporting extraction when useful. |
| Admin | Admin can enable or disable agentic mode and audit what the system decided to do. |

### User flow

1. User uploads a PDF or Excel document.
2. The upload page offers the existing context selector plus an optional **Agentic** mode.
3. If **Agentic** is selected, the user can optionally provide a short goal, for example `Find material inconsistencies and risk flags`.
4. .NET creates an `Analysis` record and enqueues a background job.
5. Python ingests the document, masks PII, asks Mistral for a JSON plan, validates the plan, and executes only allowlisted tools.
6. The UI shows step-level progress: `ingesting`, `masking`, `planning`, `executing:<tool>`, `generating`.
7. Artifacts are stored in MinIO and linked from the `Analysis` record:
   - `plan.json`
   - `trace.json`
   - tool result JSON files
   - `report.pdf` once PDF output is available.

### POC scope

In the first agentic phase, the agent can orchestrate only tools already implemented or scheduled in the roadmap:

| Tool | Availability | Notes |
|---|---|---|
| `pm_extract` | P4 | Existing PM extraction pipeline. |
| `dq_check` | P5 | Data quality flags. |
| `rm_red_flags` | P5 | Risk management analysis. |
| `regulatory_summary` | P6 | Regulatory summary. |
| `consistency_check` | P9 or earlier if moved forward | Deterministic Python check, no LLM. |
| `generate_report` | P5+ | ReportLab PDF generation. |

P4bis should implement the agentic foundation and prove it with `pm_extract`. P5-P7 then register the additional tools as they become available.

### Non-scope

- No semantic search or vector database in the POC.
- No long-running multi-document memory.
- No external web search.
- No fine-tuning.
- No user-to-agent chat beyond the optional bounded goal field.
- No tool creation by the model.
- No loops with unbounded retries.

---

## 3. Target Architecture

```
Browser
  |
  | upload + selected mode
  v
.NET / Blazor Server
  - auth and authorization
  - Analysis record
  - Hangfire job
  - audit trail
  - SignalR progress
  |
  | POST /analyze/agentic
  | X-Internal-Api-Key
  v
Python / FastAPI
  - ingest document
  - mask with Presidio
  - plan with Mistral JSON mode
  - validate plan with policy gate
  - call internal MCP server for allowlisted tools
  - create trace and artifacts
  |
  | MCP over internal Docker network
  | X-MCP-Client-Id + X-MCP-Secret-Id
  v
Python / MCP Server
  - exposes approved FinLens tools only
  - validates client credentials
  - executes typed tool handlers
  |
  | HTTPS, masked text only for tool LLM calls
  v
Mistral SaaS (EU)

MinIO
  finlens-documents/uploads...
  finlens-outputs/analyses/<analysis-id>/plan.json
  finlens-outputs/analyses/<analysis-id>/trace.json
  finlens-outputs/analyses/<analysis-id>/<tool>.json
  finlens-outputs/analyses/<analysis-id>/report.pdf
```

The agentic planner also calls Mistral directly from the AI service. Both planner calls and MCP-backed tool calls use masked text only.

### Component responsibilities

| Component | Responsibility |
|---|---|
| Blazor upload UI | Let the user select `Standard` or `Agentic`; show optional goal only for agentic mode. |
| `AnalysisService` | Persist mode, goal, expiry, and enqueue the correct job. |
| `AnalysisJob` | Call `/analyze/<context>` for standard mode or `/analyze/agentic` for agentic mode. |
| Progress callback | Accept richer steps and broadcast them with SignalR. |
| Agentic orchestrator | Own planning, policy validation, execution order, trace, and artifact upload. |
| MCP server | Expose approved FinLens tools over an internal Model Context Protocol boundary. |
| Tool registry | Register only approved internal functions with typed inputs and outputs, then expose them through MCP. |
| Policy gate | Reject unsafe or unauthorized plans before execution. |
| Report generator | Convert validated outputs into the final English PDF. |

---

## 4. Core Design

### Agentic execution model

The orchestrator is a bounded planner/executor:

1. **Ingest** the document with the existing ingestion pipeline.
2. **Mask** full document text with Presidio before any LLM call.
3. **Plan** with Mistral JSON mode using masked text, user goal, user groups, and tool descriptions.
4. **Validate** the returned plan against Pydantic schemas and policy rules.
5. **Execute** approved tools through the internal MCP server in a single pass.
6. **Validate** every tool output against existing Pydantic schemas.
7. **Assemble** a normalized result and execution trace.
8. **Generate** PDF when `generate_report` is available.

The model is allowed to choose a plan, not to perform direct side effects. Side effects are performed only by Python code that FinLens owns, behind an authenticated MCP server and a deterministic policy gate.

### Planner response schema

```json
{
  "objective": "Analyze the document for portfolio extraction and data quality issues.",
  "selected_workflows": ["PM", "DQ"],
  "steps": [
    {
      "id": "S1",
      "tool": "pm_extract",
      "reason": "The document contains fund allocation and performance tables.",
      "depends_on": [],
      "input_refs": ["masked_document"],
      "expected_output": "PMExtractionResult"
    },
    {
      "id": "S2",
      "tool": "dq_check",
      "reason": "Allocation tables should be checked for numerical consistency.",
      "depends_on": ["S1"],
      "input_refs": ["masked_document", "S1.output"],
      "expected_output": "DQResult"
    }
  ],
  "warnings": []
}
```

Pydantic models:

- `AgentPlan`
- `AgentStep`
- `AgentWarning`
- `AgentTrace`
- `AgentToolResult`
- `AgenticAnalyzeResponse`

### Tool registry

Each tool is registered with:

- stable name;
- required authorization context;
- input schema;
- output schema;
- timeout;
- retry policy;
- artifact name;
- implementation function.

Example:

```python
ToolDefinition(
    name="pm_extract",
    required_context="PM",
    input_model=PMToolInput,
    output_model=PMExtractionResult,
    timeout_seconds=120,
    max_retries=1,
    artifact_name="pm_extraction.json",
    handler=run_pm_extraction,
)
```

The planner sees only a short description of each tool, not the implementation.

### MCP server

Agentic mode should include an internal MCP server as the execution boundary for tools. The orchestrator validates the plan first, then calls MCP tools by name. The LLM never connects to MCP directly.

POC shape:

| Item | Decision |
|---|---|
| Process | Separate Python service, for example `finlens_mcp`, on the internal Docker network only. |
| Host exposure | No host port mapping. Only the AI service can reach it. |
| Protocol | MCP Streamable HTTP endpoint, for example `POST /mcp`. |
| Auth | Static service credential pair: `client_id` + `secret_id`. |
| Tools | `pm_extract` in P4bis; RM, DQ, regulatory, consistency, and report tools registered later. |
| Artifacts | MCP returns typed outputs to the orchestrator; the orchestrator owns artifact upload. |

Authentication headers:

```http
X-MCP-Client-Id: finlens-agentic
X-MCP-Secret-Id: <high-entropy-secret>
```

Configuration:

```env
MCP_BASE_URL=http://mcp:9000
MCP_CLIENT_ID=finlens-agentic
MCP_SECRET_ID=<openssl rand -hex 32>
```

`secret_id` is a shared service secret, not a database identifier. It must be generated with high entropy, excluded from git, loaded from environment variables, compared with a timing-safe comparison, and never written to `plan.json`, `trace.json`, audit details, logs, or PDF output.

MCP tool calls should be deterministic API calls from the orchestrator:

```json
{
  "tool": "pm_extract",
  "analysis_id": "uuid",
  "input_ref": "masked_document",
  "context": {
    "user_id": "...",
    "allowed_contexts": ["PM"]
  }
}
```

The MCP server must reject:

- missing or invalid `client_id`;
- missing or invalid `secret_id`;
- unknown tools;
- tools not enabled in the current phase;
- requests that include unmasked document text;
- requests containing external URLs, arbitrary file paths, shell commands, or storage targets outside FinLens buckets.

### Policy gate

The policy gate rejects a plan if:

- it references an unknown tool;
- it selects a tool the user is not authorized to run;
- it has cycles or dependencies on missing steps;
- it exceeds the configured step limit;
- it asks for raw unmasked text;
- it asks for an external URL, external storage target, shell command, or arbitrary file path;
- it requests a workflow outside POC scope;
- it attempts to persist the Presidio placeholder mapping;
- it tries to bypass MCP or call an MCP tool that is not registered and enabled.

Recommended POC limits:

| Limit | Value |
|---|---|
| Max steps | 6 |
| Max planner calls | 1 |
| Max retries per tool | 1 |
| Max document pages | Existing 10-page cap |
| Max optional user goal length | 500 characters |
| Max MCP tool call timeout | 120 seconds per tool in P4bis |

### Trace format

`trace.json` should be audit-friendly but must not contain sensitive text.

```json
{
  "analysis_id": "uuid",
  "mode": "Agentic",
  "started_at": "2026-05-16T10:00:00Z",
  "completed_at": "2026-05-16T10:01:30Z",
  "document": {
    "key": "documents/<document-id>/<filename>",
    "format": "pdf",
    "page_count": 4,
    "language": "it"
  },
  "masking": {
    "engine": "presidio",
    "placeholder_counts": {
      "PERSON": 2,
      "IBAN": 1
    }
  },
  "plan_s3_key": "analyses/<analysis-id>/plan.json",
  "steps": [
    {
      "id": "S1",
      "tool": "pm_extract",
      "status": "completed",
      "started_at": "2026-05-16T10:00:10Z",
      "completed_at": "2026-05-16T10:00:40Z",
      "artifact_s3_key": "analyses/<analysis-id>/pm_extraction.json"
    }
  ],
  "warnings": []
}
```

Do not store masked document text, unmasked document text, prompt bodies, raw LLM responses with sensitive text, or placeholder mappings in `trace.json`.

---

## 5. API Design

### Python endpoint

Add:

| Method | Path | Purpose |
|---|---|---|
| POST | `/analyze/agentic` | Plan and execute a bounded analysis workflow. |

Request extends the existing `AnalyzeRequest`:

```json
{
  "document_s3_key": "documents/<uuid>/<filename>",
  "documents_bucket": "finlens-documents",
  "document_format": "pdf",
  "language": "auto",
  "output_s3_prefix": "analyses/<analysis-id>/",
  "outputs_bucket": "finlens-outputs",
  "user_context": {
    "user_id": "...",
    "groups": ["PM", "RM"]
  },
  "analysis_id": "...",
  "callback_url": "http://app/internal/analysis/<id>/progress",
  "agentic": {
    "goal": "Find extraction values and material inconsistencies.",
    "allowed_contexts": ["PM", "RM", "DQ", "Regulatory"],
    "requested_output": "pdf"
  }
}
```

Response:

```json
{
  "status": "ok",
  "result_s3_key": "analyses/<analysis-id>/report.pdf",
  "summary": {
    "mode": "Agentic",
    "selected_workflows": ["PM", "DQ"],
    "plan_s3_key": "analyses/<analysis-id>/plan.json",
    "trace_s3_key": "analyses/<analysis-id>/trace.json",
    "tool_artifacts": [
      "analyses/<analysis-id>/pm_extraction.json",
      "analyses/<analysis-id>/data_quality.json"
    ]
  },
  "warnings": []
}
```

During P4bis, before PDF output is available, `result_s3_key` can point to `agentic_result.json`. P5 should split artifact storage explicitly with `ResultS3Key`, `ReportS3Key`, `PlanS3Key`, and `TraceS3Key` on the .NET side.

### MCP endpoint

Add an internal MCP service:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check for Docker and startup diagnostics. |
| POST | `/mcp` | MCP Streamable HTTP endpoint for authenticated tool calls. |

Required headers:

| Header | Value |
|---|---|
| `X-MCP-Client-Id` | Configured `MCP_CLIENT_ID`. |
| `X-MCP-Secret-Id` | Configured `MCP_SECRET_ID`. |

The MCP server should return `401` for missing credentials, `403` for invalid credentials, and `404` or structured MCP errors for unknown tools. It should not expose Swagger or debug endpoints outside development.

### .NET changes

Recommended `Analysis` additions:

| Column | Type | Notes |
|---|---|---|
| `Mode` | string | `Standard` or `Agentic`; default `Standard`. |
| `Goal` | string nullable | Optional bounded user goal. |
| `ResultS3Key` | string nullable | Validated JSON result or normalized agentic result. |
| `ReportS3Key` | string nullable | PDF report key. Replaces the current overloaded `PdfPath` semantics. |
| `PlanS3Key` | string nullable | Agent plan artifact. |
| `TraceS3Key` | string nullable | Execution trace artifact. |

Status values:

- `Queued`
- `Running`
- `Completed`
- `Failed`
- `Rejected`

Step values:

- `ingesting`
- `masking`
- `planning`
- `validating_plan`
- `executing:<tool-name>`
- `generating`
- `uploading`

Audit actions:

- `agentic_plan_created`
- `agentic_plan_rejected`
- `agentic_tool_started`
- `agentic_tool_completed`
- `agentic_tool_failed`
- `agentic_analysis_completed`

Audit details should include tool names, statuses, artifact keys, warning counts, and rejection reasons. They must not include document text, prompts, raw LLM responses, or placeholder mappings.

---

## 6. Python Implementation Plan

### Package layout

```
finlens_ai/
  pipeline/
    agentic/
      __init__.py
      orchestrator.py
      mcp_client.py
      planner.py
      policy.py
      state.py
      tools.py
      trace.py
  prompts/
    agentic/
      planner_v1.txt
  models/
    agentic.py

finlens_mcp/
  main.py
  auth.py
  tools.py
  schemas.py
```

### `models/agentic.py`

Define Pydantic schemas:

- `AgenticOptions`
- `AgentStep`
- `AgentPlan`
- `AgentPlanValidationResult`
- `AgentTraceStep`
- `AgentTrace`
- `AgenticSummary`

Validation rules should enforce:

- enum values for tool names;
- max string lengths;
- unique step ids;
- allowed dependency ids;
- no blank rationale;
- no external URLs in planner text fields.

### `planner.py`

Responsibilities:

- build a planner prompt from:
  - tool descriptions;
  - user groups;
  - optional user goal;
  - document metadata;
  - masked document excerpt or full masked text, still respecting the 10-page cap;
- call Mistral with JSON mode;
- validate the JSON into `AgentPlan`;
- return structured validation errors rather than free text.

Model:

- start with `mistral-small-latest`;
- only consider `mistral-large-latest` if plan quality is not enough for RM-heavy documents.

The planner prompt must explicitly say:

- choose only listed tools;
- return JSON only;
- do not request raw text;
- do not invent evidence;
- cite why each selected tool is relevant;
- prefer fewer steps when enough.

### `policy.py`

Responsibilities:

- enforce authorization;
- enforce tool allowlist;
- enforce DAG ordering;
- enforce step limit;
- enforce storage and privacy constraints;
- convert unsafe plans into a `Rejected` result.

The policy layer is deterministic and must run before any tool execution.

### `tools.py`

Register wrappers around existing functions and expose them through the MCP server:

- `run_pm_extraction`
- `run_rm_analysis`
- `run_dq_analysis`
- `run_regulatory_summary`
- `run_consistency_check`
- `generate_pdf`

Wrappers should have typed inputs and outputs. A wrapper can enrich outputs with artifact metadata, but it must not alter the validated schema returned by the underlying pipeline.

### `mcp_client.py`

Responsibilities:

- hold the configured MCP base URL;
- attach `X-MCP-Client-Id` and `X-MCP-Secret-Id` headers to every request;
- apply per-tool timeouts;
- translate MCP errors into sanitized agentic errors;
- never log credentials or request bodies containing document text.

### `finlens_mcp/auth.py`

Responsibilities:

- read `MCP_CLIENT_ID` and `MCP_SECRET_ID` from environment;
- reject missing configuration on startup;
- validate incoming headers with `hmac.compare_digest`;
- never echo credentials in errors or logs;
- optionally support `MCP_NEXT_SECRET_ID` later for secret rotation.

### `finlens_mcp/tools.py`

Responsibilities:

- register enabled tool handlers;
- enforce tool input schemas;
- call existing FinLens pipeline functions;
- return typed JSON results only;
- leave artifact upload to the orchestrator.

### `orchestrator.py`

Responsibilities:

1. Download the uploaded document from MinIO.
2. Ingest it.
3. Create a single masked document representation for planner and tools.
4. Ask planner for `AgentPlan`.
5. Upload `plan.json`.
6. Validate with policy gate.
7. Execute steps in dependency order through the MCP client.
8. Upload each step artifact.
9. Generate `trace.json`.
10. Return an `AnalyzeResponse`.

Implementation note: existing tool functions currently mask internally. P4bis should avoid duplicate and inconsistent masking by introducing a shared `MaskedDocument` object. Existing functions can keep their safety belt initially, but the target design is:

- ingestion happens once;
- masking happens once;
- all LLM tools receive the masked text;
- the Presidio mapping remains in memory and is discarded after PDF generation.

### `trace.py`

Trace writer should:

- record step timings and statuses;
- record artifact keys;
- record warning counts;
- omit sensitive text;
- omit prompts and raw completions;
- include model names and prompt template versions.

---

## 7. .NET Implementation Plan

### UI

Upload page changes:

- add a mode selector:
  - `Standard`
  - `Agentic`
- keep the existing context selector for standard mode;
- for agentic mode, compute allowed contexts from user groups:
  - PM group -> `PM`
  - RM group -> `RM`
  - DQ group -> `DQ`
  - all authenticated users -> `Regulatory` once P6 exists;
- add optional goal textarea, max 500 characters;
- show step progress from SignalR using existing progress infrastructure.

No conversational chat is needed for P4bis.

### Service and job layer

`AnalysisService.StartAnalysisAsync` should accept:

- `mode`;
- `groupContext` for standard mode;
- optional `goal`;
- computed allowed contexts for agentic mode.

`AnalysisJob` can either branch internally or delegate to a new `AgenticAnalysisJob`. For maintainability, prefer:

- `AnalysisJob` for standard workflows;
- `AgenticAnalysisJob` for `/analyze/agentic`.

Both jobs should share:

- progress notification helper;
- failure handling helper;
- audit helper.

### Configuration

Add service-to-service MCP settings to `.env`, Docker Compose, and application settings consumed by the Python AI service:

```env
MCP_BASE_URL=http://mcp:9000
MCP_CLIENT_ID=finlens-agentic
MCP_SECRET_ID=<openssl rand -hex 32>
```

The .NET app does not need to call MCP in P4bis. The AI orchestrator is the MCP client.

Docker Compose should add an internal `mcp` service with no host port mapping. The `ai` service receives `MCP_BASE_URL`, `MCP_CLIENT_ID`, and `MCP_SECRET_ID`; the `mcp` service receives `MCP_CLIENT_ID` and `MCP_SECRET_ID`.

### Storage

Store all agentic artifacts under:

```
analyses/<analysis-id>/
  plan.json
  trace.json
  agentic_result.json
  pm_extraction.json
  red_flags.json
  data_quality.json
  regulatory_summary.json
  report.pdf
```

### Results UI

For agentic analyses, results should show:

- selected workflows;
- status;
- current step;
- warning count;
- link to download PDF when available;
- admin-only link or modal to view plan/trace summaries.

The user-facing view should be concise. The trace is primarily for audit and debugging.

---

## 8. Security, Privacy, and Compliance

### Hard rules

- Ingestion must run before masking.
- Masking must run before every LLM call.
- Unmasked text must never be sent to Mistral.
- Presidio placeholder mappings stay in memory only.
- Prompt text, raw completions, and document text are not stored in audit events.
- Agentic mode cannot call any external service except Mistral SaaS over HTTPS.
- All external model calls remain Mistral EU.
- Tool execution is allowlisted and typed.
- Tool execution goes through the internal MCP server after plan validation.
- MCP authentication uses `client_id` and `secret_id` headers on every tool call.
- `secret_id` is never stored in the database, artifacts, logs, traces, prompts, or audit details.
- No arbitrary shell, file, network, or database tool is exposed to the planner.

### Authorization

The planner can only choose contexts the user is entitled to.

Examples:

- PM-only user: allowed `PM`; no `RM` or `DQ` if not assigned.
- RM-only user: allowed `RM`; optionally `DQ` only if the app grants DQ separately.
- PM+RM user: allowed `PM`, `RM`, and any other assigned context.
- Regulatory: available to all authenticated users after P6.

The server computes allowed contexts. The browser does not decide them.

### Audit

Every user-visible action remains auditable:

- upload;
- agentic analysis requested;
- plan created or rejected;
- tool execution completed or failed;
- report generated;
- report downloaded.

Retention remains 90 days for documents, analyses, and artifacts.

### MCP credential lifecycle

For the POC:

- generate `MCP_SECRET_ID` with `openssl rand -hex 32`;
- store it only in `.env` or deployment secrets;
- keep `.env` excluded from git;
- restart the AI and MCP services after rotation.

For production:

- use a secret manager;
- support `MCP_NEXT_SECRET_ID` for rolling rotation;
- consider mTLS between AI and MCP services;
- restrict network policy so only the AI service can reach the MCP port.

---

## 9. Error Handling

| Failure | System behavior |
|---|---|
| Planner returns invalid JSON | Mark analysis `Failed`; store sanitized validation error; audit failure. |
| Planner selects unauthorized tool | Mark analysis `Rejected`; store rejection reason; audit rejection. |
| Tool fails transiently | Retry once; if still failing, mark failed unless tool is optional. |
| Optional tool unavailable | Add warning and continue if final output still meets requested goal. |
| MCP credentials missing on startup | Fail startup for AI/MCP service; do not run in unauthenticated mode. |
| MCP credentials invalid during tool call | Mark analysis `Failed`; audit sanitized authentication failure. |
| MCP tool not found or disabled | Mark analysis `Rejected` if selected by planner; audit policy rejection. |
| PDF generation unavailable in P4bis | Return `agentic_result.json`; P5 adds PDF finalization. |
| Mistral API error | Fail with clear user-facing message; no raw provider payload shown. |
| Masking error | Fail closed before any LLM call. |

Fail closed is the default for privacy and authorization errors.

---

## 10. Testing Strategy

### Python tests

Add tests under `finlens_ai/tests/agentic/`:

| Suite | Coverage |
|---|---|
| `test_agentic_schemas.py` | Valid/invalid planner JSON; dependency validation; tool enum validation. |
| `test_agentic_policy.py` | Unknown tool, unauthorized context, cycles, too many steps, external URL rejection. |
| `test_agentic_orchestrator.py` | End-to-end with mocked Mistral and mocked tools; artifacts uploaded to fake S3. |
| `test_agentic_mcp_client.py` | MCP headers are attached; credentials are not logged; MCP errors are sanitized. |
| `test_mcp_auth.py` | Missing, wrong, and valid `client_id`/`secret_id` combinations return the expected status. |
| `test_agentic_masking.py` | Planner and tools receive masked text only. |
| `test_agentic_trace.py` | Trace omits document text, raw prompts, raw LLM output, and Presidio mapping. |

### .NET tests

Add or extend:

| Suite | Coverage |
|---|---|
| `AnalysisServiceTests` | Creates standard vs agentic analyses with correct mode, expiry, and audit expectations. |
| `AgenticAnalysisJobTests` | Calls `/analyze/agentic`, stores plan/trace/report keys, handles rejection and failure. |
| `UploadPage` component tests if available | Mode selector and goal validation. |
| `AuditServiceTests` | Agentic audit action details are sanitized. |

### Acceptance tests

P4bis acceptance:

1. Upload a PM factsheet with agentic mode.
2. Planner selects `pm_extract`.
3. Orchestrator executes `pm_extract` through the authenticated MCP server.
4. `plan.json`, `trace.json`, and `pm_extraction.json` are stored under `analyses/<id>/`.
5. UI shows progress through `planning` and `executing:pm_extract`.
6. Audit log contains plan and tool events.
7. Invalid MCP credentials fail closed.
8. No plan, trace, audit detail, or debug artifact contains unmasked PII, prompt text, credentials, or placeholder mappings.

P5+ acceptance:

1. Agentic mode can select PM + DQ for a factsheet with inconsistent allocations.
2. Agentic mode can select RM + DQ for a risk report.
3. Generated PDF lists selected workflows and warnings.
4. Unauthorized users cannot trigger RM or DQ through agentic mode.

---

## 11. Roadmap Integration

Add an intermediate phase after P4:

### Phase 4bis - Agentic mode foundation

Deliverable:

- agentic architecture documented;
- `/analyze/agentic` endpoint scaffolded;
- planner prompt and Pydantic schemas added;
- policy gate implemented;
- internal MCP server implemented with `client_id` + `secret_id` authentication;
- tool registry implemented with `pm_extract` exposed through MCP;
- .NET analysis mode, goal field, progress steps, and artifact columns added;
- sanitized plan and trace artifacts stored in MinIO;
- tests prove masking, authorization, and trace sanitization.

This phase should not complete RM, DQ, regulatory summary, or PDF output by itself. It creates the orchestration layer that later phases plug into.

Then update later phases:

- P5 registers RM, DQ, and PDF generation tools.
- P6 registers regulatory summary.
- P7 ensures retention and audit cleanup include plan and trace artifacts.
- P8/P9 test documents should include standard and agentic runs.

---

## 12. Implementation Checklist

1. Add Pydantic agentic schemas.
2. Add `prompts/agentic/planner_v1.txt`.
3. Add tool registry with `pm_extract`.
4. Add deterministic policy gate.
5. Add internal MCP server with authenticated `/mcp` endpoint.
6. Add MCP client in the AI orchestrator with `client_id` and `secret_id` headers.
7. Add orchestrator and `/analyze/agentic`.
8. Add `.NET` migration for mode and artifact keys.
9. Add `AgenticAnalysisJob`.
10. Extend upload UI with mode selector and optional goal.
11. Extend progress events with agentic step names.
12. Upload sanitized `plan.json` and `trace.json`.
13. Add Python tests for schema, policy, MCP auth, masking, trace, and orchestration.
14. Add .NET tests for service/job/audit behavior.
15. Update P5-P7 as new tools become available.

---

## 13. Open Decisions

| Decision | Recommended default |
|---|---|
| Is agentic mode available to every user? | Yes, but it can only run tools allowed by that user's groups. |
| Should the planner choose `mistral-large-latest`? | No for P4bis. Start with `mistral-small-latest`; use large only for RM execution. |
| Should agentic mode be the default? | No. Keep standard deterministic contexts as the default in the POC. |
| Should users edit the plan before execution? | No for POC. Show the plan after execution; add review later if needed. |
| Should failed optional tools block the whole analysis? | Only if they are required to satisfy the requested output. |

---

## 14. Success Criteria

Agentic mode is successful when:

- it reduces manual context selection without hiding what happened;
- it improves reuse of PM, RM, DQ, regulatory, consistency, and PDF components;
- every decision is represented in `plan.json` and `trace.json`;
- auditors can reconstruct which tools ran and why;
- privacy constraints are stronger than in standard mode, not weaker;
- a standard analysis path remains available for predictable demos and troubleshooting.
