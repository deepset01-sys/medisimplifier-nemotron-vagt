# JudgeBench v2 protocol — erratum

`docs/judgebench_v2_protocol.md` is a frozen pre-registration and stays as committed, apart from one
dated clarification of §5 (2026-09-28). This erratum corrects two statements in it about the automated
pass's +0.071, and its last section records where the work deviated from the protocol. It changes
nothing in the protocol's design, bands or procedure, and no v2 result.

Written 2026-09-29, after every v2 analysis had run. Figures are from
`results/tau_recompute_v1_matched.json`, written by `scripts/run_tau_recompute_v1.py`, unless another
file is named. That script is post hoc and reproduces every cell of
`results/tau_recompute_summary.json` (asserted). Evidence marked "Project v1 repo" is from Project v1's
repository ([github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius/tree/dd6681bed29199f7ed2f1eb10af3ad2c99b734d3)
at commit `dd6681b`), which is not part of this repo. It is cited only for how Project v1's stored Llama and Qwen
verdicts were produced.

## 1. §0 (line 9): "The headline +0.071 reversed to −0.144 on corrected labels"

The −0.144 [−0.195, −0.098] is the primary (B/strict) cell of `results/tau_recompute_summary.json`.
The change of sign from +0.071 to −0.144 comes from the drop share, not the labels, and both figures
pair judges that ran under different prompts.

### The two cells have different drop shares

- The +0.071 cell has 138 automated drops and 195 clean controls: 41% drops.
- The −0.144 cell has 9 hand-confirmed drops, 129 relabelled items and 195 clean controls: 2.7% drops.
- Φ_V depends on the drop share (README A8 threat 11). A judge's catches count in proportion to the
  drop share, its false alarms in proportion to the rest.
- In the −0.144 cell, adding Nemotron lowers the drops' mean b² and raises the controls'. Below
  12.8% drops the controls' rise outweighs the drops' fall in the weighted mean b²
  (`pairings.published_mixed_prompt.cells["B/strict"].mechanism.mean_b2_breakeven`). σ²_R also enters
  Φ_V, so the ΔΦ_V point estimate changes sign at a different share: it is negative up to 16% drops
  and positive from 17% (`delta_sign_runs_on_grid`). At the cell's own 2.7%, the controls' weighted
  change in mean b² is +0.0485 and the drops' is −0.0092 (`change_in_mean_b2_at_own_share`).
- In this file the incumbents flag 3 and 1 of the 195 complete-case controls and Nemotron flags 67
  (`flag_rates`), so adding Nemotron raises the control-side bias from near zero.

Compared at one share, the two cells have the same sign:

| Cell | At 2.7% drops | At 41% drops |
|--|--|--|
| Automated labels (the +0.071 cell) | −0.1931 [−0.2541, −0.1343] | +0.0706 [+0.0527, +0.0868] |
| Hand labels, B/strict (the −0.144 cell) | −0.1438 [−0.1945, −0.0979] | +0.0718 [+0.0046, +0.1154] |

The +0.0706 CI is the one in `results/tau_recompute_summary.json`. The README quotes
[+0.055, +0.087] from `vagt_bootstrap_cis.json`, whose paired bootstrap draws all four strata in turn
from one random stream (`vagt_nemotron_analysis.py:222, 274`).

The other three hand-label cells behave the same way (`pairings.published_mixed_prompt.overview`).
At their own 4.4–9.3% shares their point estimates are −0.1288 to −0.0286, and at each of those shares
the automated-label cell is negative too (−0.1320, −0.0403, −0.0924). Reweighted to 41%, every
hand-label cell is positive with a CI above zero, from +0.0718 to +0.0920.

In this file, shuffling Nemotron's column across a cell's rows keeps its flag rate and removes its link
to the labels. On the −0.144 cell's rows the shuffled column gives −0.1465, 95% range
[−0.1559, −0.1360], and the real −0.1438 lies inside that range (upper-tail p = 0.35). In the other
three cells the real column lies above its null (upper-tail p = 0.011, 0.001 and 0.021;
`permutation_null_own_share`).

v2 shows the same dependence on share under the deployed prompt: Nano's +0.0765 at 50% drops becomes
−0.0382 [−0.0708, −0.0072] reweighted to 5%. Under the calibration prompt, where Llama flags 98 of the
120 controls, it stays above zero: +0.0165 [+0.0078, +0.0281] at 5%
(`results/judgebench_v2_prevalence_sensitivity.json`; README A8 threat 11).

### The judges' verdicts came from different prompts

In this repo:
- `nemotron_judge_test.py:13` gives the source of the Llama and Qwen columns of
  `nemotron_calibration_full.json`: Project v1's `results/nebius_evidence/calibration_verdicts.json`.
  Only the Nemotron column was run by that script. It used the 4-step CoT prompt with a system
  message, `max_tokens` 8000 and JSON output (`nemotron_judge_test.py:78-124`).
- Llama's column repeats one verdict per item index. On all 160 indices that appear on more than one
  row, its verdict is the same on every row. When Llama is re-run under the deployed prompt
  (`results/gate_calibration_full.json`), this holds for 68 of the 160.
- On all 115 corrupted rows that share an index with a clean control, Llama's stored verdict equals
  its verdict on that control; re-run, 56 of 115. Of these rows, 37 are diagnosis rows (31 of 37
  re-run).
- Qwen's column does not show this pattern: 50 of 160 and 49 of 115 (`idx_repeat_check`).

In Project v1's repo at `dd6681b`:
- `results/nebius_evidence/calibration_verdicts.json` is written by `perturbation_calibration.py`, with a one-word
  prompt, one user message and `max_tokens` 2000 (`:193-227`).
- The Llama and Qwen columns of `nemotron_calibration_full.json` equal that file's on all 708 rows. This was checked
  against Project v1's repo and cannot be reproduced from this repo alone.

So the +0.071 and the −0.144 both pair a Nemotron column run under one prompt with Llama and Qwen
columns run under another. On the 37 diagnosis rows that share an index with a clean control, Llama's
verdict also equals the one it has on that control.

### Results with all three judges under one prompt

`results/gate_calibration_full.json` has all three judges under the deployed gate prompt, on the same
708 items, with no ERROR rows. There the automated labels give +0.0438 at their own
42.9% share, as in `results/consensus_accuracy.json`, and +0.0426 [+0.0264, +0.0593] at 41%. The four
hand-label cells give:

| Cell | Drops / items (share) | ΔΦ_V at own share | Nemotron column shuffled, same flag rate: 95% range (real value) | Reweighted to 41% |
|--|--|--|--|--|
| A/strict | 9/209 (4.3%) | −0.0697 [−0.1115, −0.0270] | [−0.0854, −0.0441] (inside) | +0.0428 [−0.0274, +0.1052] |
| A/generous | 22/222 (9.9%) | −0.0287 [−0.0728, +0.0114] | [−0.0690, −0.0223] (inside) | +0.0502 [+0.0041, +0.0944] |
| B/strict | 9/350 (2.6%) | −0.0510 [−0.0771, −0.0278] | [−0.0491, −0.0330] (below) | +0.0323 [−0.0384, +0.0848] |
| B/generous | 22/350 (6.3%) | −0.0492 [−0.0754, −0.0245] | [−0.0562, −0.0281] (inside) | +0.0402 [−0.0061, +0.0772] |

- At each cell's own share, the automated-label cell reweighted to that share gives −0.0616, −0.0278,
  −0.0671 and −0.0493, the same sign as the hand-label cell.
- At those shares, Nemotron's real column does no better than the same flags shuffled across the
  cell's rows: each real value is inside or below the shuffled null's 95% range.
- Reweighted to 41%, the CIs of A/strict, B/strict and B/generous include zero: no lift is detectable
  there. A/generous's CI, [+0.0041, +0.0944], lies above zero.
- These CIs keep each resampled row's weight, the convention of
  `scripts/run_prevalence_sensitivity_v2.py` and README A8 threat 11. If the weights are recomputed
  in each replicate (`ci95_fixed_p`), B/generous's CI becomes [+0.0009, +0.0774].

### What stands

- 128 of the 150 automated diagnosis positives still contained the diagnosis. Only 9 were genuine
  drops, and 13 were borderline (`results/tau_hand_labels_150.json`).
- The +0.071 was measured against those labels, with judges under different prompts. It does not
  measure the detection of silent drops.
- Nemotron flags more of the relabelled items (diagnosis still present or borderline; each still had a
  sentence removed) than of the pristine controls. In this file it
  flags 84 of 129 against 67 of 195 (`results/tau_recompute_summary.json` `split_f_diagnostic`). Under
  the deployed prompt it flags 79 of 141 against 61 of 200 (`flag_rates`).

These points are why this protocol exists, and they are unchanged.

### What does not stand

- That the +0.071 "reversed" to −0.144, or that the re-score "REFUTED" it.
- That the +0.071 was a "label-contamination artifact". At one share the hand labels give the same
  sign, and in this file nearly the same value: +0.0718 against +0.0706 at 41%.
- That the corrected ΔΦ_V is "never positive" as a property of the labels (it is negative only at the
  cells' own shares), or that its negative sign is robust across cells.

At the cells' own 3–10% shares, every hand-label cell's point estimate is negative in both the
published and the deployed-prompt pairings, and so is the automated-label cell at those shares.
A/generous's CI includes zero in both. At 41% and at 50%, every cell's point estimate is positive in
both pairings. With 9 genuine drops (22 counting borderline), the re-score cannot show whether
Nemotron adds anything.

**Corrected sentence for §0:** "The headline +0.071 was measured against labels that were 85% wrong,
with Llama's and Qwen's stored verdicts from a different prompt than Nemotron's. Re-scored with the
hand labels, the 9 genuine drops are too few to show the sign of Nemotron's effect."

## 2. §7 (lines 124–126): "the calibration/CoT prompt (to compare apples-to-apples with the +0.071)"

The +0.071 did not come from a single prompt (item 1). The v2 calibration-prompt run has all three
judges under that prompt (`results/judgebench_v2_panel_calib.json`), so it is prompt-matched within
v2. It is still not an apples-to-apples comparison with the +0.071, which also differs in its judges'
prompts, its labels and its drop share (41%, against v2's 50%). The run was carried out as planned.
Only its stated purpose is corrected here.

## Deviations from the protocol

The protocol stays frozen apart from one dated clarification of §5's wording (2026-09-28), which states the single-batch
rule as it was applied. This section records where the work differed from it, so the record matches what happened. It
changes no data and no result.

1. **Specificity controls (§8, :154–155).** The premise test names "the 200 clean controls". The v2 panel run judged the
   120 paired controls (`results/judgebench_v2_panel_gate.json`, `results/judgebench_v2_panel_calib.json`). All 200
   calibration clean controls have deployed-prompt verdicts from the earlier 708-item run
   (`results/gate_calibration_full.json`); `results/tau_recompute_v2_summary.json` reports specificity on both sets.
2. **Controls for the within-stratum ΔΦ_V (§8, :163–170).** The protocol does not say which controls these cells use.
   The headline cells use each drop's own paired control (prevalence 0.50); cells with all 120 controls are reported
   alongside (`results/judgebench_v2_phi_v_recompute.json`).
3. **Strict-tier name.** Earlier docs called `category_retained = 0` (47 items) "the pre-registered strict subset". The
   protocol's strict tier is `expert_recoverable = 0` (30 items; §8, :169). Corrected in dabd527 and de03e44.
4. **Deliverable names (§12).** Delivered under other names, late, or not committed:
   - `perturbed_calibration_set_v2.json` → `results/judgebench_v2_tau1_final.json` (the 120 drops with per-item
     metadata) and `results/judgebench_v2_clean_controls.json`.
   - `tau_v2_human_audit.(json|md)` → the V4 records are the per-item `human_verdict` in the eight committed batch files
     `results/judgebench_v2_step0_*.json`; the 120 accepted items are in `results/judgebench_v2_tau1_final.json`.
     Confirmed-genuine rate over the four batches that feed the stratum: 120/203 = 59.1% (seed-42 SCALE 28/52, seed-99
     expanded 33/51, seed-137 expanded 18/33, seed-211 expanded 41/67). The four pilot batches are diagnostic-only and
     contributed 0 items to the stratum as a source batch; 7 stratum items (all from the seed-42 SCALE batch) carry
     edited text identical to a pilot-accepted drop.
   - `strata_spot_audit.md` → the spot audit is complete per protocol §7, whose numbers stand as the historical record;
     `results/strata_spot_audit.json` is a later per-item re-run of dose and negation — additional detail, not a
     correction to §7.
   - `calibration_verdicts_v2.json` → `results/judgebench_v2_panel_gate.json` and `results/judgebench_v2_panel_calib.json`
     (three judges, both prompts).
   - `pool_verdicts_v2` / audit_panel receipt v2 → `results/judgebench_v2_pool_<model>.json`, `audit_pool_v2/`,
     `results/audit_panel_receipt_v2_diagnosis.json`.
   - `tau_recompute_v2_summary.json` → produced with this erratum by `scripts/build_tau_recompute_v2_summary.py`, after the
     results had been seen in exploratory recomputes.
   - CHANGELOG + HF dataset-card v2 note → the v2 note is the dataset card (`docs/README_hf_v2.md`); no CHANGELOG file.
5. **Generator validation (§5, :84–88, with its 2026-09-28 clarification).** The gate is a single-batch rule: batches
   are iterated, with generator fixes between them, until one batch clears ≥ 95%, and that batch validates the
   generator. The four pilot batches were the iteration, each below 95% in its `v4_review` (seed-42 14/20, seed-99 8/12,
   seed-137 7/13, seed-211 12/16). The seed-42 SCALE batch is the one batch recorded as clearing the gate: 50/52 = 96.2%
   on its first V4 pass (`gate_passed: true` in its `v4_review`). Re-audited, the same batch is 28/52 = 53.8%, below the
   gate. On the re-audited verdicts, no batch has been shown to clear ≥ 95%. For context only, not the gate: the four
   batches that feed the stratum give 120/203 = 59.1% together. Every stratum item is V4-accepted (`human_verdict`
   ACCEPT on all 120).
