# AICTE FlowWise - full Copilot prompt

Use this file as one paste if you want everything in a single message, or unzip the kit and let Copilot load the brief automatically. Part 1 is the master brief. Part 2 holds the phase prompts: paste them one at a time after Part 1, and do not skip an exit check.

---

# PART 1 - MASTER BRIEF

# AICTE FlowWise - prototype build brief

You are building the **AICTE FlowWise prototype** for Smart India Hackathon 2026 (problem statement SIH26262). Specs: `docs/PRD_v3.md` (what) and `docs/TRD_v3.md` (how). The result must run locally, be recordable as an 8-minute demo (PRD section 12), and work repeatably from seeded synthetic data.

Priority when sources disagree: this brief > TRD section 3A (prototype profile) > rest of TRD > PRD.

## Working rules
1. Build phase by phase (phases are in `PROMPTS.md`). After each phase: run the tests, start the app, fix failures, then continue. Do not stop to ask questions: choose the simplest option consistent with the docs and log it in `docs/DECISIONS.md` (one line each).
2. Never invent AICTE rules. Every rule value (SLA hours, windows, thresholds, template mapping) lives in seed config with a tag `placeholder` or `sourced_verify` (PRD section 6) and the UI shows the tag beside the value.
3. All data is synthetic: institutions are "Demo Institute of Technology 01..12". No real people, institutions or documents. A banner on every page says: "Synthetic data. Integrations simulated."
4. Every state change goes through a service function that, in ONE database transaction, writes the change and appends a hash-chained audit event. Routes never write directly.
5. `Clock.now()` is the only source of time. Never call `datetime.now()` or `utcnow()` outside `clock.py`.
6. Deterministic: fixed seeds for data generation, CP-SAT (random_seed=42, num_workers=1) and SimPy.
7. Runs on Windows, macOS and Linux with no Docker, Redis, PostgreSQL, MinIO, Tesseract or GPU.
8. Consistent error shape `{"error": {"code", "message", "details"}}`, type hints everywhere, Pydantic v2 schemas, small modules.
9. AI is advisory. With `LLM_PROVIDER=none` the whole demo must still pass.

## Stack
- Backend: Python 3.11 or 3.12, FastAPI, Uvicorn, SQLAlchemy 2.x (`create_all` is fine, no Alembic needed), Pydantic v2 and pydantic-settings, SQLite (WAL), PyJWT, argon2-cffi, APScheduler, PyMuPDF, reportlab, qrcode[pil], ortools, simpy, numpy, python-dateutil, dateparser, google-genai (optional), pytest, httpx, hypothesis.
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, `@xyflow/react` (React Flow), Recharts, react-router-dom, `@tanstack/react-query`, lucide-react. Palette: navy `#1F3A5F`, teal `#0E7C7B`, light grey surfaces; dense, professional, readable at 1080p; status shown by text plus colour.
- Layout: `backend/app/{main.py,config.py,db.py,clock.py,security.py,models/,schemas/,services/,routers/,seed/,tests/}`, `backend/scripts/{seed.py,reset.py,demo_check.py,evaluate_extraction.py}`, `backend/data/{files,seed_docs}`, `frontend/src/{pages,components,api,auth}`, `docs/`, `README.md`, `run_dev.ps1`, `run_dev.sh`.
- `.env.example`: `DATABASE_URL, JWT_SECRET, DEMO_MODE=1, LLM_PROVIDER=none|gemini, GEMINI_API_KEY, GEMINI_MODEL, PUBLIC_BASE_URL, STORAGE_DIR`.

## Roles and demo users
11 roles: `INSTITUTION_APPLICANT, SCRUTINY_OFFICER, EVC_COORDINATOR, EVC_EXPERT, SAC_SHC_MEMBER, REGIONAL_OFFICER, COMPLIANCE_OFFICER, SENIOR_MANAGEMENT, SYSTEM_ADMIN, SECOND_APPROVER, AUDITOR`. One demo user per role: `<role lowercase>@demo.test`, password `demo1234`, listed on the login page as demo accounts. Scope: officers and coordinators have a region, applicants have an institution; deny by default; enforce in a FastAPI dependency `require(roles, scope)`.

## Reference data (all tagged placeholder unless noted)
- 4 synthetic regions with coordinates: WR (19.08, 72.88), SR (13.08, 80.27), ER (22.57, 88.36), NR (28.61, 77.21). Business calendar: Mon-Fri 10:00-18:00 IST, three demo holidays.
- Application types and template mapping (table `application_type_template`, editable): `INTAKE_OR_COURSE` "Increase In Intake or New Course" -> `SCRUTINY_EVC`; `NEW_PROGRAM_OR_LEVEL` "New Program or New Level" -> `EVC_SHC`; `DEMO_SCRUTINY_ONLY` -> `ONLY_SCRUTINY`; `DEMO_EVC_ONLY` -> `ONLY_EVC`. Mark the mapping `placeholder`.
- `sourced_verify` rows (PRD section 6): EVC constituted by the Council, visit mode physical/online/hybrid; appeal to SAC within 7 days of LoR upload; State/University views 21 days; no LoA/EoA after 30 April. Show these in an admin "Rules and traceability" page with their tags.
- Documents types: `APPROVAL_LETTER, LEASE_DEED, EVC_REPORT, DEFICIENCY_LETTER, OTHER`. Deficiency categories: 6 generic ones.

## Workflow engine (TRD section 5)
- Template = JSON graph `{template, version, effective_from, start, stages[], events[], transitions[]}`; cases pin `template_version`. Stage types `task|terminal`. `sla_hours` are business hours.
- Four published templates: `ONLY_SCRUTINY` (SCRUTINY->DONE); `SCRUTINY_EVC` (SCRUTINY->EVC->DONE, EVC->SCRUTINY return with reason); `EVC_SHC` (EVC->SHC->DONE; SHC role `SAC_SHC_MEMBER`; predicate `shc_recommendation_recorded`); `ONLY_EVC` (EVC->DONE). SLA placeholders: SCRUTINY 120, EVC 240, SHC 120.
- In-stage events never change the stage, they switch the SLA holder: `ISSUE_DEFICIENCY` (reason required, holder INSTITUTION), `SUBMIT_RESPONSE` (holder AICTE_OFFICER), `CONFIRM_VISIT` (holder EXTERNAL_COMMITTEE), `RECORD_EVC_REPORT` (holder AICTE_OFFICER).
- Predicate whitelist (pure functions over stored records): `no_open_deficiency, open_deficiency, docs_verified, evc_report_received, shc_recommendation_recorded, visit_confirmed`, combined with `all/any/not`. No eval, no arbitrary expressions.
- Transition algorithm: load pinned version -> check event allowed -> evaluate predicates server-side -> check role, scope, reason -> ONE transaction (write transition, close SLA segment, open next segment, create next task, append audit) -> after commit recompute inbox scores and run alert scan. `Idempotency-Key` header required; optimistic lock on `application_workflows.version`. Stable error codes: `TRANSITION_NOT_ALLOWED, PREDICATE_FAILED, REASON_REQUIRED, FORBIDDEN_ROLE, VERSION_CONFLICT`; the error `details` names the blocking rule.
- Studio: validation (one start, terminal exists, reachability, every non-terminal reaches a terminal, roles exist, whitelisted predicates only, return transitions need reason and go backwards), dry-run (walk every path on a synthetic case, report stuck paths), state machine `DRAFT -> VALIDATED -> SUBMITTED_FOR_APPROVAL -> PUBLISHED -> RETIRED` plus `REJECTED`; approver must differ from proposer; PUBLISHED versions are immutable; UI shows a diff against the previous version.

## SLA clock (TRD section 6)
Segments `(stage_task_id, holder, started_at, ended_at, start_event, end_event)`; holders `AICTE_OFFICER, INSTITUTION, EXTERNAL_COMMITTEE, SYSTEM`. `business_seconds(start, end, calendar)` in Python over working intervals (unit-tested on weekends, holidays, partial days). Breach and escalation use AICTE_OFFICER time only. Reports: time held per party per stage per region. Hypothesis tests: segments never overlap and sum to task lifetime in business time.

## Obligation Intelligence (TRD section 7)
Upload -> validate (extension, MIME, signature, size, SHA-256) -> store under generated key in `STORAGE_DIR` -> PyMuPDF text per page -> classify (keyword rules, optional LLM second opinion) -> extract -> validate -> review queue -> confirm.
- LLM gateway `extract(doc_type, pages) -> JSON` via Gemini with a response schema (`GEMINI_MODEL`, default `gemini-2.5-flash`); every call logs provider, model, prompt version, latency, validation outcome in `extraction_runs`. If the LLM is off, fails, or returns invalid output twice, use the rule-based extractor (sentences containing shall/undertake/must/within/by + dates) and show "rule-based".
- Output contract as TRD section 7.2: `obligations[]` (category, description, responsible_party, due{kind: absolute|relative, expression}, source{page, quote}, confidence) and `validity_fields[]` (field, value, source).
- Validation: schema; quote must appear verbatim on the cited page after whitespace normalisation, else the candidate is DISCARDED (counted, never shown); relative deadlines such as "within 90 days of issue" are resolved by a custom regex parser (`resolve_due(expr, doc_date)`; weeks, months, days; dateparser only for absolute dates); due before document date is flagged.
- Review UI: candidates beside the page text with the quote highlighted (return page text and character offsets; no PDF.js needed). Accept, edit or reject. Accepted obligations create undertakings with provenance; accepted validity fields create document-validity records. Edits are stored next to the original.
- `scripts/evaluate_extraction.py` and `/evaluation/run`: precision, recall, F1 per field, valid-quote share, discard rate, for LLM and for the rule-based baseline on the 12 labelled documents. Match candidate to truth on category + resolved due date + description token overlap >= 0.6.

## EVC Planner (TRD section 8)
OR-Tools CP-SAT. Window = next 10 working days from `Clock.now()`. Variables `visit[c,d]`, `panel[c,e]`, `expert_day[c,e,d]`. Hard: one visit date per case, panel size met, expert available, no conflict record (expert-institution, same-institution group), required expertise tags covered, one visit per expert per day, per-expert cap (3 in window). Soft (weighted): maximise priority-weighted scheduled cases, reduce ageing, reduce travel (Haversine km between expert home region and case region, physical visits only; online visits cost 0), balance workload (minimise max-min load). Settings: 10 s limit, `random_seed=42`, `num_workers=1`; on timeout return best feasible plus gap.
- Explanations: per assignment, contributing factors; per excluded expert, the FIRST failing hard constraint in the order conflict, unavailable, tag mismatch, cap reached, already booked; per unscheduled case, which constraint family binds and the smallest change (widen window by N days, add an expert with tag X).
- `validate_plan(plan)` re-checks every hard constraint after coordinator edits and returns violations with names.
- Greedy baseline (oldest case first, earliest day with enough available experts, first available expert, ignoring travel and workload) on the same instance; compare scheduled count, priority-weighted ageing, total travel km, workload spread. Show both side by side.
- Confirming a plan emits `CONFIRM_VISIT` per case and writes notifications.

## Simulator (TRD section 9)
SimPy; stages SCRUTINY and EVC as queues per region with `officers` servers. Arrivals Poisson 1.2 per working day per region; service times lognormal (SCRUTINY median 12 business hours, sigma 0.5; EVC median 20, sigma 0.6; synthetic). Default officers: SCRUTINY 3 per region except NR with 2 (overloaded, backlog grows). Scenario inputs: officers per stage and region, arrival-rate multiplier, service-time multiplier. 30 replications, 120 working days, fixed seeds. Outputs: backlog over time (mean and 10-90 band), time-in-system p50 and p90 (mean and spread). UI always shows "Simulation under stated assumptions, not a forecast", the input table and `data_source = synthetic`. Test: an M/M/c case matches the Erlang C formula within tolerance.

## Priority score and Action Inbox (TRD section 10)
`score = w1*sla_pressure + w2*escalation_level + w3*obligation_urgency + w4*evc_readiness + w5*case_age + w6*blocking_others` with the exact factor definitions and default weights in TRD section 10 (0.35, 0.20, 0.15, 0.10, 0.10, 0.10). Store factors and contributions per item; UI shows a stacked bar and the numbers; resolving the underlying condition removes the item; ties: older case first, then reference number.

## Alerts and escalation (TRD section 11)
Rules: `SLA_WARNING` (AICTE-held time >= 80% of SLA), `SLA_BREACH` (>= 100%), `DEFICIENCY_RESPONSE_DUE`, `UNDERTAKING_DUE_SOON` (<= 14 days), `UNDERTAKING_OVERDUE`, `DOC_EXPIRY` (<= 30 days). `SLA_BREACH` ladder: level 0 immediately to the assigned officer (in-app); level 1 after +16 business hours to REGIONAL_OFFICER (in-app plus simulated email); level 2 after +40 business hours to SENIOR_MANAGEMENT (simulated email). Idempotency key `rule_code + entity_id + window_id + level`. States generated, sent, failed, acknowledged, escalated, resolved. APScheduler scan every 30 s real time, plus immediately after any transition and any demo clock advance. Email and SMS write to `notifications`; an Outbox page lists them, labelled simulated.

## Trust layer (TRD section 12)
- Audit: `hash_n = SHA256(hash_{n-1} || canonical_json(event_n))`, canonical JSON = UTF-8, sorted keys, no whitespace, timestamps ISO-8601 UTC with microseconds and trailing Z. Single chain, process lock on insert. `GET /audit/verify` recomputes from genesis and returns first mismatching index. Audit page: events list, Verify button, result.
- Letters (deficiency notice, EVC schedule, confirmation): reportlab PDF from a template, SHA-256 stored, QR to `{PUBLIC_BASE_URL}/verify/{token}`, simulated signature block labelled. Public page `/verify/:token` shows document type, issue date, status (valid, superseded, withdrawn) and a file-upload hash match; nothing sensitive.
- Maker-checker also applies to `app_config` changes (weights, ladders).
- Demo support (only when `DEMO_MODE=1`, SYSTEM_ADMIN only, else 404): `POST /demo/reset`, `GET /demo/clock`, `POST /demo/clock/advance {working_hours | days}`, `POST /demo/tamper` (alters one stored audit row through a raw connection). A visible demo bar exposes these three controls.

## Seed scenario (must exist so the demo script works)
- 11 demo users, 12 institutions across the 4 regions, 15 experts (tags CIVIL, MECH, ELEC, CSE, MGMT, ARCH; availability over the 10-day window with gaps; 2 experts partly unavailable), 6 conflict records including one expert-institution pair that a naive plan would use.
- 40 live cases: `FW-2026-0001` fresh at SCRUTINY (template SCRUTINY_EVC) for the deficiency loop; `FW-2026-0002` at SCRUTINY with 110 of 120 AICTE-held business hours used (breaches after about 10 more hours on the demo clock); `FW-2026-0003` with an open deficiency held by the institution for 6 working days; about 30 cases at EVC stage ready for planning across all regions with varied priority (1-5), ageing, tags, panel size 2-3 and visit mode; the rest spread over SHC and DONE. 
- 60 completed historical cases with realistic segment history for dashboards and attribution; 3 undertakings (one due soon, one overdue), 2 documents expiring within 30 days.
- 12 synthetic PDFs generated by script with ground-truth JSON beside each (4 approval letters, 3 lease deeds, 3 EVC reports, 2 deficiency letters), varied phrasing, including one letter with three obligations: a clean one, a relative-deadline one ("within 90 days of issue") and one an unsupported claim the validator must catch. `approval_letter_01.pdf` and `lease_deed_01.pdf` are the demo documents.
- Default alert rules, ladders, priority weights, 4 published templates, a valid audit chain.

## API
Implement every endpoint in TRD section 14 including the additions (committee recommendations, list reads, baseline, config, notifications, audit events, evaluation, demo). Prefix `/api/v1`, OpenAPI docs on, request id on every response, role and scope enforced and audited on every state change.

## UI pages
Login (with demo accounts); layout with role-based nav, banner, demo bar; Action Inbox; Cases list and Case detail (timeline, SLA-by-party bar, documents, observations and deficiency, actions that call transitions and show the blocking rule on failure); Institution portal (my cases, respond to deficiency, upload); EVC queue and Planner (window, run, plan grid, reasons drawer, excluded experts, baseline comparison, edit with live validation, confirm); Compliance (undertakings register, extraction review, evaluation report); Workflow Studio (React Flow canvas, palette, properties panel, validate, dry-run, submit) and Approvals (diff, approve or reject); Dashboards (status, stage, region, ageing, expiry, attribution by party); Simulator; Alerts and Outbox; Audit; Rules and traceability; public `/verify/:token`.

## Definition of done
- `python backend/scripts/demo_check.py` runs the eight scenes of PRD section 12 through the API and asserts the outcomes (new template published by a second user and used by a new case; two candidates accepted and one rejected; holder sequence AICTE_OFFICER, INSTITUTION, AICTE_OFFICER; plan with zero violations that beats the baseline on at least two measures and a COI edit that is rejected; inbox items with factors; escalation events and a notification after advancing the clock; NR p90 time-in-system drops when 2 officers are added; letter verification match; tamper detected with the first bad index). It passes three times in a row, each after `POST /demo/reset`.
- `pytest` passes: transition validator, predicates, business-time arithmetic, SLA fixtures and Hypothesis properties, alert idempotency, priority factors, hash chain tamper detection, RBAC cross-region and cross-institution denial, maker-checker self-approval blocked, planner constraint checker, Erlang C check, `resolve_due`.
- README documents Windows and macOS/Linux setup in under 6 commands, the demo accounts and the recording checklist.

---

# PART 2 - PHASE PROMPTS


## Phase 0 - Scaffold
Read `.github/copilot-instructions.md`, `docs/PRD_v3.md` and `docs/TRD_v3.md` fully. Create the repo layout from the brief, backend and frontend skeletons, `config.py` (pydantic-settings), `db.py` (SQLite WAL), `clock.py` (Clock with demo offset), `security.py` (argon2 + JWT), the global error handler and request-id middleware, and `GET /health`. Frontend: Vite + React + TS + Tailwind, router, login page with the demo accounts list, role-based layout, synthetic-data banner. Write `run_dev.ps1` and `run_dev.sh` (backend on 8000, frontend on 5173) and a first README.
Exit check: both servers start; `GET /health` returns ok; the login page renders.

## Phase 1 - Foundation: data, auth, RBAC, audit, seed
Implement every table in TRD section 13 (including the new ones in the prototype profile) as SQLAlchemy models. Implement `POST /auth/login`, `GET /auth/me`, the `require(roles, scope)` dependency, the audit service with the hash chain and `GET /audit/verify`, and `scripts/seed.py` for reference data, 11 demo users, 12 institutions, regions, calendar and rule-tag rows. Tests: hash chain tamper detection, cross-region and cross-institution denial.
Exit check: `python backend/scripts/seed.py` is repeatable; `pytest` passes; verify returns valid on a fresh seed.

## Phase 2 - Workflow engine, SLA clock, cases
Implement templates (4 published, JSON graph), the predicate whitelist, the transition algorithm with idempotency key and optimistic locking, in-stage events, SLA segments, `business_seconds`, case endpoints (`/applications`, timeline, documents, observations, responses, transitions, `/sla`), and the case list, case detail and institution portal pages. Seed cases `FW-2026-0001` to `0003` and the 30 EVC-ready cases. Tests: invalid transitions blocked with stable codes, deficiency loop holder sequence, business-time cases, Hypothesis segment properties.
Exit check: in the UI, an officer returns FW-2026-0001 with a reason, the SLA bar shows time moving to the institution, the institution responds, time returns to the officer.

## Phase 3 - Workflow Studio and maker-checker
Implement template validation, dry-run, the publication state machine with proposer and approver identities, the diff, and the pages: Studio (React Flow canvas with stage, event and transition editing and role and SLA fields), validation messages, dry-run result, Approvals page. A new case must follow the newly published template while in-flight cases stay on their version. Tests: every validator rule, self-approval blocked, immutability of PUBLISHED.
Exit check: admin builds a Scrutiny + EVC variant, validates, dry-runs, submits; second approver publishes; a new case follows it.

## Phase 4 - Obligation Intelligence
Generate the 12 synthetic PDFs with ground-truth JSON (reportlab, script in `backend/scripts`), then build the pipeline, LLM gateway (Gemini plus rule-based fallback), `resolve_due`, candidate validation (verbatim quote check, discard counting), candidate endpoints, the review page with highlighted quotes, undertakings and document-validity records with provenance, and `evaluate_extraction.py` with an Evaluation page showing LLM versus baseline. Tests: quote validation, `resolve_due`, discard path, fallback path.
Exit check: with `LLM_PROVIDER=none` upload `approval_letter_01.pdf`, accept two candidates, reject one, see the register update; evaluation report renders.

## Phase 5 - EVC Planner and Action Inbox
Seed experts, availability and conflict records. Build the CP-SAT planner, explanations, `validate_plan`, the greedy baseline and comparison, plan confirm (`CONFIRM_VISIT`), then the planner page (window, run, grid, reasons drawer, excluded experts, baseline comparison, edit with live violation display). Build the priority score service and the Action Inbox page with factor breakdown. Tests: zero hard-constraint violations over 20 generated instances, same seed gives the identical plan, score factors.
Exit check: plan 10 ready cases with zero violations, better than the baseline on at least two measures; editing in a conflicted expert shows the violation.

## Phase 6 - Alerts, dashboards, simulator
Build rules, ladders and the scan (APScheduler plus on-demand), notifications and the Outbox page, alert acknowledge, dashboards with attribution by party (Recharts), the SimPy simulator with scenarios and the Simulator page. Tests: alert idempotency, ladder timing, Erlang C check.
Exit check: advancing the demo clock 4 working days makes FW-2026-0002 breach and escalate to level 1 with a simulated email in the Outbox; the simulator shows NR p90 dropping when 2 officers are added.

## Phase 7 - Trust layer and letters
Build letter generation (reportlab, SHA-256, QR, simulated signature block), `GET /letters/{id}`, the public `/verify/:token` page with file-hash match, the Audit page with Verify, and the demo-only tamper endpoint and button. Generate letters automatically for deficiency issue and EVC confirmation.
Exit check: scanning the QR (or opening the link) shows valid and a match; tamper then verify reports the first bad event.

## Phase 8 - Demo hardening
Implement the demo bar (clock advance, reset, tamper), `POST /demo/reset` under 10 seconds, `scripts/demo_check.py` covering the eight scenes exactly as the brief states, loading and empty states, consistent labels, and fix every bug found. Finish the README: setup, demo accounts, the eight-scene recording script with the exact clicks, and a recording checklist (reset first, 1080p, hide browser bookmarks, LLM on or off).
Exit check: `demo_check.py` passes three times in a row after resets; a dry run of the eight scenes in the UI takes about 8 minutes without a manual fix.
