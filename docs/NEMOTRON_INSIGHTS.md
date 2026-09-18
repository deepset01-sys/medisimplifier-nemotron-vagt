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
| 1 | Nano — diversity judge in a 3-rater panel | **Net-positive, only rater to help** (+0.071 validity) | A 30B-class Nano *raises* panel validity where a 550B alone does not — diversity beats scale |
| 2 | Super — reasoning budget | `content=None` at 1024 tokens; needs ~16k | Budget the *reasoning* tokens, not just the answer — a silent `content=None` if under-budgeted |
| 3 | Both — verdict extraction | Regex-scraped from 8k-token reasoning | Expose/use logprobs for classification verdicts — unlocks thresholds and cuts latency |
| 4 | Nano — scoped faithfulness gate | Pre-registered **null** | Name-match verification penalizes correct paraphrase; wrong tool for a simplification task |
| 5 | Super — teacher for fine-tuning | Below Claude Opus 4.5 on generation | Strong as a *judge*, weaker as a *generator* for lay-language rewriting |

---

## Finding 1 — Nano earns its seat: diversity beats scale in a validity panel

**Role.** Nemotron Nano (30B-class, A3B MoE) added as a third judge alongside
Llama-3.3-70B and Qwen3-32B in an ensemble that decides whether a simplified
clinical summary dropped a diagnosis.

**Outcome.** Adding Nano raised diagnosis-detection validity **Φ_V 0.404 → 0.476
(ΔΦ_V +0.0706, 95% CI [0.0552, 0.0866])** on calibration, and **+0.052 [0.030, 0.075]
out-of-sample** under the deployed prompt. Nano was the **only** rater, of every
candidate we tested, that was net-positive across all corruption strata. On the
diagnosis stratum it was **statistically indistinguishable from Ultra-550B and
gpt-oss-120B** (overlapping CIs) — at ~18× fewer total parameters and a fraction
of the cost.

**Mechanism.** Counter-intuitively, adding Nano *lowered* inter-rater agreement
(Fleiss κ / Krippendorff α went negative) while *raising* validity against known
ground truth. Nano's errors are **decorrelated** from the two incumbents rather
than redundant with them, so it contributes independent signal exactly where the
larger, more-agreeing raters share a blind spot. Agreement is not validity; a
diverse small judge can be worth more than a bigger, more-consensual one.

**Implication for Nemotron users.** For ensemble/verifier use cases, **pick Nano
for decorrelation, not for raw capability**. Selecting judges by inter-rater
agreement will actively reject the model that helps most. Nano's MoE efficiency
(A3B active) makes it the right *dose* of diversity — the smallest per-item cost
penalty we measured — which is precisely what you want in a many-call safety loop.

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
failures 0.86%. The harness reproduces the published headline (3-rater Φ_V 0.472 ≈
0.476), so the null is real, not a plumbing artifact.

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
  stored numbers, and the harness reproduces our published headline (Φ_V 0.472 ≈ 0.476).
- **Honest mix:** one favorable result (Finding 1), two actionable engineering gotchas
  (2, 3), two capability characterizations (4, 5). The negatives are credible *because*
  the method also produced a positive.

## Reproduce
- Ensemble validity + CIs: `scripts/compute_pool_cis.py`, `results/pool_candidate_cis.json`
- Out-of-sample validation: `scripts/compute_split_half.py`
- Pre-registered scoped-gate null: `scripts/run_vagt_loop_experiment.py`,
  `results/vagt_loop_{A0,A1,summary}.json`
- Core metric: `src/audit_panel/vagt_core.py`

*MediSimplifier v2 — deepset01-sys/medisimplifier-nemotron-vagt*
