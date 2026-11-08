# Research brief

VERIFIED: reviewed November 8, 2026. Product code is a React workbench over a local Python privacy pipeline. Audience/device assumptions: researchers and technical reviewers, primarily laptop; trust depends on visible provenance rather than security promises.

| Opened reference | Observed structure / useful principle | Adopt / avoid (design inference) |
|---|---|---|
| https://presidio.dataprivacystack.org/ | Entity recognition, anonymization and decision-process documentation | Separate detection from proof of protection; avoid absolute guarantees |
| https://docs.private-ai.com/ | Entity detection, container playground, supported entities | Make input and output inspectable; avoid pretending every entity is supported |
| https://langfuse.com/docs | Tracing, evaluation, metrics separated in navigation | Separate execution and evidence; avoid overloaded overview |
| https://arize.com/docs/phoenix | Tracing, datasets and experiments distinct | Show source of evaluation; avoid context-free scores |
| https://docs.langchain.com/langsmith/observability | Individual traces through production metrics | Allow run inspection; avoid marketing statistics |
| https://www.synthesized.io/ | Data masking and testing are explicit product tasks | Task-led labels; avoid copying promotional proof |
| https://primer.style/ | Product UI and brand UI separated | Quiet app chrome; no marketing hero inside workbench |
| https://www.carbondesignsystem.com/ | Enterprise components, tokens and data visualization | Consistent spacing and table hierarchy |
| https://design-system.service.gov.uk/ | Components, patterns, accessibility | Explicit labels, useful error messages |

VERIFIED: fetched page text, not a pixel-level audit of these sites. Their implementation stacks, bundle sizes and private workflows are UNKNOWN. No third-party component code copied. Existing React is sufficient for the bounded tables and flow; adding a chart/grid library would not solve a necessary subproblem. Repository license/maintenance comparison is excluded because no third-party repository is adopted. Gretel and Carbon's specific table URL failed to fetch; no claims rely on them.

ASSUMED synthesis: users need to answer: what changed in this document; where did processing run; what evidence supports the result? Keep source/output inspection, route labels and audit records. Avoid neon security theater, animated graphs implying live progress, and fabricated precision. Use a pale neutral canvas, restrained teal accent, readable document typography, minimal state-transition motion. Trust cues are actual connection state and clearly scoped validation, not certification badges.

VERIFIED standards references opened: https://www.w3.org/WAI/WCAG22/quickref/ and https://web.dev/articles/vitals . Targets: AA contrast, keyboard support and reflow; field LCP <=2.5s, INP <=200ms, CLS <=0.1. Field measurements require real traffic and are NOT RUN locally.
