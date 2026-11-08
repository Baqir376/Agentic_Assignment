# QA report - usability and reliability review

VERIFIED: November 8, 2026. This report supersedes the first redesign report. Tests cover the real UI and HTTP handler with clearly scoped model/API test doubles. They do not establish real-world model quality or complete privacy protection.

## Issues found and fixed

- Clearing a document or loading a new sample discarded the previous draft: added one-level undo, including the previous result/task, and a browser leave-page warning for nonempty drafts.
- First use and disconnected service were unclear: added one-click sample, suggested tasks, setup instructions, explicit disabled-button explanations, and separate API/model availability messaging.
- Progress stayed on step one: steps now advance, elapsed time is visible, and users can stop waiting. This aborts the browser request, not the server job; the UI states that distinction.
- Comparison copy omitted the original: now copies both texts. Added redacted-only text download alongside the full sensitive JSON export.
- Missing/invalid response fields could crash rendering: added runtime checks for displayed health, pipeline and audit fields, readable errors, and retention of prior audit records on fetch failure.
- Empty entity maps were blank: added an explanation that no detections do not prove absence of sensitive data.
- Command dialog lacked an explicit name, reliable search focus and an empty state: corrected, with search reset on reopen. Mobile trigger has an accessible name.
- Small labels and mobile comparison columns were difficult to read: increased key text sizes and stacked comparison on narrow screens. Audit detail now has readable fields with technical JSON behind a disclosure.
- Stale notifications persisted after editing or clearing: clear them on edits/failures and dismiss after six seconds.
- API accepted malformed values and unbounded audit limits: added shape, encoding, size and range checks with useful errors.
- Static file paths could escape the build directory: paths are resolved and checked before serving. Missing assets return 404 instead of HTML.
- Wildcard CORS exposed local API access to arbitrary browser origins: allowlisted local app origins and reject foreign-origin POST/preflight requests. This is not authentication.
- Model outages produced fallback text marked as successful answers: removed fallback answers; empty generation is a failure in the response and audit.
- Exhausted redaction validation continued to routing: now routes directly to audit without inference. Cloud processor also rejects unvalidated documents and instructions with detectable identifiers. These guards do not guarantee complete identifier detection.
- Health ignored configured Ollama URL/model: it now checks the configured endpoint and model availability.

## Executed checks

| Command / method | Actual result |
|---|---|
| `npm run build` in frontend | PASS: strict TypeScript and production Vite build |
| `npm run lint` | PASS: no reported warnings/errors |
| Production gzip size | JS 80.86 kB, CSS 4.92 kB, HTML 0.42 kB; within 100/15 kB JS/CSS budgets |
| `python tests/test_app.py` | PASS: 24 unittest cases. Actual HTTP handler on an ephemeral loopback port, real isolated SQLite, symbolic rules, validator and reinserter. External dependencies/model clients and LangGraph scheduler are test doubles; real scheduler NOT RUN |
| `node review/usability.cjs` | PASS: 18 scenario groups: first-use guidance, sample, tasks, clear/replace undo, steps, clipboard contents, redacted export contents, stale result clearing, invalid HTML/JSON results, zero entities, late result after stop, input limit, dialog behavior, audit search/filter/detail and malformed audit retention |
| Same browser suite: responsive | PASS: 5 screens x 6 widths (320,375,768,1024,1440,1920), no document horizontal overflow |
| Same suite: axe | PASS: 7 states, zero reported violations (5 screens plus populated comparison and command dialog) |
| Same suite: page errors | PASS: zero uncaught errors captured |
| `node review/edge.cjs` | PASS: 7 Microsoft Edge smoke checks: offline explanation, setup help, keyboard skip, command dialog, offline sample preparation, 320px reflow, reduced motion |
| Screenshot inspection | Reviewed desktop and mobile post-interaction captures plus clean initial desktop; fixed stale notices and mobile sentence spacing. PNGs in review |
| Existing contrast evidence | Previous numeric token checks: text/white 14.57:1, muted/background 5.14:1, accent/white 6.51:1. Those color tokens did not change |
| `npm audit --json` | INCOMPLETE: registry advisory endpoint could not be reached |
| Python environment discovery | `python` absent from PATH. Bundled Python 3.12 exists but lacks langgraph/langchain_ollama/httpx/dotenv |
| Dependency install attempt | `python -m pip install --target .runtime langgraph langchain-ollama langchain-groq python-dotenv --disable-pip-version-check --retries 0 --timeout 15` failed: no matching langgraph distribution from the configured package source. No successful install |

The testing suite asserted behavior across unittests, accessibility rules, and browser layout reflow. No real private document was submitted, no cloud inference was invoked, and existing audit records were not mutated by backend tests.

Initial browser assertions required test-harness corrections for Windows clipboard CRLF, rendered line breaks, and an exact input locator. The corrected suite passes. Tests assert behavior, not merely record it.

## Remaining limits / not run

- Live end-to-end local/cloud model inference and real LangGraph scheduling: NOT RUN, dependencies unavailable. No claim that model processing is operational here.
- Firefox/WebKit: NOT RUN; executables not installed. Chrome and Edge share Chromium and are not cross-engine coverage.
- Screen reader, full manual assistive-technology pass, physical touch devices, actual 400% browser zoom: NOT RUN. Keyboard automation and viewport reflow are narrower checks.
- Field Core Web Vitals, Lighthouse, long-running concurrency/load, broad penetration testing, fresh benchmark execution: NOT RUN.
- Stop waiting does not cancel backend computation; retries can create another run. Drafts/undo are in memory only. Offline processing is unavailable.
- API remains a local research service without accounts, role authorization or production abuse controls. Audit filters remain session-only. Public hosting needs an explicit deployment design.
- Detection can miss identifiers and generated answers can lose facts. No privacy certification or universal zero-leakage claim.

Known UI regressions observed in executed checks: 0. Total undiscovered defects: UNKNOWN. Evidence: `frontend/review/usability-results.json`, `edge-results.json`, test scripts and screenshots. Build output may change slightly with subsequent text-only edits.

