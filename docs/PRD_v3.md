SIH 2026  |  PRODUCT REQUIREMENTS DOCUMENT

AICTE FlowWise

AI-Powered Approval Workflow Automation, Compliance Monitoring and Alert Management

Version 3.0  |  30 October 2026  |  SIH solution specification

| Scope note. This is a proposed design for the Smart India Hackathon. Workflow rules, timelines, roles, thresholds and integrations must be validated against the current AICTE Approval Process Handbook and authorised stakeholders before they are presented as official. All demonstration data is synthetic and labelled as such. Values marked "Sourced - verify" in section 6 come from public AICTE texts and press coverage read on 30 October 2026, not yet from the Approval Process Handbook itself; confirm them with a mentor before presenting them as official. |
| --- |

| Item | Detail |
| --- | --- |
| Document | Product Requirements Document (PRD) |
| Version | 3.0 - supersedes v2.0 |
| Status | SIH prototype-ready specification (audited; handbook terms sourced where marked) |
| Product | AICTE FlowWise |
| Problem statement | Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management |

### What changed from v2.0

| Area | v2.0 | v3.0 |
| --- | --- | --- |
| Handbook terms | SAC/SHC left undefined; EVC assumed to be constituted by the Regional Officer | SAC = Standing Appellate Committee, SHC = Standing Hearing Committee; EVC constituted by the Council with physical, online or hybrid visits (2026-27 corrigendum). Sourced values in section 6 |
| Application types | Generic category | Seeded with the two categories seen on 2026-27 portal reports: Increase In Intake or New Course, and New Program or New Level. The template mapping is a demo assumption |
| EVC Planner | Travel clustering for every visit | Visit mode (physical, online, hybrid); travel cost applies to physical visits only (FR-13) |
| In-stage events | Deficiency and response described loosely | Explicit in-stage events switch the SLA holder without changing the stage (FR-03) |
| Committee outcomes | Not modelled | EVC reports and SAC/SHC recommendations stored as structured records that workflow conditions can read (FR-04) |
| Differentiators | Summary said four; scope table listed more | Four headline differentiators, supported by the Action Inbox and trust layer, stated consistently |
| Prototype profile | Container-style stack assumed | New section 17 and TRD section 3A: what is real, what is simulated, demo clock, reset and tamper tool |
| Demo script | Eight steps; tamper done in the database | Eight timed scenes for a recorded video; SLA and escalation shown with the demo clock; tamper through a labelled demo-only tool |
| Submission format | Open question | Public template copy: PDF, at most six slides, no video field; video is linked inside the PDF (verify on the portal) |

## 1. Executive Summary

AICTE FlowWise is a configurable workflow and compliance intelligence platform for the AICTE approval lifecycle. It manages scrutiny, re-scrutiny, Expert Visit Committee (EVC) coordination, SAC/SHC stages, institutional undertakings, document validity, alerts and escalation in one auditable system.

Thesis: a tracker tells an officer where a case is; FlowWise tells them what to do next, what is about to go wrong, and why. The platform supports authorised human decisions. It never grants, rejects or alters a statutory approval, and every AI or algorithmic output is advisory, cited to its source and confirmed by an officer.

Beyond a solid workflow core, FlowWise adds four headline differentiators, supported by an explainable Action Inbox and a hash-chained trust layer:

Obligation Intelligence - AI reads approval letters, EVC reports and lease deeds and proposes undertakings, deadlines and validity dates, each linked to the exact source page and text span. Officers confirm; only confirmed items enter the register.

Clock-Aware Pendency and What-If Simulator - SLA clocks pause while the institution holds a case, so delay is attributed to the right party. A simulator then answers capacity questions such as "what happens to the regional backlog if two scrutiny officers are added?"

EVC Planner - a constraint solver proposes visit dates and panels while respecting availability, conflicts of interest, geography and workload, and explains every proposal.

Visual Workflow Studio - administrators assemble stage combinations on a canvas, validate and dry-run them, and publish a versioned template that live cases then follow.

## 2. Problem and Opportunity

Approval applications can pass through different combinations of scrutiny, re-scrutiny, EVC and SAC/SHC stages, depending on application type and governing rules. In parallel, institutions carry time-bound undertakings, conditions and documents such as lease records that need follow-up long after a decision. The pain points below are working assumptions to validate with officers and mentors.

| Pain point (assumed - validate) | Why conventional tracking falls short | FlowWise answer |
| --- | --- | --- |
| Officers cannot see owner, pending action and age for each case without manual follow-up | Status lists show state, not priority or next action | Action Inbox with explainable priority; case timeline with owner and next step |
| Obligations are buried in letters and reports and tracked manually | Manual transcription is slow and error-prone, so deadlines are missed | Obligation Intelligence with source-cited, officer-confirmed extraction |
| Pendency numbers blame the wrong party | A single elapsed clock mixes officer time and institution response time | Party-aware SLA clocks and delay attribution |
| EVC scheduling is coordination-heavy | Queues record outcomes but do not solve availability, conflicts and travel | Constraint-based EVC Planner with explanations |
| Stage combinations vary and rules change | Hard-coded flows need developers for every change | Visual Workflow Studio with versioning and maker-checker |
| Management cannot test capacity decisions | Dashboards describe the past only | What-if simulator calibrated from the system's own clock data |

## 3. Vision, Objectives and Differentiation

Vision: one configurable, transparent and auditable operational view of the AICTE approval and compliance lifecycle that helps officers act early.

Configure and publish application pathways for the supported stage combinations without code changes.

Route cases to the correct authorised role or queue only when prerequisites are met.

Track scrutiny observations, resubmissions, EVC planning and committee-stage progress.

Keep institution-level registers of undertakings, conditions and document validity, populated with AI assistance and human confirmation.

Attribute pendency to the party that actually holds the case and let management test capacity scenarios.

Generate timely reminders and rule-based escalations; rank officer work by explainable priority.

Preserve a complete, tamper-evident action history with strict role and scope control.

| Capability | Conventional workflow tracker | AICTE FlowWise |
| --- | --- | --- |
| Obligation capture | Manual entry | AI-proposed, source-cited, officer-confirmed |
| Ageing | Total elapsed time | Time held by AICTE officer vs institution vs committee |
| EVC scheduling | Record a date | Solve for dates and panels; show why |
| Workflow change | Developer change request | Drag, validate, dry-run, publish with second approval |
| Officer view | Status lists and charts | Ranked next actions with factor breakdown |
| Capacity planning | Retrospective charts | Scenario simulation |
| Audit | Event table | Hash-chained log; QR-verifiable letters |

## 4. Users and Roles

| Role | Primary capabilities |
| --- | --- |
| Institution applicant | Submit applications and documents; view permitted status; respond to deficiencies; submit evidence against undertakings and renewals. |
| Scrutiny officer | Review assigned cases; record observations; issue deficiencies; verify resubmissions; recommend stage completion. |
| EVC coordinator | Manage the EVC queue; run the EVC Planner; set visit mode (physical, online or hybrid); confirm schedules and panels; record visit completion and the EVC report outcome. |
| EVC expert / committee member | View assigned visits; declare availability and conflicts of interest; submit visit reports. The Council constitutes the EVC; FlowWise only schedules and records. |
| SAC/SHC member | Member of the Standing Appellate or Standing Hearing Committee: view assigned cases, EVC reports and show-cause replies; record the committee recommendation as defined by the handbook. |
| Regional officer | Monitor regional cases, workload, ageing and assigned escalations. |
| Compliance officer | Confirm extracted obligations; verify evidence; track conditions and document expiry. |
| Senior management | View consolidated dashboards, bottleneck attribution and run capacity simulations. |
| System administrator | Manage users, roles, workflow templates (as maker), notification settings and reference data. |
| Second approver | Review and approve or reject workflow-template and rule changes proposed by an administrator (maker-checker). |
| Auditor (read-only) | View permitted cases, audit chain, template versions and verification status without modifying anything. |

Permissions are role- and assignment-based and scoped by region and institution. A user sees only the records and actions their authorisation allows.

## 5. Scope

| Tier | Content | Depth for the SIH prototype |
| --- | --- | --- |
| 1. Core (must) | Case records, versioned workflow engine, scrutiny and deficiency handling, EVC queue, undertaking and document registers, alerts and escalation, dashboards, audit, RBAC | Complete and demonstrable end to end on synthetic data |
| 2. Differentiators (must, thin but real) | Obligation Intelligence, clock-aware SLA, What-If Simulator, EVC Planner, Visual Workflow Studio, Action Inbox, trust layer | Each works on the demo dataset with explanations; depth limits stated in section 14 |
| 3. Stretch (only after tiers 1-2 pass) | Deficiency Assist with handbook retrieval, real SMTP email delivery, bilingual (English/Hindi) UI, bulk import | Designed in the TRD; built only if time allows |
| Out of scope | Autonomous approval decisions; replacing inspections or committee deliberation; claiming live AICTE integration; training foundation models; using real sensitive records | Stated explicitly in the pitch |

## 6. Terminology and Handbook Traceability

Several terms in the problem statement depend on the current AICTE Approval Process Handbook. They must be defined from the handbook, not from this document. The tables below are working artefacts: the team completes them before build freeze, and the demo configuration may use only values recorded here. Rows marked "Sourced - verify" were taken from public AICTE texts (the 2016 Regulations as mirrored online, the 2026-27 corrigendum, a 2026-27 SAC report published by an institution) and press coverage. They have not been checked against the Approval Process Handbook itself and stay configurable.

| Term | Meaning in FlowWise | Source to confirm |
| --- | --- | --- |
| Scrutiny / re-scrutiny | Document and data review stage (Scrutiny or Re-Scrutiny Committee), and its repeat after institution response | Regulations 2016; Handbook process chapter - confirm |
| EVC | Expert Visit Committee: verifies infrastructure on site, online or hybrid. Constituted by the Council from 2026-27 (earlier by the Regional Officer). FlowWise schedules and records visits; it never constitutes committees | 2026-27 corrigendum (issued 2 December 2025) - Sourced, verify |
| SAC / SHC | SAC: Standing Appellate Committee, hears appeals from institutions. SHC: Standing Hearing Committee, reviews EVC reports and replies to show-cause notices and recommends to the Executive Committee. Portal reports show SAC/SHC as one stage with a status such as Recommended | Regulations 2016; a 2026-27 AICTE SAC report published by an institution - Sourced, verify with mentor |
| Undertaking / condition | A time-bound obligation recorded against an institution and approval | Approval letters, handbook |
| Deficiency | An observation requiring institution response. The portal generates a deficiency report and lets institutions correct data online several times before final submission | Regulations 2016; Handbook, officer interviews - confirm |
| Application type | Category that selects the workflow template. 2026-27 portal reports show types such as Increase In Intake or New Course and New Program or New Level; the type-to-template mapping in the demo is an assumption | Portal reports 2026-27; Handbook, problem statement - confirm |

| Workflow element | Handbook clause | Value used in demo | Status |
| --- | --- | --- | --- |
| Only Scrutiny path | To be recorded | Configurable placeholder | Pending validation |
| Scrutiny + EVC path | To be recorded | Configurable placeholder | Pending validation |
| EVC + SAC/SHC path | To be recorded | Configurable placeholder | Pending validation |
| Only EVC path | To be recorded | Configurable placeholder | Pending validation |
| Return / revert rules | To be recorded | Configurable placeholder | Pending validation |
| Deficiency response period | To be recorded | Configurable placeholder | Pending validation |
| EVC scheduling and conflict rules | To be recorded | Configurable placeholder | Pending validation |
| Undertaking types and deadlines | To be recorded | Configurable placeholder | Pending validation |
| Document validity rules | To be recorded | Configurable placeholder | Pending validation |
| Escalation hierarchy | To be recorded | Configurable placeholder | Pending validation |
| EVC constitution and visit mode | 2026-27 corrigendum (2 Dec 2025) | Council-constituted; visit mode field: physical, online or hybrid | Sourced - verify |
| Appeal to SAC | Regulations 2016; confirm in Handbook 2024-27 | Appeal within 7 days of the LoR upload date (configurable) | Sourced - verify |
| State or University views | Regulations 2016 (scrutiny) | 21 days from receipt; silence treated as no objection (configurable) | Sourced - verify |
| Approval decision cut-off | Regulations 2016 | No LoA or EoA after 30 April of the calendar year (configurable) | Sourced - verify |

## 7. Functional Requirements

### 7.1 Core platform

| ID | Requirement | Priority | Acceptance criteria |
| --- | --- | --- | --- |
| FR-01 | Application and institution records: unique case reference, institution profile, versioned documents, current stage, owner, next action, due date | Must | A case page shows owner, stage, last action, next action and due date; document versions are never silently overwritten. |
| FR-02 | Configurable, versioned workflow engine supporting Only Scrutiny, Scrutiny + EVC, EVC + SAC/SHC, Only EVC and configurable extensions; authorised return/revert with reason | Must | Cases follow only valid transitions for their pinned template version; a blocked transition shows the rule that blocked it. |
| FR-03 | Scrutiny and deficiency handling: structured observations, deficiency communication, institution response, resubmission versions; deficiency and response are in-stage events that switch the SLA holder without changing the stage | Must | A deficiency return needs a reason and category; the response and re-scrutiny status appear in the timeline. The stage stays the same while the SLA holder switches. |
| FR-04 | EVC management: queue with readiness and ageing, visit mode (physical, online or hybrid), schedule and panel records, EVC report and SAC/SHC recommendation records, visit completion, routing after the visit | Must | EVC queue filters by region and readiness; completion routes the case per the template. EVC reports and committee recommendations are stored as structured records that workflow conditions can read. |
| FR-05 | Undertaking and compliance register with owner, evidence, due date and verification status (Not Due, Due Soon, Submitted, Under Verification, Compliant, Deficient, Overdue) | Must | An undertaking can be created or confirmed from an extraction, evidenced, verified and closed with full history. |
| FR-06 | Document validity and renewal: issue and expiry dates, reminders, renewal versions | Must | An expiring document appears on dashboards and triggers a configured reminder; the old version stays in history. |
| FR-07 | Alerts and escalation: configurable triggers, windows, recipients, ladders and templates; delivery and result logging | Must | An overdue item reaches the authorised queue; escalation history records trigger, recipient, time and result; no duplicate active alerts. |
| FR-08 | Dashboards and reports: status, stage, region, type, officer, ageing, EVC queue, compliance, expiry; filters and export | Must | Counts reconcile with the test dataset; exports are restricted to authorised roles. |
| FR-09 | Audit and administration: role-based users, permissions, workflow versions with effective dates, change history | Must | Every material action records actor, entity, time, before/after values, reason and source. |

### 7.2 Differentiators

| ID | Requirement | Priority | Acceptance criteria |
| --- | --- | --- | --- |
| FR-10 | Obligation Intelligence. Ingest approval letters, EVC reports, deficiency letters and lease deeds; classify the document; propose obligations (description, responsible party, due date or rule, category) and lease/validity fields. Each candidate carries the page, the verbatim source text and a confidence value. | Must | Candidates whose quoted text is not found in the source page are rejected automatically. An officer can accept, edit or reject each candidate; only accepted items enter the register with provenance. Extraction failure never blocks manual entry. |
| FR-11 | Clock-aware SLA and pendency attribution. Each stage task has an SLA clock split into segments held by AICTE officer, institution, external committee or system. Clocks pause and resume on defined events and respect a configurable business calendar. | Must | Elapsed time per party is computed from segments and matches hand-calculated test cases; escalation uses the running AICTE-held time only; reports show delay by stage and by party. |
| FR-12 | What-If Capacity Simulator. Run scenarios (officers added or removed, arrival-rate change, stage service-time change) per region or type and compare backlog and ageing outcomes. | Must | A scenario returns backlog and ageing percentiles with spread across replications; results are labelled "simulation, not forecast" and show the input assumptions and data source (synthetic or system clock data). |
| FR-13 | EVC Planner. Propose visit dates and panels for ready cases subject to expert availability, declared conflicts of interest, expertise tags, panel size, workload caps, visit mode, regional clustering of physical visits and case priority. Show reasons for each assignment and for each excluded expert. | Must | Proposals never contain a conflict-of-interest violation or an unavailable expert; the coordinator can accept, edit or re-run; an infeasible request explains which constraints conflict; results beat a naive greedy baseline on the stated measures. Online visits carry no travel cost. |
| FR-14 | Visual Workflow Studio. Canvas for stages, transitions, conditions, responsible roles and SLA targets. Validation (reachability, dead ends, terminal states, role coverage), dry-run on a sample case, and versioned publishing. | Must | An administrator builds a new stage combination, validates it, dry-runs it and submits it; a second approver publishes it; a new case follows it; in-flight cases stay on their old version. |
| FR-15 | Officer Action Inbox. A ranked list of next actions per officer with a deterministic, configurable priority score and a visible factor breakdown. | Must | Each item shows its score and factors (for example SLA time left, escalation level, obligation due date, EVC readiness, age); changing weights changes ranking predictably. |
| FR-16 | Deficiency Assist (stretch). Draft a structured deficiency notice from officer observations with handbook citations; after an institution response, flag each observation as likely addressed or unclear for the officer. | Could | Every cited clause is retrieved from the loaded handbook with page reference; if nothing is found the assistant says so; the officer edits and dispatches. |
| FR-17 | Trust layer. Hash-chained audit events; generated letters with SHA-256 fingerprint and QR code resolving to a verification page; maker-checker for template and rule publication. | Must | Altering any stored audit event breaks verification and is reported; scanning a letter QR shows match or mismatch and status without exposing sensitive data; the same user cannot propose and approve a change. |

## 8. Key User Journeys

### Journey A - application through configured stages

Institution submits an application and documents; the system creates a case on the template version approved for that application type.

The case enters the scrutiny or EVC queue; the SLA clock starts with the AICTE officer as holder.

Officer records observations; if deficient, the case returns to the institution with reasons, and the clock switches to the institution.

Institution responds; the clock returns to the officer, who verifies the resubmission and records stage completion.

The engine advances the case only when prerequisites and authorisation checks pass, and the next task appears in the next officer's Action Inbox.

### Journey B - obligation intelligence

A compliance officer uploads an approval letter or lease deed.

FlowWise extracts text (OCR when scanned), classifies the document and proposes obligations and validity fields with source quotes.

The officer sees each candidate beside the highlighted source page, edits or rejects, and confirms.

Confirmed items create undertakings and document-validity records with provenance; reminders and escalation schedules start automatically.

### Journey C - EVC planning

The coordinator opens the EVC queue of ready cases and sets the planning window.

The EVC Planner proposes dates and panels, with reasons and a list of excluded experts and why.

The coordinator adjusts any assignment; the plan is re-checked for conflicts.

Confirmed visits notify experts and the institution; completion records route the case onward.

### Journey D - officer day

Officer opens the Action Inbox and sees the highest-priority items with factor breakdown.

Acting on an item opens the case at the right panel; alerts that are already resolved disappear.

Unresolved warnings escalate along the configured ladder, and the escalation is visible in the case history.

### Journey E - administrator changes a workflow

Administrator opens the Workflow Studio, drags stages and transitions into a new combination, and assigns roles and SLA targets.

The studio validates the graph and runs a dry-run on a sample case.

The administrator submits the version; a second approver reviews the diff against the previous version and publishes it.

New cases follow the new version; running cases are unaffected.

## 9. AI and Algorithm Governance

| Component | What it may do | Human gate | Fallback |
| --- | --- | --- | --- |
| Obligation extraction (LLM) | Propose obligations and fields as schema-validated JSON with a verbatim source quote | Officer accepts, edits or rejects every candidate | Rule-based and regex extraction; manual entry |
| Document classification | Suggest a document type | Reviewer confirms | Manual type selection |
| Deficiency Assist (stretch) | Draft notice text with retrieved citations; flag likely addressed observations | Officer edits and dispatches; flags are advisory | Manual drafting |
| EVC Planner (optimisation) | Propose dates and panels | Coordinator confirms or edits | Manual scheduling |
| Simulator and priority score | Rank and project under stated assumptions | Advisory only | Plain dashboards |

No AI or algorithmic output grants, rejects or alters a statutory approval or a compliance status.

Every extracted value links to a source page and quoted text; an ungrounded value is discarded, not shown.

Model, prompt version, time and validation outcome are stored for every AI call.

Corrections by officers are logged and kept separately from the original extraction.

The system stays usable if the AI provider is unavailable.

Simulation and ranking outputs always display their assumptions and are never described as predictions.

## 10. Non-Functional Requirements

| Area | Requirement |
| --- | --- |
| Security | Server-side RBAC with region and institution scope; least privilege; secure sessions; encryption in transit and, where supported, at rest; short-lived signed download links. |
| Privacy | Collect only necessary data; synthetic data in the demo; define retention and deletion before any real deployment; avoid sending sensitive documents to external AI providers without approval. |
| Auditability | Hash-chained audit events for material actions and configuration changes; verification endpoint. |
| Reliability | Idempotent workflow transitions, alerts and scheduled scans; extraction and solver failures degrade to manual paths without data loss. |
| Performance (prototype targets) | Dashboard and search reads within 2 seconds on the demo dataset; EVC Planner result within 15 seconds for the demo instance; document extraction asynchronous, typically under a minute per document. |
| Accessibility | Keyboard navigation, readable contrast, non-colour status indicators, clear errors. |
| Localisation | All user-facing text externalised so English and Hindi can be supported; Indic OCR language packs where available. The prototype ships English only. |
| Maintainability | Modular services, documented APIs, automated tests, versioned configuration. |
| Scalability | New regions, application types, stages and notification channels addable without changing the core model. |

## 11. Success Metrics

All figures below are prototype targets set by the team and measured on clearly labelled synthetic data. Replace them with measured baselines if AICTE supplies any.

| Metric | How measured | Prototype target |
| --- | --- | --- |
| Cases with visible owner, stage and next action | Query over demo dataset | 100% |
| Manual follow-up steps per case | Scripted scenario: manual process steps vs FlowWise steps | Clear reduction, with both counts shown |
| Time to reconstruct a case history | Timed task from search to full timeline | Under 30 seconds |
| Obligation extraction quality | Precision, recall and F1 on a labelled synthetic document set; share of accepted candidates with valid source quote | Report results; target at least 90% on dates and parties for text PDFs; 100% grounded quotes |
| SLA clock correctness | Test cases with hand-computed party times | 100% of cases match |
| EVC Planner constraint violations | Automatic checker on generated plans | 0 conflicts of interest, 0 unavailable experts |
| EVC Planner quality vs greedy baseline | Weighted ageing, travel and workload spread on the same instance | Better on at least two measures, with numbers shown |
| Invalid stage transitions blocked | Negative test suite | All blocked with a stable error and rule explanation |
| Reminders generated on time | Scheduler tests with simulated time | 100% of due reminders, 0 duplicates |
| Audit tamper detection | Mutate a stored event and verify the chain | Detected 100% of tries |
| Officer usability | Short task-based feedback session with team and mentors | Task completion without help |

## 12. Demonstration Script (about eight minutes, recorded)

Scenes run from seeded data after a reset. Scenes 3 and 6 use the demo clock so SLA pauses and escalations show without waiting. If the video must be shorter, shorten each scene rather than drop one: every scene proves a differentiator.

Workflow Studio (about 1:15). Admin builds a new Scrutiny + EVC combination, validates and dry-runs it; a second approver publishes it. A new case follows it.

Obligation Intelligence (about 1:30). Upload a synthetic approval letter and lease deed; show candidates with highlighted source text; confirm two, reject one; the register and reminders update.

Deficiency loop with clock-aware SLA (about 1:00). Officer returns a case; the clock visibly switches to the institution; the institution responds; the clock returns.

EVC Planner (about 1:15). Plan ten ready cases; show reasons, excluded experts and the greedy-baseline comparison; edit one assignment and watch the conflict check re-run.

Action Inbox (about 0:45). Show ranked items with factor breakdown; open the top item and resolve it.

Escalation (about 0:45). Advance the demo clock past the AICTE-held SLA; show the overdue task, its escalation history and the simulated email in the outbox.

What-If Simulator (about 0:45). Add two scrutiny officers to a region; compare ageing outcomes, with assumptions displayed.

Trust (about 0:45). Scan a generated letter QR; then use the labelled demo-only tamper tool to alter one stored audit record and show the chain verification fail at that event.

## 13. Risks, Dependencies and Mitigations

| Risk / dependency | Impact | Mitigation |
| --- | --- | --- |
| Handbook rules misunderstood or changing | Wrong workflows and thresholds | Complete the traceability matrix; versioned, configurable templates; mentor review |
| LLM invents or misreads obligations | False compliance records | Verbatim-quote grounding check, schema validation, officer confirmation, rule-based fallback, measured accuracy |
| Scheduler infeasible or slow on real constraints | Unusable proposals | Soft-constraint relaxation with penalties; time limit; explanation of conflicts; manual path |
| Simulation read as prediction | Misleading decisions | Permanent "simulation" label, visible assumptions, data-source tag |
| Scope too large for six people | Incomplete demo | Depth limits in section 14, cut-line order, shared API contracts early |
| No access to AICTE systems or APIs | No live integration | Documented adapters with mock implementations; do not claim integration |
| Sensitive institutional documents | Privacy and security exposure | Synthetic data, least privilege, private storage, audit, approved providers only |
| Prototype stack too heavy for the time available | Unfinished demo | Prototype profile in TRD section 3A (SQLite, in-process scheduler, local storage); the production stack stays a documented target |
| Handbook values taken from secondary sources | Wrong thresholds shown as fact | Rows marked Sourced - verify; mentor confirmation; every value configurable and tagged on screen |

## 14. MVP Depth, Cut-Lines and Roadmap

### Depth limits for the prototype

| Feature | Prototype depth |
| --- | --- |
| Workflow engine and Studio | Four templates plus one built live in the demo; conditions limited to a whitelist of predicates |
| Obligation Intelligence | Three document types (approval letter, lease deed, EVC report), English text, evaluated on a labelled synthetic set |
| Clock-aware SLA | Full engine with working-calendar support and tests |
| Simulator | Per-region, per-stage queueing model with officer-count and arrival-rate scenarios |
| EVC Planner | Single planning window, about 30 cases and 15 experts in the demo instance |
| Action Inbox | Deterministic weighted score with configurable weights |
| Trust layer | Hash chain, QR verification page and maker-checker on templates |
| Runtime profile | FastAPI, SQLite and React run locally with an in-process scheduler, local file storage and a simulated email outbox; Docker is not needed (TRD section 3A) |
| Demo dataset | Four regions, 12 institutions, 40 cases (about 30 ready for EVC planning), 15 experts, 12 labelled synthetic documents and one demo user per role; all synthetic |
| Demo controls | Demo clock fast-forward, one-click data reset and a labelled audit tamper tool, available only in demo mode |

### If time is short, cut in this order

Deficiency Assist and handbook retrieval.

Simulator polish (keep one working scenario).

Priority-score weight editor (keep fixed weights).

Extra document types for extraction (keep lease deed and approval letter).

Never cut: workflow core, clock-aware SLA, Obligation Intelligence with grounding, Workflow Studio, audit chain.

### Roadmap beyond the hackathon

Authorised integration with AICTE and institutional systems and an approved identity provider.

Calibrate simulator and risk views on real historical data after governance review.

Additional application categories, policy templates and notification channels.

Handbook-change impact analysis: compare a new handbook or circular with templates and flag affected rules and in-flight cases.

## 15. Definition of Done

All Tier 1 and Tier 2 functional requirements pass their acceptance criteria on the synthetic dataset.

The demonstration script runs repeatably from a setup script with seeded data and a one-click reset; Docker is not required for the prototype.

Every role and scope restriction is tested at API level.

Metric table in section 11 is filled with measured results, not estimates.

All demo data, simulated integrations and non-official rule values are labelled as such on screen.

The traceability matrix lists only validated values, or marks the rest as placeholders.

## 16. Open Questions

Which handbook provisions define each workflow combination, transition and return rule? SAC (Standing Appellate Committee) and SHC (Standing Hearing Committee) are now sourced; who sits on them and their exact place in each path are still open.

Which roles may assign, return, complete, verify and escalate at each stage? What are the official timelines and escalation hierarchy?

Which undertaking types and document categories matter most, and what do real approval letters and lease records look like (in anonymised form)?

What conflict-of-interest rules and expert-selection norms apply to EVC panels?

Which data fields and integrations, if any, are available to a student team?

What retention, hosting, residency and AI-provider restrictions apply?

SIH submission format: public copies of the 2026 idea template show a PDF of at most six slides with no video field, so the prototype video is linked from inside the PDF. Confirm against the official template; the evaluation criteria remain open.

## 17. Prototype Build Profile and Submission Packaging

The prototype proves every Tier 1 and Tier 2 requirement on synthetic data. The table states what is real and what is simulated, so the video never implies a live AICTE integration.

| Capability | In the prototype | Shown as |
| --- | --- | --- |
| Workflow engine, Studio, maker-checker | Real and persistent | Live in the app |
| Clock-aware SLA and escalation | Real, driven by an injectable demo clock | Fast-forward control in the demo bar |
| Obligation Intelligence | Real extraction on synthetic PDFs; LLM optional, rule-based fallback always available | Highlighted source quotes; evaluation report |
| EVC Planner | Real CP-SAT solve with a greedy baseline | Plan view with reasons and excluded experts |
| What-If Simulator | Real SimPy runs on synthetic service-time distributions | Labelled simulation with assumptions shown |
| Action Inbox and dashboards | Real, computed from seeded data | Factor breakdown per item |
| Email and SMS | Simulated outbox | Outbox page labelled simulated |
| Digital signature | Simulated signature block | Labelled simulated on the letter |
| AICTE portal and external systems | Not integrated; mock adapters only | Never shown as a live integration |
| Handbook rule values | Configurable placeholders unless marked Sourced - verify | Tag shown beside each value |

### Demo readiness

One demo user per role (11), listed on the login screen and labelled as demo accounts.

A persistent banner states that all data is synthetic and integrations are simulated.

A demo bar offers clock fast-forward, data reset and the audit tamper tool; it appears only when demo mode is on.

The LLM can be switched off; the demo script must still pass using rule-based extraction.

### Submission packaging

The idea submission is a PDF of at most six slides (from a public copy of the template; verify on the portal). Put the video link on the Technical Approach slide as clickable text.

Upload the recording to YouTube as Unlisted, not Private, so evaluators can open it; check that it plays while signed out.

Keep the video to the eight scenes in section 12 and record from the seeded dataset right after a reset.
