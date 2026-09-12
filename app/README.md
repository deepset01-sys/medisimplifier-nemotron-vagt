# MediSimplifier — Safety Gate Demo

A single-page demo of the MediSimplifier diagnosis-drop safety gate, built on two
real, captured cases from the 1,001-item student self-audit
(`../results/student_audit_review.json`) — nothing synthetic, nothing staged.

## The two cases

**FLAGGED — Case #44:** the plain-language rewrite silently dropped the diagnosis
"liquoral hypotension" (intracranial hypotension). Llama-3.3-70B and Qwen3-32B
passed it; Nemotron Nano flagged it; the gate returned DISAGREE. Both LLM auditors
(Claude Sonnet 5 + Gemini 2.5 Pro) independently confirmed the drop.

**SAFE — Case #820:** a faithful COVID-19 rewrite. All three judges SAFE; the gate
passes it — showing the gate is a real discriminator, not a flag-everything alarm.

Toggle between them with the **"Show SAFE example" / "Show FLAGGED example"** button.

## The two acts (FLAGGED case only)

**Act 1 — the gate catches the drop.** Cached real verdicts — stable,
auditor-confirmed. The red highlight shows exactly what was dropped.

**Act 2 — why trust the panel?** *"We don't trust one call. We measured it."* The
audit_panel ΔΦ_V leaderboard ranks 5 candidate judges by how much each fixes the
panel's diagnosis blind spot. Nemotron Nano recommended: +0.0706, CI [0.0552, 0.0866].

**"Run audit_panel live →" button:** calls `/v1/audit_panel` — deterministic (same
answer every call, pure CPU). Returns the same recommendation every time.

## Setup

```bash
npm install && npm run dev
```
→ http://localhost:5173

## Live button — prerequisite

The demo makes exactly **one** live call: the **"Run audit_panel live →"** button,
which POSTs to `/v1/audit_panel` (proxied by Vite to the Nebius endpoint). That route
is **pure CPU** — it re-ranks pre-computed verdict files and calls no models — so it
returns in ~1 s, deterministically, the same recommendation every time.

It does require the **endpoint-v5 (Safe Endpoint)** container to be running, since that
is what *serves* the `/v1/audit_panel` route. Start it from the Nebius Console before
presenting. It does **not** need the Qwen3-32B dedicated judge endpoint or any GPU
inference — audit_panel touches neither.

If endpoint-v5 is down, the button falls back gracefully to *"showing the committed
receipt"* (the same numbers as the static Act 2 chart), so the demo still works fully —
you just don't get the live round-trip.

Note: **Act 1 (the gate verdicts) is cached** — the demo does *not* call `/v1/simplify`
live — so the DISAGREE result and the auditor confirmation display with no endpoint
running at all.

Research prototype — **not for clinical use.**
