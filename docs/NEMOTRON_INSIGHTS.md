# What We Learned Working With Nemotron
### Field notes from MediSimplifier v2 — Nebius × NVIDIA Global AI Hackathon

**Audience:** NVIDIA model & inference engineers
**Context:** We used Nemotron in **four distinct roles** inside a clinical-summary
safety system (Nano as an ensemble safety-judge, Nano as a scoped single-gate,
Super as a training-data teacher, and both under a production verdict-extraction
path), and measured each with one criterion-anchored validity framework (VAGT).
Every number below is reproducible from committed scripts and a locked verdict set;
we pre-registered the experiments that could have gone either way and report them
whether they helped us or not.

These are engineer-to-engineer notes: two are immediately actionable SDK/inference
items, two are capability/task-fit characterizations, one is a genuinely favorable
result that surprised us. We lead with the surprise.

---

## TL;DR

| # | Role | Outcome | One-line takeaway for Nemotron users |
|---|------|---------|--------------------------------------|
| 1 | Nano — third judge in a validity panel | **Real, detection-specific lift** (ΔΦ_V +0.0765 at a 50% drop share) | A 30B Nano matches a 550B Nemotron; two other families added more (partly by construction — see Finding 1) — choose judges against verified labels, not agreement |
| 2 | Super — reasoning budget | `content=None` at 1024 tokens; needs ~16k | Budget the *reasoning* tokens, not just the answer — a silent `content=None` if under-budgeted |
| 3 | Both — verdict extraction | Regex-scraped from 8k-token reasoning | Expose/use logprobs for classification verdicts — unlocks thresholds and cuts latency |
| 4 | Nano — scoped faithfulness gate | Pre-registered: **no recall cost, no demonstrated gain** | Narrowing the prompt doesn't fix name-match false positives on paraphrased text; the lever is semantic grounding |
| 5 | Super — teacher for fine-tuning | Below Claude Opus 4.5 on generation | Strong as a *judge*, weaker as a *generator* for lay-language rewriting |

---

## Finding 1 — Nano earns its seat on a balanced benchmark; scale doesn't help within the family, other families help more

**Role.** Nemotron Nano (30B-class, A3B MoE) added as a third judge alongside
Llama-3.3-70B and Qwen3-32B in an ensemble that decides whether a simplified
clinical summary dropped a diagnosis.

**Outcome.** On a hand-verified benchmark — 120 patient-invisible primary-diagnosis
drops plus 120 paired faithful controls (50% drops) — adding Nano raised diagnosis-detection
validity **Φ_V 0.4764 → 0.5529 (ΔΦ_V +0.0765, 95% CI [+0.0516, +0.0992])** under the
deployed gate prompt (0.4745 → 0.5337, +0.0591 [+0.0387, +0.0802] under the
calibration prompt). It replicates across patients — split by patient, **+0.0735 [0.036,
0.104]** and **+0.0789 [0.047, 0.109]** on the two halves — and it is detection, not
flag-rate: the lift sits far outside a τ-blind permutation null (p = 0.001). Nano
**matches Nemotron Ultra-550B** (+0.0781 [0.0552, 0.1003]; overlapping CIs) at ~18×
fewer total parameters. It is **not** the strongest addition: **gpt-oss-120b**
(+0.1220 [0.1000, 0.1416]) and **DeepSeek-V4-Flash** (+0.1238 [0.1024, 0.1440]) add
more, though on the same rows their CIs only just clear Nano's or overlap it (gpt-oss +0.1000
vs Nano's upper +0.0992 on all 240 rows; DeepSeek +0.1024 vs +0.1056 on its 233 completed rows). Of six candidates, five pass the permutation null (gemma-3-27b
does not, p = 0.449).

**Mechanism.** Under the deployed gate prompt the two incumbents each catch 56 of the 120
genuine drops, and both pass the same **41 of the 120** as SAFE (34 would be expected if
their misses were independent; under the calibration prompt they share 3 of 120). Their
recall (46.7% each, Wilson 95% CI 38.0–55.6%) is outside the v2 protocol's pre-registered
*incumbent blind spot confirmed* band (both below 30%; `docs/judgebench_v2_protocol.md`
§8). Nano flags **33 of those 41** — its signal lands exactly where
the incumbents are jointly wrong (gpt-oss flags 38). Adding Nano leaves
inter-rater agreement with no detectable change (Fleiss κ 0.2144 → 0.1788,
Δκ −0.0356 [−0.1310, +0.0565]; Krippendorff α 0.216 → 0.1799) while raising
validity — agreement simply carries no signal
about which judge helps. The cost is over-flagging: in 47 of 120 patients Nano flags
both the version missing the diagnosis and the faithful one; in 63 it flags only the
lossy version.

**Implication for Nemotron users.** Within the Nemotron family, **scale did not buy
detection** — Nano matched Ultra-550B — so try the smallest Nemotron first in a
many-call safety loop, after checking your drop rate: every candidate adds less at 20%
drops than at 50%, and under the deployed prompt Nano's gain is no longer detectable at
20% (ΔΦ_V +0.0066 [−0.0264, +0.0384]; point estimate below zero at 17% and below). The bias
its false alarms add on clean text (it flags 53 of 120 faithful controls) weighs more as
drops get rarer and, below about 16%, outweighs what its catches remove (with the rater
spread it adds, its point estimate turns negative below about 18%). gpt-oss-120b's point
estimate stays positive at every share tested, though its CI includes zero below about 8%
drops (post hoc reweighting, `results/judgebench_v2_prevalence_sensitivity.json`).
But **measure candidates against a verified criterion before choosing**: on our benchmark
(50% drops) two other families added ~1.6× as much validity, and our
own panel-selection endpoint (`/v1/audit_panel`) recommends gpt-oss-120b for this
panel (statistically tied with DeepSeek-V4-Flash; the fewest-errors tie-break that picks
gpt-oss was added after the result was known. Caveat: the benchmark's τ=1 items were screened by gpt-oss-120b as oracle and
edited by DeepSeek-V4-Pro, so those two families' lead is partly by construction;
Nano's measurement is free of this — the panel judges were kept out of benchmark
construction, see README A8). Agreement statistics would not have shown any of this.

*An earlier version of this finding reported +0.071 (at a 41% share of corrupted items, not the 50%
above) on an automated benchmark whose diagnosis labels were later found ~85% wrong; see the project
README (A6, A8).*

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

## Finding 4 — Name-match faithfulness verification is the wrong tool for a paraphrase task (pre-registered: no recall cost, no demonstrated gain)

**Role.** Nano as a **single scoped gate**. We compared a prompt that asks only "did the summary drop a diagnosis?" (A1) with the deployed gate prompt (A0), with Llama and Qwen held fixed.

**Outcome.** We ran both prompts on the 120 hand-verified diagnosis drops and their 120 paired controls, four calls per item per prompt (1,920 calls). The design, thresholds and analysis were committed before the first call.

| Pre-registered test | A1 − A0 [95% CI] | Result |
|--|--|--|
| Guardrail: recall must not fall | ΔR **+0.019** [−0.031, +0.069] | pass |
| Primary: Youden J up by 0.10 or more | ΔJ **+0.046** [−0.060, +0.154] | fail |
| Driver: false positives down by 0.15 or more | ΔF **−0.027** [−0.129, +0.077] | fail |

Scoping the prompt costs no recall: a loss of more than about 3 points is ruled out. But it doesn't deliver the pre-registered improvement, and the +0.046 is not a small win, for two reasons:

- **It is within measurement noise.** Nano's verdicts vary between calls even at temperature 0: the deployed prompt's four calls disagree on 37% of items. Comparing one pair of a prompt's calls with its other pair, the same prompt against itself, gives differences of up to +0.042 in either arm. That is almost the observed +0.046. The pre-registered noise check passed, since no self-comparison reached a threshold, but the effect can't be told apart from that noise.
- **It depends on token budgets above the deployed 8,000.** The scoped prompt's reasoning runs away more often. 33 of its 960 calls didn't finish within 8,000 tokens, against 6 for the deployed prompt, and 3 never finished even at 32,000. Counting only verdicts reached within 8,000 tokens, with unfinished calls scored against the scoped prompt, the edge disappears (ΔJ −0.006 [−0.115, +0.102]).

**Decision.** The deployed gate prompt stays unchanged. The guardrail passes, neither improvement threshold does, and the one edge that shows up needs budgets production doesn't give it.

**Mechanism.** False positives barely move. Both prompts flag 37–40% of the paired controls, which are the same summaries as the drops but with the diagnosis still present. The flags are paraphrase mismatches. In about half of the scoped prompt's 177 false flags (at least 87), the diagnosis it calls missing is the pair's own diagnosis, which the control states in lay words. The v1 example (item idx=12): source *"Acute T-cell lymphoblastic leukemia"* → faithful summary *"a fast-growing blood cancer"* → flagged as a **dropped diagnosis**. The verifier matches names, while the task is deliberate lay-language *paraphrase*. Narrowing the prompt to diagnoses did not change that.

**Earlier run.** A first run of this comparison (n=350) reported a "clean null" with a recall loss (ΔJ −0.083, ΔR −0.068). It was scored on automatically labelled drops, 128 of 150 of which still contained the diagnosis. On its 8–21 genuine drops it could not tell the prompts apart, and its recall "loss" came from items where no diagnosis had been dropped. It stays in the repo as disclosed history (`results/vagt_loop_summary.json`).

**Implication for Nemotron users.** For faithfulness checking over paraphrased or simplified text, **a name-match verifier will systematically penalize correct simplification**, and scoping its prompt doesn't change that. The lever is **semantic grounding** (entailment or embedding-level presence), not rubric wording or model scale. Also, a scoped JSON rubric makes Nano's reasoning overrun more often. Measure it at your production token budget, because an edge found at a larger budget may not survive it.

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
- **Pre-registration:** Finding 4's design, thresholds and analysis were fixed before any call, and we report the result whatever it was. The earlier v1 run was committed together with its results, so its pre-registration can't be checked.
- **Git-enforced pre-registration (v2 scoped-gate re-run):** the design, thresholds and analysis were committed (`d69f506`) before any call. The runner refuses the full run unless the pre-registration note and the runner are committed and unmodified, and it records their git blob ids and HEAD in the results. Anyone can check `git rev-parse d69f506:docs/vagt_loop_v2_preregistration.md` against `run_meta.prereg_blob`.
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
- Prevalence sensitivity (post hoc reweighting): `scripts/run_prevalence_sensitivity_v2.py`, `results/judgebench_v2_prevalence_sensitivity.json`
- Split-half replication (patient-disjoint): `scripts/run_split_half_v2.py`, `results/judgebench_v2_split_half.json`
- Agreement: `results/judgebench_v2_agreement_recompute.json`
- Scoped gate, v2 (pre-registered, git-enforced): `docs/vagt_loop_v2_preregistration.md`, `scripts/run_vagt_loop_v2.py`, `results/vagt_loop_v2_{summary,calls,pilot}.json`, `results/vagt_loop_v2_deviations.md`. `run_meta` in the summary holds HEAD `d69f506` and the blob ids of the note and the runner.
- Scoped gate, v1 (automated labels; disclosed history): `scripts/run_vagt_loop_experiment.py`, `results/vagt_loop_{A0,A1,summary}.json`
- Core metric: `src/audit_panel/vagt_core.py`

*MediSimplifier v2 — deepset01-sys/medisimplifier-nemotron-vagt*
