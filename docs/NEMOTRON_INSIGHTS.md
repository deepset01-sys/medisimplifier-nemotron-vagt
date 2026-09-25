# What We Learned Working With Nemotron
### Field notes from MediSimplifier v2 — Nebius × NVIDIA Global AI Hackathon

**Audience:** NVIDIA model & inference engineers
**Context:** We used Nemotron in **four distinct roles** inside a clinical-summary
safety system (Nano as an ensemble safety-judge, Nano as a scoped single-gate,
Super as a training-data teacher, and both under a production verdict-extraction
path), and measured each with one criterion-anchored validity framework (VAGT).
Every number below is reproducible from committed scripts and a locked verdict set;
we pre-registered the one experiment that could have gone either way and report it
whether it helped us or not.

These are engineer-to-engineer notes: two are immediately actionable SDK/inference
items, two are capability/task-fit characterizations, one is a genuinely favorable
result that surprised us. We lead with the surprise.

---

## TL;DR

| # | Role | Outcome | One-line takeaway for Nemotron users |
|---|------|---------|--------------------------------------|
| 1 | Nano — third judge in a validity panel | **Real, detection-specific lift** (+0.0765 Φ_V) | A 30B Nano matches a 550B Nemotron; two other families added more (partly by construction — see Finding 1) — choose judges against verified labels, not agreement |
| 2 | Super — reasoning budget | `content=None` at 1024 tokens; needs ~16k | Budget the *reasoning* tokens, not just the answer — a silent `content=None` if under-budgeted |
| 3 | Both — verdict extraction | Regex-scraped from 8k-token reasoning | Expose/use logprobs for classification verdicts — unlocks thresholds and cuts latency |
| 4 | Nano — scoped faithfulness gate | Pre-registered **null** | Name-match verification penalizes correct paraphrase; wrong tool for a simplification task |
| 5 | Super — teacher for fine-tuning | Below Claude Opus 4.5 on generation | Strong as a *judge*, weaker as a *generator* for lay-language rewriting |

---

## Finding 1 — Nano earns its seat; scale doesn't help within the family, other families help more

**Role.** Nemotron Nano (30B-class, A3B MoE) added as a third judge alongside
Llama-3.3-70B and Qwen3-32B in an ensemble that decides whether a simplified
clinical summary dropped a diagnosis.

**Outcome.** On a hand-verified benchmark — 120 patient-invisible primary-diagnosis
drops plus 120 paired faithful controls — adding Nano raised diagnosis-detection
validity **Φ_V 0.4764 → 0.5529 (ΔΦ_V +0.0765, 95% CI [+0.0516, +0.0992])** under the
deployed gate prompt (0.4745 → 0.5337, +0.0591 [+0.0387, +0.0802] under the
calibration prompt). It holds out-of-sample — split by patient, **+0.0735 [0.036,
0.104]** and **+0.0789 [0.047, 0.109]** on the two halves — and it is detection, not
flag-rate: the lift sits far outside a τ-blind permutation null (p = 0.001). Nano
**matches Nemotron Ultra-550B** (+0.0781 [0.0552, 0.1003]; overlapping CIs) at ~18×
fewer total parameters. It is **not** the strongest addition: **gpt-oss-120b**
(+0.1220 [0.1000, 0.1416]) and **DeepSeek-V4-Flash** (+0.1238 [0.1024, 0.1440]) sit
entirely above Nano's CI. Of six candidates, five pass the permutation null (gemma-3-27b
does not, p = 0.449).

**Mechanism.** The two incumbents share a blind spot: both pass **41 of the 120**
genuine drops as SAFE. Nano flags **33 of those 41** — its signal lands exactly where
the incumbents are jointly wrong (gpt-oss flags 38). Adding Nano also lowers
inter-rater agreement slightly (Fleiss κ 0.2144 → 0.1788; Krippendorff α 0.216 →
0.1799) while raising validity, but on this benchmark the agreement drop is **not
significant** (Δκ −0.0356 [−0.1314, +0.0557]) — agreement simply carries no signal
about which judge helps. The cost is over-flagging: in 47 of 120 patients Nano flags
both the version missing the diagnosis and the faithful one; in 63 it flags only the
lossy version.

**Implication for Nemotron users.** Within the Nemotron family, **scale did not buy
detection** — Nano matched Ultra-550B — so try the smallest Nemotron first in a
many-call safety loop. But **measure candidates against a verified criterion before
choosing**: on our benchmark two other families added ~1.6× as much validity, and our
own panel-selection endpoint (`/v1/audit_panel`) recommends gpt-oss-120b for this
panel (caveat: the benchmark's τ=1 items were screened by gpt-oss-120b as oracle and
edited by DeepSeek-V4-Pro, so those two families' lead is partly by construction;
Nano's measurement is free of this — the panel judges were kept out of benchmark
construction, see README A8). Agreement statistics would not have shown any of this.

*An earlier version of this finding reported +0.071 on an automated benchmark whose
diagnosis labels were later found ~85% wrong; see the project README (A6, A8).*

---

## Finding 2 — Nemotron Super's reasoning budget is a silent failure mode

**Role.** Nemotron Super used to regenerate reference simplifications (teacher /
data-generation path), called via the Nebius OpenAI-compatible API.

**Outcome.** At `max_tokens=1024` the API returned a well-formed response whose
`content` was **`None`** — no error, no truncation flag, just empty content. Raising
to **~16,000** was required before usable text appeared.

**Mechanism.** The reasoning trace consumes the token budget *before* any answer
tokens are emitted. A budget sized for the visible answer is entirely absorbed by
thinking, so the model "succeeds" with empty content. This is characteristic of
reasoning models generally — but here it surfaced as a **silent** `None` rather than
a visible truncation, which is the dangerous part: a naïve pipeline will treat it as
a valid empty result.

**Implication for Nemotron users.**
- Budget **reasoning + answer** tokens together; start high (16k) for Super and tune down.
- Treat `content is None` as a **retryable budget error**, not an empty answer — silent `None` is the single most likely way to corrupt a batch job.
- Docs/SDK request: surface a distinct signal when generation ends inside the reasoning phase, before any answer tokens are emitted.

---

## Finding 3 — Classification verdicts are being scraped from prose; logprobs would fix three problems at once

**Role.** Nano and the panel producing a binary SAFE / UNSAFE gate verdict in
production.

**Outcome.** Verdicts are obtained by **regex over an ~8,000-token reasoning
generation** (`\b(SAFE|UNSAFE)\b`). Consequences we measured: ~26.5 s gate latency,
a ~35% false-positive rate **with no tunable knob**, and no confidence score.

**Mechanism.** All three symptoms share one root cause: the decision is read from
*generated text* instead of from the model's *distribution*. Because there is no
score, there is no threshold to calibrate; because the full reasoning must complete
before the keyword appears, latency is bounded below by the whole generation; because
extraction is textual, it is brittle to phrasing. Despite `enable_thinking=False` in
the call (`safety_gate.py:44`), the gate still emits ~8k-token reasoning — confirming
the flag did not suppress the reasoning trace in our runs.

**Implication for Nemotron users.** For any classification/verdict task, **read
logprobs or use constrained decoding** rather than scraping reasoning:
- A continuous `P(UNSAFE)` turns a fixed operating point into a **calibratable threshold** (the FP knob you otherwise don't have).
- Constrained/first-token decoding collapses latency from "full reasoning" to "one token."
- SDK request: first-class logprob access and a constrained-output mode on Nemotron endpoints would make these models drop-in for scored classification, not just chat.

---

## Finding 4 — Name-match faithfulness verification is the wrong tool for a paraphrase task (pre-registered null)

**Role.** Nano as a **single scoped gate** — a tightly-scoped "did the summary drop a
diagnosis?" verifier, pre-registered against explicit success thresholds.

**Outcome.** A clean **null**. The scoped rubric failed all three pre-registered
thresholds: ΔΦ (Youden) **−0.083 [−0.240, +0.069]** vs a +0.10 target; false-positive
rate did **not** fall (ΔF +0.015). n=350 diagnosis stratum, 347 complete-case, parse
failures 0.86%. The harness reproduces the original pipeline's automated-pass 3-rater
Φ_V on the same items (0.472 ≈ 0.476), so the null is real, not a plumbing artifact.

**Mechanism.** 100% of the clean-item false positives were *in-scope*, and the cause
is **paraphrase-mismatch**. Smoking gun (item idx=12): source *"Acute T-cell
lymphoblastic leukemia"* → faithful summary *"a fast-growing blood cancer"* → Nano
flags the technical name as a **dropped diagnosis**. The verifier is doing string/
name matching, but the task is deliberate lay-language *paraphrase*. Tightening the
prompt cannot fix this, because the flags are correct *as name-matching* and wrong
*as faithfulness*.

**Implication for Nemotron users.** For faithfulness checking over paraphrased or
simplified text, **a name-match verifier will systematically penalize correct
simplification**. The lever is **semantic grounding** (entailment / embedding-level
presence), not rubric wording or model scale. Any small verifier — Nemotron or
otherwise — will hit this floor on a paraphrase task; know it before you deploy one
as a gate.

---

## Finding 5 — Super is a strong judge but a weaker generator for lay-language rewriting

**Role.** Nemotron Super as a **teacher** generating reference simplifications for
fine-tuning, compared against Claude Opus 4.5 references.

**Outcome.** A measurable generation-quality gap: Super's lay-language rewrites were
weaker than the Claude-authored references we compared against, even though Super is
entirely serviceable in the **judge/verifier** roles above.

**Mechanism.** The two roles stress different capabilities. Judging a simplification
is a discrimination task (is fact X preserved?); *producing* a good simplification is
an open-ended generation task requiring register control and audience modeling.
Super's strengths line up with the former.

**Implication for Nemotron users.** Role-match matters: **use Super where the task is
evaluation/verification, and benchmark carefully before using it as a generator** for
audience-specific rewriting. "Good judge" does not imply "good author."

---

## Why these numbers are trustworthy

- **One measurement framework (VAGT):** criterion-anchored G-theory with a *known*
  ground truth τ, so every claim is validity against reference, not agreement.
- **Pre-registration:** Finding 4's thresholds were fixed before we looked at the
  eval split; we report the null it produced.
- **Same-harness baselines:** we re-ran comparisons in one harness rather than diffing
  stored numbers, and the harness reproduces the original pipeline's automated-pass Φ_V (0.472 ≈ 0.476).
- **Hand-verified benchmark:** Finding 1 is measured on 120 hand-verified drops + 120 paired
  controls, pre-registered before any judge ran (`docs/judgebench_v2_protocol.md`).
- **Honest mix:** one favorable result (Finding 1), two actionable engineering gotchas
  (2, 3), two capability characterizations (4, 5). The negatives are credible *because*
  the method also produced a positive.

## Reproduce
- Benchmark (hand-verified v2): `results/judgebench_v2_tau1_final.json`, `results/judgebench_v2_clean_controls.json`
- Ensemble validity + CIs: `scripts/run_phi_v_recompute.py`, `scripts/run_pool_judgebench_v2.py`,
  `results/judgebench_v2_phi_v_recompute.json`, `results/judgebench_v2_pool_table.json`
- Detection vs flag-rate (permutation null): `scripts/run_null_control_v2.py`, `results/judgebench_v2_null_control.json`
- Out-of-sample validation: `scripts/run_split_half_v2.py`, `results/judgebench_v2_split_half.json`
- Agreement: `results/judgebench_v2_agreement_recompute.json`
- Pre-registered scoped-gate null: `scripts/run_vagt_loop_experiment.py`,
  `results/vagt_loop_{A0,A1,summary}.json`
- Core metric: `src/audit_panel/vagt_core.py`

*MediSimplifier v2 — deepset01-sys/medisimplifier-nemotron-vagt*
