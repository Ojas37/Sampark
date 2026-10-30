# AICTE FlowWise

AICTE FlowWise is a local Smart India Hackathon prototype for approval workflow automation, compliance monitoring and alert management. It uses synthetic demo data only. AICTE systems are not connected, and notifications are simulated.

The supplied specifications are available as [PRD v3](docs/PRD_v3.md), [TRD v3](docs/TRD_v3.md), and the [build prompt](FlowWise_Copilot_Prompt.md). All non-validated rule values are explicitly tagged as placeholders; see [implementation decisions](docs/DECISIONS.md).

## Run locally

### Windows

Install Python 3.11, Node.js 20.19+ and npm, then run:

```powershell
.\run_dev.ps1
```

The script installs dependencies, seeds the database, and starts the FastAPI API on `http://localhost:8000` and the Vite UI on `http://localhost:5173`. API docs: `http://localhost:8000/docs`.

### macOS / Linux

Install Python 3.11, Node.js 20.19+ and npm, then run:

```bash
chmod +x run_dev.sh
./run_dev.sh
```

For manual setup, install `requirements.txt`, run `python backend/scripts/seed.py`, then start `uvicorn backend.app.main:app --reload --port 8000` and `npm install && npm run dev` from `frontend/`.

## Demo accounts

All accounts use password `demo1234`. Select an account on the login screen:

| Role | Email |
|---|---|
| Institution applicant | `institution_applicant@demo.test` |
| Scrutiny officer | `scrutiny_officer@demo.test` |
| EVC coordinator | `evc_coordinator@demo.test` |
| EVC expert | `evc_expert@demo.test` |
| SAC/SHC member | `sac_shc_member@demo.test` |
| Regional officer | `regional_officer@demo.test` |
| Compliance officer | `compliance_officer@demo.test` |
| Senior management | `senior_management@demo.test` |
| System administrator | `system_admin@demo.test` |
| Second approver | `second_approver@demo.test` |
| Auditor | `auditor@demo.test` |

## Reset and verify

`python backend/scripts/seed.py` resets and deterministically recreates all demo data. The demo-only API controls are restricted to `SYSTEM_ADMIN`. Run `python backend/scripts/demo_check.py` and `python -m pytest` from the workspace root.

The implemented prototype includes JWT/Argon2 demo login, region/institution-scoped reads, 40 synthetic cases, the scrutiny-deficiency-response loop with business-hour SLA attribution, four published workflow definitions, hash-chained audit verification and demo tamper detection. It also includes a deterministic CP-SAT EVC proposal with availability, expertise, conflict and workload constraints; a greedy baseline; plan persistence and confirmation with simulated applicant notifications; an explainable priority inbox; and a seeded SimPy capacity comparison.

The three headline differentiators are now built end to end:

- **Obligation Intelligence (FR-10).** A deterministic, offline rule-based extractor reads synthetic approval letters, lease deeds and EVC reports and proposes obligations and validity fields. Each candidate carries the source page, a verbatim quote and a confidence value; candidates whose quote is not found on the cited page are discarded. Relative deadlines ("within N days of issue") are resolved against the document date by code, not a model. An officer accepts, edits or rejects each candidate; only accepted items create undertakings with provenance. Documents can also be added by pasting synthetic text (use a form feed to split pages). An LLM path can sit behind this later; the demo needs no external provider.
- **Workflow Studio with maker-checker (FR-14).** Workflow definitions are versioned graphs. The validator enforces single start, terminal reachability, role coverage and a predicate whitelist, and a dry-run walks a synthetic case to a terminal stage. An administrator drafts and submits a new version; a second approver publishes it (the approver must differ from the proposer); publishing retires the previous version and new cases follow the new one.
- **Letters and QR verification (FR-17).** Deficiency notices and EVC schedules render to a ReportLab PDF with a SHA-256 fingerprint, a simulated signature block and a QR code. A public, unauthenticated verification page (`/verify/:token`) reports document type, issue date and status, and can confirm the stored file matches its fingerprint, without exposing sensitive content.

Full alert/escalation ladders and the complete eight-scene rehearsal remain to be finished; the UI labels any remaining gaps instead of presenting them as working integrations.

### Local Python note

The repository ships without a virtual environment. On first run, create one with the local interpreter and install dependencies: `python -m venv .venv; .venv\Scripts\python.exe -m pip install -r requirements.txt`. The stack runs on Python 3.11-3.13.

## Eight-scene recording checklist

The source PRD's planned recording covers Workflow Studio, Obligation Intelligence, deficiency/SLA, EVC planning, Action Inbox, escalation, simulator and trust/audit in about eight minutes. The current build supports deficiency/SLA, EVC planning, Action Inbox, simulator and audit verification. The remaining scenes are not yet finished end-to-end flows; do not present them as live functionality.

Before recording, reset the seeded dataset, use 1080p, hide browser bookmarks, and keep the synthetic-data and simulated-integrations banner visible. Do not present placeholder or `sourced_verify` values as official AICTE rules.
