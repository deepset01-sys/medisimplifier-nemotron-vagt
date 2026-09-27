# Scoped-gate experiment on JudgeBench v2 — pre-registration

**Status:** frozen from the commit that adds it. `scripts/run_vagt_loop_v2.py` refuses the full
run unless this file and the runner are both committed and unmodified, and it records their git
blob ids and HEAD in the results. Written 2026-09-27, before any v2 call of this experiment.

The v1 result (`results/vagt_loop_summary.json`, commit dca6961) stays in the repo as disclosed
history. This is a new run on a different stratum, not a re-analysis of v1.

## 1. Why re-run

The v1 run scored A0 vs A1 on 150 automatically labelled diagnosis drops, about 85% of which
still contained the diagnosis. By hand label only 8–21 were genuine drops, so its intervals are
about ±0.35 and it cannot say whether A1 helps or hurts. Its reported recall loss came from items
where the diagnosis was still present. Two measurement problems also affected it:

- **Truncation.** One A1 call on a genuine drop ran out of tokens and was dropped; scoring it as
  a miss instead moves strict d_R from 0.000 to −0.111.
- **Run-to-run noise.** Re-running A0 reproduced the stored Nano verdicts on only 69% of items.

Sections 5 and 6 address these two.

## 2. Question

Holding Llama-3.3-70B and Qwen3-32B fixed, does changing Nemotron Nano's prompt from the deployed
gate prompt (A0) to the scoped diagnosis-drop rubric (A1) improve truth-alignment on genuine
primary-diagnosis drops? The question and the thresholds are the same as v1.

## 3. Stratum

- 240 items: the 120 hand-verified τ=1 drops in `results/judgebench_v2_tau1_final.json`, and the
  120 `primary_paired` τ=0 controls in `results/judgebench_v2_clean_controls.json`.
- Each control is the pre-edit summary of one drop, so the items form 120 patient pairs.
- Original note text comes from the same inputs as `run_pool_judgebench_v2.canonical_items`.
- The 172 supplementary controls are not analysed. Ten of them are used only for the cost pilot (§10).

## 4. Arms

- **Model:** `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (Nebius Token Factory), temperature 0.
- **A0:** `safety_gate.JUDGE_PROMPT` as one user message. The payload is identical to v1's
  `call_A0`, including `extra_body: {"enable_thinking": false}`. That flag is known not to stop
  the model's reasoning; it is kept for comparability.
- **A1:** `A1_SYSTEM` + `A1_USER`, imported unchanged from `scripts/run_vagt_loop_experiment.py`,
  with `response_format: json_object`. Same flag.
- **Parsing:** A0 takes the last SAFE/UNSAFE after any `</think>`; A1 reads the JSON `verdict`
  (FAIL/PASS). Both parsers are the v1 parsers.

## 5. Run-to-run noise: repeated measurement

- **K = 4 independent calls per item per arm** (1,920 analysis calls).
- All calls run in one session. Their order is shuffled across arms, items and repeats (seed 42),
  with 8 concurrent workers, so changing serving conditions affect both arms alike.
- **Per-item score:** p̂ = the fraction of that item's 4 calls that flag it (A0 UNSAFE, A1 FAIL).
  - R = mean p̂ over the 120 drops.
  - F = mean p̂ over the 120 controls.
  - J = R − F (Youden, as in v1).
- **Intervals:** paired cluster bootstrap over the 120 patient pairs. A drop and its control are
  resampled together, with all their calls. 1,000 resamples, seed 42, percentile 95%. Contrasts
  are A1 − A0.
- **Noise check (placebo):** within each arm, calls 1–2 are compared with calls 3–4 as if they
  were two arms, using the same analysis. If either placebo would pass the **primary** or the
  **driver** threshold, noise alone can produce the kind of improvement being tested. The
  experiment is then reported **INCONCLUSIVE (noise)** and no pass/fail claim is made. Placebo
  intervals are reported in full either way.
- **Reliability, reported per arm:** mean pairwise agreement between an item's calls, and the
  share of items whose calls disagree.

## 6. Truncation and other non-answers

- **Budget ladder per call:**

  | Step | max_tokens | Timeout |
  |--|--|--|
  | 1 | 8,000 | 120 s |
  | 2 | 16,000 | 240 s |
  | 3 | 32,000 | 480 s |

  A reply that ends at the token limit (`finish_reason=length`) or has empty content is never
  scored; the call moves to the next step. This applies even if the cut-off text happens to
  contain SAFE or UNSAFE; v1 accepted such A0 replies.
- **Other failures:**
  - Transient failures (HTTP 429/5xx, timeouts, connection errors): up to 3 tries per step, then
    the next step.
  - Unparseable replies that did finish (`finish_reason=stop`): one retry at the same step, then
    the next step.
  - Any other HTTP 4xx: no retry.
- **Non-answers (NV):** a call with no verdict after the last step. The primary rule scores NV
  **against the hypothesis**:
  - an A1 NV counts as a miss on a drop and as a false flag on a control;
  - an A0 NV counts as a catch on a drop and as a pass on a control.

  So no threshold can pass because A1 failed to answer or A0 failed to answer. The same analysis
  is also reported with NV scored the other way, and complete-case. A threshold whose result
  differs between the two scorings is flagged **NV-SENSITIVE** in the summary.
- **Records:** every attempt is stored (step, finish_reason, token usage, elapsed time, outcome).
  For each arm and each τ, the summary reports how many verdicts needed each step and how many
  NV remain.
- **Production view (secondary):** the same contrast, counting only verdicts reached at 8,000
  tokens within 60 s. Those are the deployed gate's settings.

## 7. Pre-registered thresholds

These are unchanged from v1. They use the Youden R − F metric, paired A1 − A0, and the primary NV
rule.

| Test | Rule |
|--|--|
| primary | d_J ≥ +0.10 AND CI lower bound > 0 |
| guardrail | d_R ≥ −0.05 AND CI lower bound > −0.10 |
| driver | d_F ≤ −0.15 |

## 8. Secondary and descriptive (no thresholds)

- **Reproducibility:** A0's majority verdict (UNSAFE if at least 2 of 4 calls flag) against the
  stored v2 panel Nemotron column (`results/judgebench_v2_panel_gate.json`, same prompt).
- **ΔΦ_V:** the change when the A0-majority or the A1-majority Nano column is added to Llama +
  Qwen (vagt_core, seed 42, 1,000 resamples).
- **R by stratum:** R per arm for `expert_recoverable` = 0 and = 1.
- **Cost:** total token usage, and cost at $0.06 per 1M input and $0.24 per 1M output tokens.
  These rates are implied by the README cost table: its Nano calibration row totals 3.22M input
  and 8.23M output tokens at $2.17.

## 9. Power

With 120 drops, the d_R interval half-width is about 1.96·√(p_d/120), where p_d is the share of
drops on which the two arms disagree:

| p_d | Half-width |
|--|--|
| 10% | 0.057 |
| 25% | 0.089 |
| 33% | 0.103 |
| 50% | 0.127 |

Averaging 4 calls per item lowers the per-item noise further. The guardrail's interval condition
can be met if the arms disagree on fewer than about a third of drops. In v1 the half-width was
about 0.35.

## 10. Procedure and commitments

1. Commit this note together with `scripts/run_vagt_loop_v2.py`.
2. **Offline self-test** (`--selftest`, no API calls). It must reproduce the committed v2 Nano
   ΔΦ_V of +0.0765 [+0.0516, +0.0992] through the secondary pipeline, and zero contrast when both
   arms are fed identical verdicts.
3. **Cost pilot:** 10 supplementary controls, which are not analysed, × 2 arms × 1 call = 20
   calls. The pilot outcomes are not used in any analysis. Stop and report if:
   - the projected full-run cost exceeds $5; or
   - more than 2 of the 20 pilot calls end with no verdict.
4. **Full run:** 1,920 calls. No looks at outcomes before it completes. No re-runs of individual
   items outside §6. No change to the thresholds, K, the NV rule or the analysis.
5. **Report** the result whatever it is (pass, fail or inconclusive) and update the README and
   NEMOTRON_INSIGHTS text to match. Any deviation from this note is logged in the summary file.

## 11. Known limitations

- The `enable_thinking=False` flag does not stop Nano's reasoning. It is sent as in production.
- Calls at temperature 0 still vary between runs. The repeats measure that variation; they do not
  remove it.
- τ labels were author-verified item by item, with Claude Opus 4.8 as a drafting aid, and were
  not reviewed by clinicians.
- Construction circularity does not apply: Nano was neither the editor nor the oracle of this
  benchmark.
- F is measured on the paired pre-edit summaries, not on v1's 200 clean controls. Each control is
  the same text as its drop, with the diagnosis still present.
