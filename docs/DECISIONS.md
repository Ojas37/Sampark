# Implementation decisions

- The v3 PRD and TRD Word attachments are mirrored here as Markdown exports; the original documents remain at the workspace root.
- The prototype uses the TRD 3A profile: FastAPI, SQLite in WAL mode, local storage, simulated notifications, and an injectable demo clock.
- Every institution, person, document, rule value and workflow in the seed data is synthetic; demo workflow mappings and SLA values remain tagged as placeholders.
- AICTE integrations and email/SMS delivery are not connected; the UI labels them simulated.
- The initial implementation prioritizes a working, repeatable foundation and the core case/deficiency workflow; unimplemented areas remain visible as roadmap items rather than being represented as live integrations.
- EVC planning uses OR-Tools CP-SAT with a deterministic greedy baseline, independent post-solve hard-constraint validation, and confirmation recorded with case transitions in one database transaction.
- Capacity what-if results use SimPy and seeded synthetic arrival/service distributions; they are labelled as simulations, not forecasts.
