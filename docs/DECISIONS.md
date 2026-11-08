# Decisions and gap audit

ASSUMED: redesign the existing local research web application, not create a public marketing site or desktop installer. Preserve Python pipeline and API contracts. No approval needed for a separate deployment: this task changes the local project only. Product classification T5 + T6; included document workspace, pipeline, evaluation, audit and guide. Excluded marketing, mobile-native, desktop-native and multi-tenant surfaces.

VERIFIED: server.py provides health, run, audit and samples; pipeline/graph.py provides the displayed stage and retry structure. Historical evaluation snapshot contains five documents and 36.47% factual retention. No new runtime package installed. Existing React and Vite APIs checked against https://react.dev/reference/react and https://vite.dev/guide/. Package versions are recorded in package-lock.json; latest registry versions were not queried because no dependency change was needed. Custom icons are original SVG paths. System fonts are used without redistributing font files.

ASSUMED: light-only reading environment; local draft held in memory rather than localStorage to avoid persisting sensitive source text. Processing runs only against the actual service. A missing service never produces simulated success. Existing presets are labeled Sample data; names/organizations are test fixtures, not authenticated records. Exports of full results include explicit sensitive-content notices. Evaluation JSON is a build-time snapshot copied from the repository; changing the original requires refreshing the copy.

## Gap audit, before build and delivery

| Topic | Decision / reason |
|---|---|
| Authentication, roles, payments | Exclude: local research prototype has no supporting endpoints; deployment with multiple users requires backend work |
| Onboarding | Include sample selector, explanatory empty state and guide |
| Settings | Exclude account/preferences panels without supported actions; API base configurable at build time |
| Notifications | Include inline status/errors and copy feedback; no notification service |
| Search | Include audit search and Ctrl/Cmd+K screen navigation |
| i18n / RTL | English UI; document input accepts automatic text direction. Full translation/RTL UI excluded pending product requirement |
| SEO, analytics, consent | Private app uses noindex and no analytics. No cookie banner needed for this implementation |
| Legal | Include truthful data-handling explanation, not fabricated legal policies. Formal terms/privacy review required for public release |
| 404 / 500 / offline | Unknown hash falls back to workspace; request errors and unavailable banner included. No service worker/offline processing |
| Transactional email | Exclude: no account/email backend |
| Help / support | Persistent guide link and keyboard-accessible navigation; no invented support address |
| Changelog / status | Connection status included; public status/changelog excluded |
| Dark mode | Exclude: deliberate single light theme |
| Keyboard shortcuts | Include Ctrl/Cmd+K and native Escape dialog dismissal |
| Print | Include print stylesheet |
| Favicon, app icons, OG, manifest | Include SVG favicon; exclude installable-app assets and social sharing images for private research UI |
| Empty states | Include no source, no result, no audit records, no filter matches, unavailable/error/loading |
| Export / deletion | JSON export for results, evaluation and filtered audit. Clear in-memory draft. Persistent deletion excluded: no API |
| Error monitoring | Visible client errors; no third-party telemetry for sensitive documents |
| Backups / sync | Exclude from frontend; audit persistence remains backend-owned |
| Rate limits / abuse | Existing local API unchanged; production hardening is outside frontend scope |
| Performance budget | <=100 kB gzip initial JS, <=15 kB gzip CSS; no raster assets/remote fonts |
| Accessibility statement | Guide documents supported interactions; no claim of certified compliance |

UNKNOWN: production hosting/origin, dataset provenance approval, server timestamp timezone, exact legal obligations, full backend security posture. These do not block local UI implementation. No claims of tamper-proof logging, guaranteed privacy or complete detection.

ASSUMED table scope: recent 100 records, sort by run sequence, search, route filter and detail inspection. No resize/pinning/grouping/virtualization or bulk mutation because this bounded read-only dataset does not justify them. No date-comparison controls because an arbitrary recent subset cannot support honest period comparisons. Audit query filters are session-only, not shareable URL state; hash screen navigation is shareable.

## Subsequent usability review

VERIFIED: first-use sample CTA, task suggestions, undo, leave-page guard, processing timer, stop-waiting, response validation, redacted-only export, command dialog accessibility and readable audit details are implemented. API input limits are 30,000 document / 2,000 task characters. Local CORS is restricted to the documented application origins. Failed redaction checks now stop before routing; model outages are failures rather than fabricated answers. Backend regression tests isolate persistence and replace external dependencies; live inference is still unverified. These changes supersede the earlier decision to leave all backend behavior unchanged.
