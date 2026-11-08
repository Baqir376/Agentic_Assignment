# Component inventory

VERIFIED: active entry is frontend/src/App.tsx. Previous glow, header, redactor, topology, metrics and ledger components were removed after replacement.

- App: owns screen navigation, API health, source draft, execution result, audit loading and filter state.
- Icon({ name }): original consistent stroke SVG; decorative and hidden from assistive technology.
- Empty({ title, children }): explanatory empty/loading presentation.
- TokenText({ text }): renders plain text and token marks; no HTML injection.
- Shell: persistent navigation, current-screen breadcrumb, connection state, native command dialog, skip link, guide/footer.
- Document desk: labeled sample selector, source editor, instruction input, processing/error states, four output views, copy and export.
- Pipeline: ordered selectable stages, retry annotations, inspector and actual health details.
- Evaluation: provenance banner, snapshot values, semantic table with labeled meters, scope limitation.
- Audit: search, route filter, sequence sort, bounded table, selected record detail, refresh/export, stale-data warning.
- Guide: workflow, data handling, keyboard support and limits.

Tokens and responsive behavior: frontend/src/index.css. API schemas: frontend/src/types/index.ts. Evaluation snapshot: frontend/src/data/evaluation.json. No additional component library.

Usability review additions: `frontend/src/api.ts` validates displayed response fields and defines input limits. App adds reversible draft replacement, suggested tasks, elapsed processing, stop-waiting, redacted-only export, and accessible command search. Server request/path/origin checks and pipeline failure guards are covered by `tests/test_app.py`; browser workflows by `frontend/review/usability.cjs` and `edge.cjs`.
