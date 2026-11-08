# PrivacySwarm frontend

React + TypeScript + Vite research workbench. All main screens were redesigned with a shared light token system: document workspace, pipeline, recorded evaluation, audit log, guide.

## Run

From this directory: `npm install` if dependencies are absent, then `npm run dev`. Open the printed Vite URL. Start the existing backend separately with `python server.py` from the parent directory using its configured Python environment and requirements. Development Vite proxies `/api` to `http://127.0.0.1:8000`.

## Build and serve

`npm run build` checks TypeScript and writes `dist`. `npm run lint` runs oxlint. The Python server serves the built frontend and API together on port 8000. For another API origin, set `VITE_API_BASE_URL` before building; this public setting must never contain secrets. A separate static host must proxy `/api` or use that setting and allow the intended origin. No deployment was performed.

## Data

Document drafts/results live in memory and clear on reload. Processing uses the real API; offline UI never fabricates a response. Presets are labeled Sample data. Evaluation is a static copy of `../evaluation/results_20261105_215814.json`, not a live benchmark. Refresh `src/data/evaluation.json` when intentionally publishing new evidence. Full-result export contains original sensitive content.

## Verification

See `../QA_REPORT.md` for comprehensive verification details, including responsive layout checks (320px–1920px), automated accessibility audits, and test results. No test result proves absolute backend privacy guarantees.

Design/research documents are in the parent directory. No external fonts, analytics, or raster assets load in the active UI. This is a local research prototype; production authentication, authorization and rate limiting require backend work.

## Usability and reliability update

- Start with **Try a sample document**, choose a suggested task, then **Process document**.
- Clear/sample replacement supports one-level undo. Drafts are memory-only; the page warns before leaving with a nonempty document.
- **Stop waiting** stops the browser request only. The server may still complete it; inspect Audit log before repeating a run.
- **Save redacted text** exports only the redacted output; **Export full result** includes sensitive original values.
- Limits: 30,000 document characters and 2,000 instruction characters; recent audit queries support 1-100 records.
- The local Python handler permits browser origins on localhost/127.0.0.1 ports 8000, 5173 and 5174. A different deployment must intentionally configure its allowed origin; changing VITE_API_BASE_URL alone does not authorize it.
- Backend regression tests: `python tests/test_app.py` from the parent directory. They use isolated SQLite and dependency/model test doubles, not real inference. Frontend regression tests: `node review/usability.cjs` and `node review/edge.cjs` while Vite is serving at port 5173. See QA_REPORT.md for environment-specific executable paths and unavailable checks.
