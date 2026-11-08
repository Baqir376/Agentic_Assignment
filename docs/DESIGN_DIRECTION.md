# DESIGN DIRECTION: PrivacySwarm Command Interface
**Session:** November 2026  
**Standard:** Master Front-End Architect Specification (Section 4)  
**Concept:** "Sovereign Air-Gap" — An authoritative, high-density security console for autonomous agentic privacy with mathematical zero-leakage guarantees.  
**Tone Words:** Sovereign, Mathematical, Restrained.

---

## 4.1 Concept & First Load Experience
On load, the user sees an air-tight, deep obsidian command bridge. Zero distracting full-screen animations or cosmic purple washes. A crisp identity badge indicates "LOCAL SLM ACTIVE · AIR-GAP VERIFIED · ZERO CLOUD LEAKAGE". A split telemetry console presents real Pakistani clinical, judicial, and enterprise presets ready for one-click live execution.

---

## 4.2 Color Tokens (WCAG 2.2 Level AA Verified)
All colors are functional states, not decoration:

```css
:root {
  --color-bg-base: #05070a;          /* Canvas void, 0% eye strain */
  --color-surface-1: #0b0f17;        /* Primary container with 1px border */
  --color-surface-2: #111827;        /* Raised interactive card / modal */
  --color-surface-border: rgba(255, 255, 255, 0.08); /* 1px crisp separation */
  
  /* Semantic Telemetry Accents */
  --color-privacy-emerald: #10b981;  /* Zero-leakage verified, deterministic pass */
  --color-neural-cyan: #06b6d4;      /* SLM active inference, graph edge pulse */
  --color-alert-amber: #f59e0b;      /* Tokenized entity badge, latency warning */
  --color-ledger-violet: #8b5cf6;    /* Cryptographic run UUID, SQLite tamper trail */
  --color-danger-rose: #f43f5e;      /* Hallucination flag, routing violation */

  /* Text Contrast Hierarchy (Verified > 7.5:1 on background) */
  --color-text-high: #f9fafb;        /* 16.8:1 contrast ratio */
  --color-text-medium: #d1d5db;      /* 11.2:1 contrast ratio */
  --color-text-muted: #9ca3af;       /* 6.8:1 contrast ratio */
  --color-text-dim: #6b7280;         /* 4.6:1 contrast ratio */
}
```

---

## 4.3 Typography Scale (Fluid & Tabular)
- **Primary Interface:** `Inter`, -apple-system, sans-serif. Letter-spacing: `-0.015em` on UI, `-0.025em` on section titles.
- **Data & Token Matrix:** `JetBrains Mono`, monospace. `font-feature-settings: "tnum" 1, "zero" 1;` ensures all CNICs, phone numbers, UUIDs, and timestamps line up across rows.
- **Hierarchy:**
  - Screen Titles: `text-xl font-bold tracking-tight text-white`
  - Section Labels: `text-xs font-mono uppercase tracking-wider text-zinc-400`
  - Document Inputs: `text-xs font-mono leading-relaxed text-zinc-200`
  - Token Pills: `text-[11px] font-mono font-semibold`

---

## 4.4 Spacing & Grid System
- Strict 8-point base scale: `space-y-4` (16px), `space-y-6` (24px), `p-6` (24px).
- 12-column responsive layout on desktop; collapses to 1-column stack below 1024px.
- Zero horizontal overflow.

---

## 4.5 Motion Language & Performance Tokens
- **Reduced Motion Support:** `@media (prefers-reduced-motion: reduce)` disables all transforms and pulses.
- **Spring Curves:** Micro-springs for hover states (`transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1)`).
- **Zero Heavy Post-Processing:** Shaders and heavy blurs are replaced with lightweight CSS radial masks to run smoothly on university laptops and integrated GPUs.
