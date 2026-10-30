# MediSimplifier — demo page

A single-page app with two modes, Replay and Live, and the panel section below them.

## Replay — the page opens here

Replay shows the 28 cases chosen by [`docs/replay_set.md`](../docs/replay_set.md), recorded
once on the final endpoint image, from `replay_recording.json` (`replay.jsx`):

- **Part A:** 12 texts, each with the endpoint's full answer as Live shows it (the gate's
  verdict, the rewrite and, for a flagged rewrite, the explanation), whatever the gate said.
  A case says when its answer came from a repeated call, and a case with no usable answer
  in three attempts is shown as not recorded.
- **Part B:** 16 known-answer pairs, each with the gate's recorded verdict beside its
  committed one, grouped by the cell each pair was drawn from.

Replay sends nothing: it shows what the recording holds. Until `replay_recording.json` is in
the page, Replay says the cases are not in this version yet. Pasted text is never processed
in Replay: pasting switches to Live.

## Live

Live sends a text to a running Safe Endpoint, straight from your browser, and shows what
it returns: the safety gate's verdict (the three judges and the consensus), the rewrite,
and, for a flagged rewrite, the endpoint's explanation in its own words. It sends the same
request as the replay recording: the text, `max_tokens` 1,024 and flag mode, so the rewrite
is never withheld; the verdict is shown beside it.

- **Your own endpoint.** Deploy one with [`docs/REPRODUCIBILITY.md`](../docs/REPRODUCIBILITY.md)
  and paste its URL into the page; **Check endpoint** asks its `/health` whether it is ready
  (that check does not call the judges).
  The URL stays in the page: it is not saved and not added to the address bar.
- **The project's endpoints, on request.** The Safe Endpoint and its two judge endpoints are not kept running
  between demos (about $14 an hour together). To try Live on them at no cost to you, write to
  deepset01@gmail.com with the time you plan to look; they are started for your session and take about 8 to 10
  minutes to load, and you get an endpoint address to paste into the page. That endpoint has no
  authentication: use synthetic text only.
- **Where your text goes:** to that endpoint, nowhere else. This is not medical advice.
- **Browser access:** the endpoint answers browsers only from this page on GitHub Pages and
  from a local `npm run dev` (below); its `CORS_ALLOW_ORIGINS` setting replaces that list.
- **Waiting:** a rewrite and its check usually take under 30 seconds, or under 45 when the
  rewrite is flagged and the endpoint adds its explanation; a cold start takes longer. The
  page gives up after 5 minutes, and **Cancel** stops the wait at any time (the endpoint may
  still finish the request). Measured on a running endpoint in October 2026: 16 to 29 seconds
  for discharge summaries of about 1,000 characters, flagged ones included; the times above
  allow a margin.

## The panel section

**Why trust the panel?** *"We don't trust one call. We measured it."* The
audit_panel ΔΦ_V leaderboard ranks 6 candidate judges on 240 hand-verified items
(120 real dropped diagnoses + 120 paired controls — a 50% drop rate; ΔΦ_V depends on it,
README A8 threat 11). gpt-oss-120b recommended: +0.1220,
CI [0.1000, 0.1416] — statistically tied with DeepSeek-V4-Flash, chosen by a fewest-errors
tie-break (0 vs 7) that was added after the v2 result was known. DeepSeek's errors were
token-budget truncations; at a matched budget gpt-oss still wins, on specificity.
A collapsed **"What changed and why"** note explains that an earlier automated pass
recommended Nemotron Nano, and why that result did not survive hand-verified labels.

**"Run audit_panel live →" button:** calls `/v1/audit_panel` — deterministic (same
answer every call, pure CPU). Returns the same recommendation every time.

**"Try a different panel":** pick any 2+ of the 8 judges; the same endpoint recommends
which judge to add for that panel.

## Setup

```bash
npm install && npm run dev
```
→ http://localhost:5173. Open exactly this address: the endpoint's CORS allows it (not
`127.0.0.1`), and the dev server stops rather than move to another port if 5173 is taken.

## Live calls — CPU audit_panel service

The panel section makes live calls from two places — the **"Run audit_panel live →"** button and
**"Try a different panel"** — both POSTing directly to `/v1/audit_panel` on the
**CPU audit_panel service** (open to any origin; the URL is `AUDIT_ENDPOINT` in `demo.jsx`).
That route is **pure CPU** — it re-ranks pre-computed verdict files and calls no
models — so it returns in ~1 s, deterministically, the same recommendation every time.

That route is served by the **CPU audit_panel service** (`chambul/medisimplifier:audit-cpu-v2.1`)
— a slim CPU-only container with no vLLM, no GPU, and no API key (~$1–3/day while running).
It is kept running through the judging period;
if it cannot be reached, the page falls back as described below. It does **not** touch the H100 endpoint, the Qwen3-32B dedicated
judge, or any GPU inference — audit_panel touches none of them.

A live result is shown only if the response reports `benchmark: "MedSimp-JudgeBench-v2"`.
If the service is unreachable — or answers from any other pool — the button shows
*"Live service unavailable — the chart above is the committed v2 receipt"*, so the demo
still works fully and never displays numbers that contradict the chart.

Research prototype — **not for clinical use.**
