SIH 2026  |  TECHNICAL REQUIREMENTS DOCUMENT

AICTE FlowWise

Architecture for AI-Powered Approval Workflow Automation, Compliance Monitoring and Alert Management

Version 3.0  |  30 October 2026  |  SIH solution architecture

| Scope note. This is a proposed architecture for the Smart India Hackathon. Workflow rules, timelines, roles and integrations are configuration, not code, and must be validated against the current AICTE Approval Process Handbook. External AICTE integrations are not assumed; adapters are mocked in the demo and labelled. |
| --- |

| Item | Detail |
| --- | --- |
| Document | Technical Requirements Document (TRD) |
| Version | 3.0 - supersedes v2.0; pairs with PRD v3.0 |
| Status | SIH prototype-ready architecture draft |
| Product | AICTE FlowWise |

### What changed from v2.0

| Area | v2.0 | v3.0 |
| --- | --- | --- |
| Prototype profile | Production-style stack only (Celery, Redis, MinIO, MailHog, Docker) | New section 3A: a runnable profile (SQLite, in-process scheduler, local storage, outbox page). The production stack stays the documented target |
| Windows-friendly libraries | WeasyPrint and Celery, which are awkward on Windows | ReportLab and APScheduler in the prototype profile |
| Template JSON example | No start marker; EVC had no path to DONE, so it failed its own validator | Fixed. Adds in-stage events with holder_after, and a predicate whitelist (section 5.2a) |
| SLA query | Selected c.calendar_id from business_calendars, which has no such column; used now() | Uses c.id and a bound :now from the Clock service; Python implementation for SQLite |
| Committee records | EVC reports and SAC/SHC recommendations not modelled | New committee_recommendations table that the evc_report_received and shc_recommendation_recorded predicates read |
| Configuration tables | Alert rules, ladders, weights, regions and the email outbox referenced but absent | Added regions, alert_rules, escalation_ladders, app_config, notifications and jobs |
| EVC Planner | One travel model; seed alone assumed to give reproducibility | Visit mode (travel counts for physical visits only); single search worker for deterministic solves |
| Relative deadlines | dateparser for "within N days of issue" | dateparser for absolute dates only; a custom rule parser for relative deadlines |
| Demo support | Not specified | Injectable clock, reset, audit tamper tool, evaluation endpoint and seed contents (sections 3A, 14) |
| API | 18 endpoint groups | Adds committee recommendations, list reads, config, audit events, notifications, evaluation and demo endpoints |

## 1. Technical Overview

FlowWise is a modular web application: React frontend, FastAPI backend, PostgreSQL, S3-compatible object storage and a Celery worker tier for extraction, scheduled scans, solver runs and simulations. Four design principles apply throughout:

Sections 2 and 3 describe the target architecture. Section 3A defines the lighter runtime profile that the prototype actually runs; the modules, data model and API are the same in both.

Rules are data. Workflow graphs, SLA targets, escalation ladders, scoring weights and compliance windows live in versioned configuration, not in code.

Determinism where it counts. State transitions, SLA clocks, alerts and priority scores are deterministic and reproducible. AI proposes; officers decide.

Everything is grounded and logged. AI output must quote its source and pass validation; every material action enters the hash-chained audit log.

Graceful degradation. If the LLM, OCR or solver fails, the user falls back to a manual path with no data loss.

## 2. Architecture

| Institution / Officer / Expert / Admin users \| React Web UI  (Workflow Studio = React Flow) \| HTTPS / REST (OpenAPI) FastAPI  -- Auth + RBAC + scope checks \| +----------------------------------------------------------+ \| Case \| Workflow \| SLA Clock \| Compliance \| Document \| Alert \| \| Svc  \| Engine   \| Engine    \| Register   \| Registry \| Svc   \| +----------------------------------------------------------+ \| Obligation \| EVC Planner \| Priority  \| Simulator \| Letters \| \| Intelligence\| (CP-SAT)   \| Scoring   \| (SimPy)   \| + Verify\| +----------------------------------------------------------+ \|               \|                \|              \| PostgreSQL     Redis + Celery     MinIO (S3)     Audit hash chain (+pgvector      workers/beat      documents      (in PostgreSQL) stretch)            \| +--> LLM gateway (provider-agnostic, optional) +--> OCR (Tesseract eng + hin) +--> Email adapter (MailHog in demo) / SMS (mock) |
| --- |

## 3. Technology Stack (target)

| Layer | Choice | Purpose and notes |
| --- | --- | --- |
| Frontend | React + TypeScript + Vite; Tailwind CSS or Material UI | Role-based workspaces, dashboards, inbox, timelines |
| Workflow canvas | React Flow | Workflow Studio editor and live case-position view |
| Charts | Recharts | Pendency, attribution, simulator outputs |
| Backend | Python FastAPI + Pydantic v2 | REST APIs, validation, OpenAPI documentation |
| ORM / migrations | SQLAlchemy 2.x + Alembic | Schema control; repeatable seed scripts |
| Database | PostgreSQL (pgvector in stretch) | Transactional data, audit chain, retrieval index for handbook |
| Jobs | Celery + Redis (beat for schedules) | Extraction, reminders, escalation scans, solver, simulation |
| Object storage | MinIO (S3-compatible), private bucket | Documents and generated letters |
| Text extraction | PyMuPDF; Tesseract via pytesseract (eng + hin packs) | Text layer first, OCR fallback, page references retained |
| LLM access | Provider-agnostic gateway with JSON-schema outputs | Obligation extraction and classification; swappable; optional |
| Optimisation | Google OR-Tools CP-SAT | EVC Planner |
| Simulation | SimPy | What-If Capacity Simulator |
| Dates and calendars | dateparser (absolute dates only), a custom rule parser for relative deadlines such as "within N days of issue", python-dateutil, custom business calendar | Due-date resolution and SLA time arithmetic |
| Letters and QR | Jinja2 templates; ReportLab (prototype) or WeasyPrint (production); qrcode | Generated notices with fingerprint and verification QR |
| Authentication | JWT with OAuth-compatible provider abstraction; Argon2id/bcrypt | Server-side RBAC; MFA hook for approvers |
| Email (demo) | MailHog SMTP sink | Demonstrates real SMTP delivery without external services |
| Testing | Pytest, HTTPX, Hypothesis; Vitest + React Testing Library | Unit, API, property-based clock tests, UI |
| Deployment | Docker Compose | One-command demo environment |

## 3A. Prototype Profile (what is built for the demo)

The prototype keeps the modules, data model and API of sections 4 to 14 and swaps only infrastructure, so it runs with two commands on a laptop. Each swap sits behind an interface, so the production component drops in without changing module code.

| Concern | Target (sections 2-3) | Prototype profile |
| --- | --- | --- |
| Database | PostgreSQL | SQLite in WAL mode through SQLAlchemy 2.x; DATABASE_URL switches to PostgreSQL. Audit-chain inserts are serialised with a process lock |
| Background jobs | Celery, Redis, beat | FastAPI BackgroundTasks for extraction, solver and simulation; APScheduler in-process for scans, inbox recompute and audit anchoring; outcomes stored in a jobs table |
| Object storage | MinIO (S3) | StorageBackend interface with a local ./data/files implementation; same generated keys, SHA-256 and signed-link logic |
| Email and SMS | MailHog SMTP, SMS mock | notifications table plus an in-app Outbox page labelled simulated; optional SMTP when MAILHOG_HOST is set |
| PDF letters | WeasyPrint | ReportLab with qrcode (pure pip install) |
| OCR | Tesseract (eng, hin) | Off by default; PyMuPDF text layer only, and the synthetic PDFs have a text layer. Optional scanned sample if Tesseract is installed |
| LLM | Provider-agnostic gateway | Gemini through google-genai with a response schema, behind the gateway. LLM_PROVIDER=none runs the rule-based extractor |
| Vector search | pgvector (stretch) | Out of scope for the prototype |
| Time | System clock | Clock service is the only source of "now"; a demo offset can be advanced |
| Packaging | Docker Compose | Setup, seed and run scripts; backend with uvicorn and frontend with npm run dev. Docker optional |
| Audit write protection | DB role without UPDATE or DELETE | The ORM exposes insert only; a demo-only tamper endpoint (DEMO_MODE=1) uses a raw connection so a failing verification can be shown |

### 3A.1 Demo support requirements

Clock. Every SLA segment, alert, scan and score reads Clock.now(). The offset lives in app_config (demo_clock_offset_seconds); POST /demo/clock/advance moves it, and the next scheduler pass produces alerts, escalations and inbox scores for the new time.

Reset. POST /demo/reset drops and reloads the seed data, rebuilds the audit chain and restores the clock. Prototype target: under 10 seconds.

Seed data. 4 regions with coordinates and calendars; 12 institutions; 40 cases across 4 templates and several stages (about 30 ready for EVC planning); 15 experts with availability and conflict records; 11 users, one per role; 12 synthetic PDFs with ground-truth JSON; default alert rules, ladders and priority weights. Everything is labelled synthetic.

Determinism. Seeds are fixed for the data generator, the CP-SAT solve (one search worker) and the simulator, so every recording take shows the same numbers.

Graceful AI. With LLM_PROVIDER=none the pipeline uses the rule-based extractor and the demo script still passes.

Honesty labels. A persistent banner states that data is synthetic and integrations are simulated; Sourced - verify and placeholder values are tagged beside the value.

## 4. Modules and Responsibilities

| Module | Responsibilities |
| --- | --- |
| Identity and Access | Users, roles, scoped assignments (region, institution), session handling, access checks on every route |
| Case Service | Applications, institutions, case timeline, document versions |
| Workflow Engine | Versioned graph templates, transition validation, parallel stages and joins, return/revert, dry-run, publication state machine |
| SLA Clock Engine | Clock segments by holder, business calendar arithmetic, pause/resume on events, party attribution |
| Scrutiny | Observations, deficiency notices, responses, resubmission versions |
| EVC Management and Planner | Queue, expert registry, availability, conflict declarations, CP-SAT planning, explanations, confirmations |
| Compliance Register | Undertakings, evidence, verification, document validity and renewals |
| Obligation Intelligence | Ingestion, classification, grounded extraction, validators, candidate queue, evaluation harness |
| Alert and Escalation | Rule scans, ladders, dedupe, channels, delivery logs, digests |
| Priority Scoring | Deterministic score with factor breakdown; Action Inbox feed |
| Analytics and Simulator | Pendency, attribution, process-mining queries, SimPy scenarios |
| Letters and Verification | Template rendering, fingerprinting, QR, public verification endpoint |
| Audit | Append-only events with hash chain and verification |

## 5. Workflow Engine Design

### 5.1 Templates as validated graphs

A workflow template is a versioned directed graph stored as JSON and normalised into tables. Cases pin the template version at creation so later changes never alter cases in flight. The same JSON is what the Workflow Studio edits.

| { "template": "SCRUTINY_EVC", "version": 3, "effective_from": "2026-11-01", "start": "SCRUTINY", "stages": [ {"code": "SCRUTINY", "role": "SCRUTINY_OFFICER", "sla_hours": 120, "type": "task"}, {"code": "EVC", "role": "EVC_COORDINATOR", "sla_hours": 240, "type": "task"}, {"code": "DONE", "type": "terminal"} ], "events": [ {"stage": "SCRUTINY", "event": "ISSUE_DEFICIENCY", "requires_reason": true, "holder_after": "INSTITUTION"}, {"stage": "SCRUTINY", "event": "SUBMIT_RESPONSE", "when": {"pred": "open_deficiency"}, "holder_after": "AICTE_OFFICER"}, {"stage": "EVC", "event": "CONFIRM_VISIT", "holder_after": "EXTERNAL_COMMITTEE"}, {"stage": "EVC", "event": "RECORD_EVC_REPORT", "holder_after": "AICTE_OFFICER"} ], "transitions": [ {"from": "SCRUTINY", "to": "EVC", "event": "COMPLETE_SCRUTINY", "when": {"all": [{"pred": "no_open_deficiency"}, {"pred": "docs_verified"}]}}, {"from": "EVC", "to": "DONE", "event": "COMPLETE_EVC", "when": {"pred": "evc_report_received"}}, {"from": "EVC", "to": "SCRUTINY", "event": "RETURN", "requires_reason": true} ] } |
| --- |

All numbers above are placeholders for illustration, not AICTE values. "start" names the single start stage. "sla_hours" are business hours. "events" are in-stage events: they never change the stage, they switch the SLA holder (section 6) and they are the only way a holder changes. "transitions" change the stage.

### 5.2 Template validation (run in the Studio and again at publish)

Exactly one start stage; at least one terminal stage; every stage reachable from start; every non-terminal stage has an outgoing path to a terminal stage.

Every transition references existing stages; every task stage has a responsible role that exists in the role catalogue.

Conditions use only whitelisted predicates (for example no_open_deficiency, docs_verified, evc_report_received) combined with all/any/not; no arbitrary expressions or code.

Parallel stages declare a join rule (all, any, or N of M) and the join target.

Return/revert transitions must require a reason and may only target earlier stages.

Dry-run: a synthetic case is walked along every path; unreachable or stuck paths are reported.

### 5.2a Whitelisted predicates

Conditions may combine only these predicates with all, any and not. Each is a pure server-side function of stored records.

| Predicate | True when | Reads |
| --- | --- | --- |
| no_open_deficiency | Every deficiency observation has an institution response that the officer has verified | scrutiny_observations, institution_responses |
| open_deficiency | At least one deficiency observation still awaits an institution response | scrutiny_observations, institution_responses |
| docs_verified | All document types required for the application type are uploaded and verified | documents, template required types |
| evc_report_received | An EVC report record exists for the current EVC task | committee_recommendations |
| shc_recommendation_recorded | An SHC or SAC recommendation record exists for the case | committee_recommendations |
| visit_confirmed | The EVC plan assignment for the case is confirmed | evc_plan_assignments |

### 5.3 Publication state machine (maker-checker)

| DRAFT -> VALIDATED -> SUBMITTED_FOR_APPROVAL -> PUBLISHED -> RETIRED \| +--> REJECTED (reason required) Rule: approver_user_id != proposer_user_id; both recorded in the audit chain. Rule: PUBLISHED versions are immutable; edits create a new draft version. |
| --- |

### 5.4 Transition algorithm

Load the case's pinned template version and current stage(s).

Check the requested event against allowed transitions; reject with a stable error code and the blocking rule otherwise.

Evaluate whitelisted predicates server-side; never trust client-supplied stage identifiers.

Check actor role, scope and assignment; check reason presence for return/revert.

In one database transaction: write the transition, close the current SLA segment, open the next segment with its holder, create the next stage task, and append the audit event.

After commit: enqueue notifications and recompute priority scores. Use an idempotency key (case, event, expected version) so a retried request cannot transition twice.

In-stage events (ISSUE_DEFICIENCY, SUBMIT_RESPONSE, CONFIRM_VISIT, RECORD_EVC_REPORT) follow steps 1 to 6 except that the stage does not change: close the open SLA segment, open a new one for holder_after, and append the audit event.

## 6. Clock-Aware SLA Engine

Each stage task carries an SLA clock stored as segments. A segment records who held the case, when, and which event started and ended it. Elapsed time per party is the sum of segment durations measured in business time.

| Holder | Meaning | Starts on | Ends on |
| --- | --- | --- | --- |
| AICTE_OFFICER | Case waits for an AICTE officer action | Task creation; institution response received | Deficiency issued; stage completed |
| INSTITUTION | Case waits for the institution | Deficiency or clarification dispatched | Response submitted |
| EXTERNAL_COMMITTEE | Case waits for EVC expert or committee | Visit confirmed; case placed before committee | Report or recommendation recorded |
| SYSTEM | Automated processing | Extraction or scan started | Completed or failed |

### 6.1 Computation rules

Business calendar: working days, working hours and holiday sets are configurable per region; elapsed time between two timestamps is computed over working intervals only.

SLA breach and escalation use only AICTE_OFFICER time. Institution time is tracked against the deficiency response period instead, with its own reminders.

Pausing is a consequence of events (deficiency issued, response received), not a manual toggle; manual overrides require a reason and are audited.

Reports aggregate segments by stage, holder, region and template version, which gives delay attribution and stage-wise percentiles without extra instrumentation.

| -- time held by each party for one case (business-time applied) -- PostgreSQL target; the prototype computes the same sums -- in Python (business_seconds) SELECT s.holder, SUM(business_seconds(s.started_at, COALESCE(s.ended_at, :now), c.id)) AS held_s FROM sla_clock_segments s JOIN stage_tasks t ON t.id = s.stage_task_id JOIN applications a ON a.id = t.application_id JOIN business_calendars c ON c.id = a.calendar_id WHERE t.application_id = :case_id GROUP BY s.holder; |
| --- |

Property-based tests (Hypothesis) assert that segments never overlap, that the sum of segment time equals the task lifetime in business time, and that pause/resume sequences produce the hand-computed values in the fixture set.

## 7. Obligation Intelligence Pipeline

### 7.1 Stages

Ingest and validate: extension, MIME type, signature and size; store in private bucket under a generated key; compute SHA-256.

Text layer: PyMuPDF per page; if a page has too little text, rasterise and run Tesseract (English plus Hindi packs where installed). Retain page number, method and character offsets.

Classify: approval letter, lease deed, EVC report, deficiency letter, other. Rule-based keywords first; LLM classification as an optional second opinion. Reviewer can override.

Extract: prompt the LLM per document type with a strict JSON schema (below). Process page windows so every claim can cite a page.

Validate: schema validation; the quoted text must appear verbatim (after whitespace normalisation) on the cited page; dates must parse; relative deadlines such as "within N days of issue" are resolved against the document date by deterministic code, not by the model; due dates earlier than the document date are flagged.

Queue: valid candidates enter the review queue with confidence and highlighted source; invalid candidates are discarded and counted in the run statistics.

Confirm: the officer accepts, edits or rejects; accepted items create undertakings or validity records with provenance (document, page, quote, run id, reviewer). Edits are logged next to the original.

### 7.2 Output contract (illustrative demo data)

| { "doc_type": "approval_letter", "doc_date": "2026-10-12", "obligations": [ { "category": "UNDERTAKING", "description": "Submit registered lease deed for the permanent campus", "responsible_party": "INSTITUTION", "due": {"kind": "relative", "expression": "within 90 days of issue"}, "source": {"page": 2, "quote": "<verbatim text span from page 2>"}, "confidence": 0.86 } ], "validity_fields": [ {"field": "lease_expiry", "value": "2036-03-31", "source": {"page": 1, "quote": "<span>"}} ] } |
| --- |

### 7.3 Deterministic cross-checks (not AI)

Lease expiry against the declared institution data and any configured minimum validity from the template.

Required document types present for the application type.

Resolved due dates against the business calendar; weekends and holidays handled by configuration.

### 7.4 Evaluation harness

A labelled synthetic corpus (letters, lease deeds, reports, some scanned and degraded) with ground-truth obligations is kept in the repository. A script reports, per field type, precision, recall and F1, the share of candidates with a valid quote, the discard rate and the average review time proxy (candidates per document). Results go into the metric table in the PRD. A rule-based baseline (regex plus dateparser) runs on the same set so the benefit of the LLM is measured rather than assumed.

### 7.5 Fallbacks and privacy

If the LLM is unavailable or returns invalid output twice, the document goes to manual entry with the rule-based suggestions shown.

Provider, model, prompt version, temperature, validation outcome and latency are stored per run.

Only synthetic documents are sent to an external provider in the demo; real deployment requires an approved or self-hosted model and a data-handling review.

## 8. EVC Planner

The planner is an optimisation service, not a decision-maker. It builds a CP-SAT model for a planning window and returns a proposal with explanations. The coordinator confirms or edits.

| Element | Specification |
| --- | --- |
| Inputs | Ready cases (region, priority, ageing, required expertise tags, panel size, visit mode: physical, online or hybrid), experts (tags, home region, availability by date, workload caps), conflict records, planning window |
| Decision variables | visit_date[c,d] (boolean), on_panel[c,e] (boolean), and linking variables expert_on_day[c,e,d] |
| Hard constraints | Each case at most one visit date; panel size met when scheduled; expert available on the visit date; no expert with a conflict record for the case or institution; required expertise covered; an expert at most one visit per day; per-expert cap in the window |
| Soft objectives (weighted) | Maximise scheduled priority-weighted cases; reduce ageing of scheduled cases; cluster same-region visits on adjacent days to cut travel (Haversine distance from the regions table; physical visits only, online visits carry zero travel cost); balance workload across experts |
| Conflict sources | Declared by experts; same institution or group; configured rules such as same-state restriction if the handbook requires it (placeholder until validated) |
| Solver settings | Time limit about 10 seconds for the demo instance; fixed random seed and a single search worker (multi-threaded CP-SAT is not deterministic even with a seed); on timeout, report the best feasible plan and the optimality gap |
| Explanations | For each assignment: contributing factors. For each excluded expert: the first failing hard constraint. For unscheduled cases: binding constraints |
| Infeasibility | Re-solve with penalised relaxations to report which constraints conflict, and suggest the smallest change (for example widen the window or add an expert) |
| Baseline | Greedy earliest-date, first-available-expert assignment on the same instance, used for comparison metrics |

After the coordinator edits a plan, a validator re-checks every hard constraint and shows violations before confirmation. The plan, its parameters, the solver status and its explanations are stored for audit.

## 9. Capacity Simulator

The simulator is a discrete-event model in SimPy. Each region and stage is a queue served by the configured number of officers. Arrivals follow a rate by application type; service times at each stage are sampled from empirical or fitted distributions built from AICTE_OFFICER segments only, so institution waiting time does not distort capacity estimates.

Scenarios change officers per stage or region, arrival rate, or service-time distribution. Each scenario runs N replications with fixed seeds.

Outputs: backlog over time, ageing percentiles (median, 90th) and time-in-system, each with a spread across replications.

Data source is tagged on every run: synthetic distributions in the demo, system clock data once real cases exist.

The UI labels results as simulation under stated assumptions. It never presents them as predictions of actual outcomes.

## 10. Priority Score and Action Inbox

The priority score is a transparent weighted sum of normalised factors. Weights live in configuration and are visible to administrators.

| score = w1*sla_pressure + w2*escalation_level + w3*obligation_urgency + w4*evc_readiness + w5*case_age + w6*blocking_others sla_pressure = 1 - clamp(remaining_officer_time / sla_target, 0, 1) # 1 if overdue escalation_level = current_level / max_level            # 0 to 1 obligation_urgency = 1 - clamp(days_to_due / 30, 0, 1)  # 1 if overdue evc_readiness = 1 if ready for EVC and unscheduled, else 0 case_age = clamp(age_in_working_days / 60, 0, 1) blocking_others = 1 if it blocks another task, else 0 Defaults (placeholders, configurable): w1=0.35 w2=0.20 w3=0.15 w4=0.10 w5=0.10 w6=0.10 The 30 and 60 day horizons are configurable (app_config). |
| --- |

Each inbox item stores factor values and contributions so the UI can show "why this is first".

Items disappear when their underlying condition is resolved; scores are recomputed after events and on a schedule.

Tie-breaking is deterministic (older case first, then reference number).

## 11. Alerts and Escalation

Triggers: stage ageing against AICTE-held time, deficiency response period, undertaking due dates, document expiry windows, EVC pending readiness, assignment changes, decisions recorded.

Ladders: configurable levels with delay, recipient role resolved by scope (region), and message template. Escalate only when the ladder is approved configuration; each level change is an event.

Idempotency: unique key of the form rule_code + entity_id + window_id + level so repeated scans never duplicate an alert.

States recorded separately: generated, sent, failed, acknowledged, escalated, resolved. Bounded retries for delivery; delivery retries never repeat business transitions.

Digest and quiet hours: low-severity alerts batch into a daily digest; quiet hours are configurable to reduce fatigue.

Channels: in-app (default), email through SMTP (MailHog in the target demo stack; a simulated outbox in the prototype profile), SMS as a clearly labelled mock adapter.

## 12. Trust Layer

### 12.1 Hash-chained audit

| hash_n = SHA256( hash_{n-1} \|\| canonical_json(event_n) ) event_n = {actor, action, entity_type, entity_id, before, after, reason, request_id, occurred_at} Verification: recompute from genesis (or last anchor) and compare; report first mismatching event. Writes: insert-only table; application role has no UPDATE/DELETE grants on audit_events. canonical_json: UTF-8, keys sorted, no whitespace, timestamps as ISO-8601 UTC with microseconds and trailing Z, lowercase UUIDs. |
| --- |

Chain is per tenant scope and serialised on insert (advisory lock) to keep order deterministic. The prototype uses a single chain and a process lock under SQLite.

Periodic anchor: the latest hash is exported to a separate file or store so truncation of the tail is also detectable.

This is tamper-evidence, not tamper-proofing; production would add managed key signing and external anchoring.

Demo tamper tool (prototype only). With DEMO_MODE=1 an administrator can alter one stored event through a raw database connection so the verifier's failure and the first mismatching event can be shown on screen. The tool is disabled in any other configuration.

### 12.2 Generated letters and verification

Deficiency notices, EVC schedules and confirmation letters are rendered from versioned templates to PDF, fingerprinted with SHA-256 and stored.

A QR code encodes a verification URL with a random identifier. The public page shows only document type, issue date, status (valid, superseded, withdrawn) and whether an uploaded file matches the stored hash. No personal or sensitive content is exposed.

Digital signature integration (for example eSign or DSC) is an adapter point; the demo uses a simulated signature block, labelled.

### 12.3 Maker-checker

Workflow templates, escalation ladders, scoring weights and compliance windows are changed through proposals. A different authorised user must approve. Both identities, the diff and the reason are audited. Emergency overrides, if configured, require a reason and a post-hoc review flag.

## 13. Data Model

Use UUID primary keys, UTC timestamps, created_at/updated_at columns and foreign keys. Index reference_no, institution identifier, status, region, current stage, due_at, expiry_date, holder and expert availability dates. Tables carried over from v1.0 are listed first, then new tables.

| Table | Key fields / relationships |
| --- | --- |
| users, roles, user_roles | id, name, email, password_hash or provider_subject, active; role_name; scope_type, scope_id (region or institution) |
| institutions | id, permanent_identifier, name, region, address, status |
| applications | id, reference_no, institution_id, application_type, academic_year, submitted_at, status, calendar_id |
| workflow_templates, workflow_stages, workflow_transitions | template_id, version, status, effective_from; stage code, role, sla_hours, type; from/to, event_code, condition_json, requires_reason |
| application_workflows | application_id, template_id, template_version, current_stage_ids, status, version (for optimistic locking) |
| stage_tasks | application_id, stage_id, assigned_role, assigned_user, status, due_at, completed_at |
| scrutiny_observations, institution_responses | observation: stage_task_id, category, remarks, created_by; response: observation_id, text, version, submitted_at |
| undertakings, compliance_evidence | institution_id, application_id, title, due_at, status, verifier_id, provenance_id; evidence: undertaking_id, document_id, review_status |
| documents | institution_id, application_id, document_type, storage_key, sha256, version, issue_date, expiry_date, uploaded_by |
| alerts, alert_events | entity_type, entity_id, rule_code, recipient_id, idempotency_key, status; channel, level, delivery_status, triggered_at |
| audit_events | actor_id, action, entity_type, entity_id, before_json, after_json, reason, occurred_at, prev_hash, hash, request_id |
| sla_clock_segments (new) | stage_task_id, holder, started_at, ended_at, start_event_id, end_event_id, override_reason |
| business_calendars, calendar_holidays (new) | region, working_days, start_time, end_time; calendar_id, date, label |
| workflow_change_requests (new) | template_version_id, proposed_by, approved_by, status, diff_json, reason |
| extraction_runs, extraction_pages (new) | document_id, method, model, prompt_version, status, stats_json; page_no, text, offsets |
| obligation_candidates (new) | run_id, category, description, party, due_json, resolved_due, source_page, source_quote, confidence, status, reviewed_by, edited_json |
| evc_experts, expert_availability, coi_records (new) | expert profile, tags, home_region, caps; expert_id, date, available; expert_id, institution_id or group, reason, declared_at |
| evc_plans, evc_plan_assignments (new) | window, params_json, solver_status, objective; case_id, date, panel, visit_mode, explanation_json, status (proposed, edited, confirmed) |
| priority_scores (new) | entity_type, entity_id, user_id, score, factors_json, computed_at |
| simulation_scenarios, simulation_runs (new) | params_json, data_source, seed; metrics_json, replications, created_by |
| generated_documents (new) | case_id, template_code, template_version, storage_key, sha256, verify_token, status |
| handbook_chunks (stretch) | document_id, page, text, embedding (pgvector), version |
| committee_recommendations (new) | application_id, stage_task_id, committee (EVC, SHC, SAC), recommendation, remarks, document_id, submitted_by, submitted_at |
| regions (new) | code, name, latitude, longitude, calendar_id |
| alert_rules, escalation_ladders (new) | rule_code, trigger_type, window, severity; ladder: rule_code, level, delay_hours, recipient_role, template_code |
| app_config (new) | key, value_json, version, status; holds priority weights, horizons, quiet hours and the demo clock offset; changes go through maker-checker |
| notifications (new) | alert_event_id, channel, recipient_id, subject, body, status, created_at; the outbox for simulated email and SMS |
| jobs (new) | kind, entity_id, status, attempts, last_error, started_at, finished_at |

## 14. API Design

Prefix /api/v1; JSON bodies; consistent error shape {"error":{"code","message","details"}}; pagination and filtering on lists; authorisation and audit on every state change.

| Method and endpoint | Purpose |
| --- | --- |
| POST /auth/login; GET /auth/me | Authenticate; current user and scopes |
| GET/POST /applications; GET /applications/{id}; GET /applications/{id}/timeline | Cases, permitted detail and chronological history |
| POST /applications/{id}/documents | Upload with validation, versioning and checksum |
| POST /applications/{id}/observations; POST /applications/{id}/responses | Scrutiny and institution response; a deficiency observation emits ISSUE_DEFICIENCY and a response emits SUBMIT_RESPONSE (SLA holder switches, stage unchanged) |
| POST /applications/{id}/transitions | Request a workflow event; idempotency key header required |
| GET /applications/{id}/sla | Clock segments and time held by each party |
| POST /documents/{id}/extract; GET /documents/{id}/extraction | Start and read an extraction run |
| GET /obligation-candidates; POST /obligation-candidates/{id}/decision | Review queue; accept, edit or reject |
| POST /undertakings; POST /undertakings/{id}/evidence; PATCH /undertakings/{id}/verification | Register, evidence and verification |
| GET /evc/queue; POST /evc/plans; GET /evc/plans/{id}; POST /evc/plans/{id}/assignments/{aid}; POST /evc/plans/{id}/confirm | Queue, run planner, inspect, edit and confirm |
| GET/POST /experts/{id}/availability; POST /experts/{id}/conflicts | Availability and conflict declarations |
| GET /inbox | Ranked actions with factor breakdown for the caller |
| GET /alerts; POST /alerts/{id}/ack | Alert list and acknowledgement |
| GET /dashboard/summary; GET /reports/pendency; GET /reports/attribution | Role-scoped aggregates and per-party delay attribution |
| POST /simulations; GET /simulations/{id} | Run and read scenarios (management role) |
| GET/POST /admin/workflow-templates; POST /admin/workflow-templates/{id}/validate; POST .../dry-run; POST .../submit; POST .../approve; POST .../reject | Studio persistence, validation, dry-run and maker-checker |
| POST /letters; GET /letters/{id}; GET /verify/{token} (public) | Generate letter; public verification |
| GET /audit/verify?scope=... | Recompute and report hash chain status (auditor, admin) |
| POST /applications/{id}/committee-recommendations | Record an EVC report outcome or an SHC/SAC recommendation; the EVC kind emits RECORD_EVC_REPORT |
| GET /institutions; GET /experts; GET /documents; GET /undertakings | Scope-filtered list reads with filters and pagination |
| GET /evc/plans/{id}/baseline | Greedy baseline result and the comparison measures |
| GET/PUT /admin/config/{key}; GET /admin/users | Weights, horizons and ladders (maker-checker applies); users and roles |
| GET /notifications | Outbox of simulated email and SMS |
| GET /audit/events | Recent audit events with hashes (auditor, admin) |
| POST /evaluation/run; GET /evaluation/latest | Run the extraction evaluation against the rule-based baseline; read the metrics |
| POST /demo/reset; GET /demo/clock; POST /demo/clock/advance; POST /demo/tamper | Demo support; administrator only, and 404 unless DEMO_MODE=1 |

## 15. Security and Privacy

Server-side RBAC plus scope checks (region, institution, assignment) on every protected operation; deny by default.

Argon2id or bcrypt password hashing; short-lived access tokens; MFA hook for approver and admin roles; refresh rotation for production.

Upload validation (extension, MIME, signature, size), private storage, short-lived signed download URLs, optional malware scanning where infrastructure permits.

Public verification endpoint exposes only status and hash match, with rate limiting and non-guessable tokens.

LLM calls go through a gateway that logs requests, strips unnecessary metadata, and can be disabled or pointed to an approved or self-hosted model.

Secrets in environment or secret manager; .env excluded from version control; separate dev, demo and production credentials.

Retention, backup, recovery and incident-response procedures must be defined and approved before any production use.

DEMO_MODE=1 enables the /demo endpoints and the audit tamper tool; with it off they return 404, and when on they are administrator only.

## 16. Reliability and Error Handling

Workflow transitions, SLA segment changes and audit appends share one transaction; optimistic locking on application_workflows prevents double transitions.

Status codes: 400 invalid input, 401 unauthenticated, 403 unauthorised, 404 missing, 409 invalid state or version conflict, 422 schema failure, 500 unexpected. Every response carries a request id.

Worker tasks are idempotent and retried with backoff; poison tasks go to a dead-letter list visible to administrators. In the prototype, background job outcomes are stored in the jobs table and shown to administrators.

Solver and simulation runs are time-bounded and report partial or infeasible status rather than failing silently.

Database constraints (foreign keys, unique keys, check constraints) act as a second line of defence behind application validation.

## 17. Testing and Evaluation

| Category | Examples and targets |
| --- | --- |
| Unit | Transition validator, whitelisted predicates, business-time arithmetic, alert idempotency, priority score factors, hash computation |
| Property-based | SLA segments never overlap and sum to task lifetime; transition sequences never reach invalid states; template validator accepts only well-formed graphs |
| API integration | Submission creates case on pinned template; transition creates task, segment switch and audit event; maker-checker blocks self-approval |
| Security | Cross-institution access denied; scope enforcement for regional roles; public verify endpoint leaks nothing sensitive |
| Extraction evaluation | Precision, recall and F1 per field on labelled synthetic corpus; 100% of displayed candidates have a verifiable quote; baseline comparison |
| Planner evaluation | Checker finds 0 hard-constraint violations across generated instances; compare to greedy baseline on ageing, travel and workload spread; the same seed returns the identical plan |
| Simulator sanity | Known cases (single queue with known rates) match the Erlang C formula within tolerance (M/M/c cases); seeds reproduce results |
| Audit integrity | Mutating any stored event is detected and located by the verifier |
| UI | Studio validation messages, inbox factor display, EVC plan editing, role navigation |
| Demo acceptance | Run the eight-step script in PRD section 12 from seeded data three times without manual fixes |

## 18. Deployment and Configuration

The table lists the containerised target environment. The prototype profile (section 3A) runs only web and api.

| Service | Role in demo environment |
| --- | --- |
| web | React build served over HTTPS (reverse proxy) |
| api | FastAPI application with health endpoint and OpenAPI docs |
| worker | Celery workers for extraction, solver, simulation and notifications |
| beat | Scheduler for reminders, escalation scans, inbox recomputation, audit anchoring |
| postgres | Primary database (named volume) |
| redis | Broker and cache |
| minio | Private object storage (named volume) |
| mailhog | SMTP sink and inbox viewer for demonstrating real email delivery |

Setup scripts install dependencies, run migrations and load repeatable seed data (synthetic institutions, cases, experts, conflicts, documents and expired or expiring items); Docker Compose is the one-command path for the target stack.

.env.example documents DATABASE_URL, storage path, JWT secret, DEMO_MODE, LLM_PROVIDER (none or gemini) and its key (optional), solver time limit and upload limits; Redis and SMTP settings apply only to the target stack.

The system remains fully usable with the LLM disabled: manual entry plus rule-based suggestions.

Production hosting, residency, backups and monitoring require institutional approval and security review.

## 19. Team Allocation and Build Sequence

| Member | Ownership |
| --- | --- |
| 1. Product and workflow lead | Handbook mapping, workflow engine, template validation, SLA clock engine |
| 2. Backend and database | Schema, RBAC and scope, audit hash chain, letters and verification, API contracts |
| 3. Compliance, alerts and analytics services | Undertaking and document registers, scheduler, escalation, priority score, simulator |
| 4. Frontend lead | App shell, role navigation, Workflow Studio (React Flow), case timeline |
| 5. Frontend and data visualisation | Dashboards, Action Inbox, EVC planner UI, attribution and simulator charts |
| 6. AI, optimisation and QA | Extraction pipeline and evaluation harness, CP-SAT planner, synthetic data, test scenarios |

Member 6 carries two heavy items. If the schedule slips, member 2 takes the planner API and persistence while member 6 keeps the solver model and extraction.

| Phase | Deliverable | Exit condition |
| --- | --- | --- |
| 0. Validate | Handbook glossary and traceability matrix; synthetic corpus plan; frozen API contracts | Workflow combinations and roles confirmed or marked as placeholders |
| 1. Foundation | Auth, scope, schema, audit chain, seed data | All roles log in; chain verifies |
| 2. Workflow and SLA | Engine, SLA segments, return/resubmit, timeline | Deficiency loop switches clock holders correctly |
| 3. Studio | Graph editor, validation, dry-run, maker-checker | New template built, approved and followed by a new case |
| 4. Obligation Intelligence | Pipeline, review UI, evaluation report | Metrics generated; fallback path works |
| 5. EVC Planner and Inbox | Solver, explanations, editing, priority score, inbox | Zero violations; baseline comparison shown |
| 6. Alerts, analytics, simulator | Escalation ladders, attribution, scenarios | Overdue item escalates; scenario compares outcomes |
| 7. Harden and rehearse | Security tests, demo rehearsals, documentation | Eight-step script passes three consecutive runs |

Cut-line order if time is short: Deficiency Assist, simulator polish, weight editor, extra document types. Never cut the workflow core, SLA engine, grounded extraction, Studio or audit chain.

## 20. Stretch Design: Deficiency Assist

Load the handbook and circulars as versioned documents; chunk by page and heading; embed into pgvector; retrieval returns passages with document and page.

Draft generation uses retrieved passages only; every clause reference in the draft must map to a retrieved chunk, otherwise it is removed. If nothing relevant is retrieved the assistant states that.

After an institution response, a per-observation comparison produces likely addressed, unclear or not addressed with the supporting snippet; officers can override, and overrides are logged.

Recurring-deficiency analytics count categories by application type to feed applicant pre-submission checklists.

## 21. Open Technical Decisions

Official authentication method, user directory and any single sign-on requirement.

Approved integration APIs and data contracts, if any, and whether a sandbox exists.

Authoritative source and update process for workflow rules, timelines and conflict-of-interest norms.

LLM hosting: external provider with synthetic data only, or an approved self-hosted model, and OCR choice for Indic scripts.

Expected concurrency, document volume and seasonal peaks for sizing.

Authorised notification channels and digital-signature mechanism.

Hosting environment, data residency and retention requirements.

## 22. Demo Acceptance Checklist

Studio: build, validate, dry-run and submit a template; a second user approves; a new case follows it.

Obligation Intelligence: upload synthetic letter and lease deed; candidates with highlighted quotes; accept, edit, reject; register updates; evaluation report available.

SLA: deficiency return switches holder to institution; response switches back; attribution report matches fixture values.

EVC Planner: plan with explanations; edit an assignment; conflict validator reacts; comparison with greedy baseline displayed.

Action Inbox: ranked items with factor breakdown; resolving an item removes it.

Escalation: advancing the demo clock past the AICTE-held SLA creates ladder events and an email visible in the simulated outbox (MailHog in the target stack).

Simulator: scenario comparison with assumptions and data source shown.

Trust: QR verification works; altering an audit row with the demo-only tamper tool is detected and the first mismatching event is named.

Clock and reset: advancing the demo clock moves SLA segments, alerts and inbox scores consistently; a reset restores the seed state (prototype target: under 10 seconds).

All demo data, simulated integrations and placeholder rule values are labelled on screen.
