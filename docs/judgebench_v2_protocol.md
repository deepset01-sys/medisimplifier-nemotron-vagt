# JudgeBench v2 — Diagnosis-Stratum Rebuild: Pre-Registration Protocol
Status: FROZEN pre-registration. Committed before any judge is run or any statistic is
computed. Working principles: rigorous, precise, no invented data, no fabrication, verify
before asserting, human is final authority. Prepared 2026-09-20.

## 0. Why this exists
The v1 diagnosis stratum of MedSimp-JudgeBench is 85% mislabeled: `perturb_drop_diagnosis`
deleted a cue-word sentence, not the diagnosis (hand-audit of all 150; `results/
tau_hand_labels_150.json`). The headline +0.071 reversed to −0.144 on corrected labels,
and the project's central premise ("standard judges miss silently dropped diagnoses") is
currently UNSUPPORTED — only 9 genuine drops exist, "9 items is not a result." This
protocol rebuilds the stratum with genuine, hand-verified drops so the premise can be
tested for the first time, and reports whatever the result is.

## 1. Target and scope
- Build **≥ 100 GENUINE, hand-verified PRIMARY-diagnosis drops** (the clinically
  meaningful case). A clearly-stated SECONDARY diagnosis may be used only when the primary
  cannot be cleanly removed; each such case is labeled as secondary in the item metadata.
- Reuse the **200 unperturbed CLEAN CONTROLS** (τ=0); spot-verify a sample that each still
  states its diagnosis.
- **Spot-audit 50 each of dose / negation / lateral** (hand) to confirm those strata are
  sound (their perturbations are targeted substitutions, expected clean — but verified,
  not assumed). If any is contaminated, flag and treat like diagnosis.
- Source: the same `GuyDor007/medisimplifier-dataset` test split v1 used.
- The v1 contaminated stratum is KEPT and published as DEPRECATED (transparency), not
  deleted.

## 2. Roles (division of authority)
- **EDITOR = deepseek-ai/DeepSeek-V4-Pro** (Nebius Token Factory). Removes the target
  diagnosis. A tool, never trusted; every output is verified.
- **ORACLE = openai/gpt-oss-120b.** Independent semantic verifier (V3). Different model and
  provider from the editor.
- **HUMAN = final arbiter (V4).** Nothing enters the stratum as τ=1 without human
  confirmation; the human overrides all automated gates.
- Integrity constraints:
  * Neither editor nor oracle is a PANEL JUDGE (panel = Llama-3.3-70B, Qwen3-32B,
    Nemotron-Nano) — so construction cannot inherit a judge's blind spot.
  * Neither is the v1 TEACHER (Claude Opus 4.5) — no self-preference on the source text.
  * **Independence:** gpt-oss-120b (OpenAI) shares NO model family with any panel judge
    (Llama/Meta, Qwen/Alibaba, Nemotron/NVIDIA), the teacher (Claude/Anthropic), or the
    editor (DeepSeek) — a fully independent verifier.
- Decoding: temperature 0, fixed seeds, `max_tokens` generous; treat empty/None content as
  a retryable error, never a silent pass (reasoning-budget lesson).

## 3. Construction procedure (per item)
1. Identify the target diagnosis and ALL its surface forms in `clean_ref`: technical name,
   abbreviation, synonyms, and the lay paraphrase actually used (e.g. "leukemia" →
   "fast-growing blood cancer"), plus any header line (Admission/Discharge Diagnosis).
2. EDITOR removes every one of those forms — including headers — while leaving every other
   diagnosis, medication, dose, finding, and plan intact and the text fluent. Output: the
   edited summary only.
3. Verify via the four gates (Section 4). Keep only items passing ALL gates as τ=1.
   Discard or retry the rest. Yield, not correctness, varies.

## 4. Verification gates (τ=1 ONLY if all four pass)
- **V1 SURFACE (automated):** the target's surface forms (name + synonyms + the specific
  lay paraphrase) do not appear in the perturbed text — word-boundary match plus an
  embedding-similarity sweep for stray paraphrase above a fixed threshold.
- **V2 SCOPE (automated):** `diff(clean_ref, perturbed)` touches ONLY target-diagnosis
  spans; EVERY other source diagnosis / medication / dose still appears in perturbed
  (guards the new failure mode of collateral removal).
- **V3 SEMANTIC ORACLE (gpt-oss-120b):** two questions, both must be answered correctly —
  (a) "Could a reader still tell the patient has {target}?" → must be NO;
  (b) "Was any OTHER clinical fact removed or altered?" → must be NO.
- **V4 HUMAN (arbiter, final):** a human reads source + `clean_ref` + `perturbed` and
  confirms the target is genuinely, fully absent AND nothing else changed. Human overrides
  V1–V3.
  * First batch: hand-verify ALL.
  * Thereafter: hand-verify a ≥ 20% random audited sample, with any V1–V3 disagreement
    hand-verified in full.

## 5. Generator validation (before trusting it at scale)
The generator is "validated" only if the human-audited set shows **≥ 95%** of
τ=1-accepted items are genuine (V4 confirms V1–V3). The confirmed-genuine rate is
reported. If < 95%, the editor prompt / gates are revised and re-validated — revisions are
logged; we do not quietly lower the bar.

## 6. Ground-truth definition
- **τ = 1:** a human confirmed the target diagnosis is genuinely, fully absent from the
  summary and nothing else was removed/altered.
- **τ = 0:** unperturbed clean control (diagnosis present by construction; sample-verified).
- No item enters the stratum on construction alone — the v1 error.

## 7. Re-run plan (only the changed stratum)
- Run the 3 panel judges (Llama-3.3-70B, Qwen3-32B, Nemotron-Nano) on the v2 diagnosis
  stratum under BOTH prompts used before: the calibration/CoT prompt (to compare
  apples-to-apples with the +0.071) and the deployed-gate prompt.
- Run the 6-candidate pool (`gen_pool_verdicts`) on v2 diagnosis for the audit_panel
  recompute.
- Non-diagnosis strata verdicts (per the Section-1 spot-audit, now COMPLETE):
  * **Lateral: REUSE as-is** — 50/50 (100%) genuine.
  * **Dose: FILTER first** — ~22% contaminated (the dose regex catches lab values
    `g/dL`·`units/mL`, organ/blood volumes, and decimal substrings that are non-changes);
    restrict to medication context (adjacent drug name), drop those matches, re-verify
    before reuse.
  * **Negation: FILTER / CAVEAT** — ~36% borderline (flips on simplifier-added
    definitional glosses, garbled surface, or boilerplate; no hard non-errors); filter
    those out or disclose the rate.
  * **Diagnosis: REBUILD** — 6% genuine (this protocol).
  * (dose/negation/lateral rates are n=50 samples ±~13%; diagnosis is a full census.)
- Est. cost ~$15, ~1 day.

## 8. Analysis plan + PRE-REGISTERED BANDS (fixed before running)
Identical `vagt_core` pipeline, SEED=42, n_boot=1000, complete-case. Only the stratum
(clean v2 labels) changes.

**PRIMARY metric** — diagnosis ΔΦ_V (2-rater Llama+Qwen → 3-rater +Nemotron), paired
bootstrap 95% CI:
- **POSITIVE**  : point ≥ +0.05 AND CI lower bound > 0.
- **WEAK-POS**  : point +0.02 to +0.05, CI lower > 0 (reported as a small real effect).
- **NULL**      : CI includes 0 (and |point| < 0.05).
- **NEGATIVE**  : point ≤ −0.02 AND CI upper bound < 0.

**PREMISE TEST (answers the hostile-judge "9 items is not a result")** — per-judge RECALL
on the ≥ 100 genuine drops (τ=1), Wilson 95% CI, plus specificity (FP) on the 200 clean
controls:
- **INCUMBENT BLIND SPOT CONFIRMED** : Llama recall AND Qwen recall each < 0.30.
- **NO BLIND SPOT**                  : either incumbent recall ≥ 0.50.
- **NEMOTRON ADVANTAGE (material)**   : recall(Nemotron) − max(recall Llama, Qwen) ≥ +0.15
                                        with CI excluding 0.
- Nemotron over-flag reported explicitly: its FP on the clean controls (the
  paraphrase-mismatch check, now on genuinely-clean data).

**SECONDARY:** null-rater control, split-half, and the 6-candidate pool ΔΦ_V + CIs — all
recomputed on v2.

## 9. Honest floor + risk acceptance (agreed before starting)
- **HONEST FLOOR:** we report whatever the bands return — positive, weak, null, or
  negative. A null or negative ("no judge in the pool reliably catches silent diagnosis
  omission") is a legitimate, publishable result reported without spin, with the working
  gate attached.
- **RISK — YIELD:** fully removing a PRIMARY diagnosis while keeping coherence is hard;
  reaching ≥ 100 confirmed may require editing 150–200 candidates. Accepted.
- **RISK — OUTCOME:** this genuinely tests the premise for the first time and may not
  vindicate the original story. Accepted. The framing is chosen from the result, never
  before it.

## 10. Artifacts updated after the recompute (all from v2 numbers)
1. **README** — diagnosis claims rewritten to v2 results (correction/narrative decision
   lands here, now with REAL numbers).
2. **`tests/test_audit_panel.py`** — assertions set to v2 truth; the `ci_excludes_zero`
   regression lock removed unless v2 genuinely supports it. Tests assert reality, not a
   re-lock.
3. **`app/demo.jsx` Act 2** — `PANEL_CANDIDATES` updated to v2 (Act 1 / Case-44 untouched).
4. **`results/audit_panel_live_receipt.json`** — regenerated from the endpoint re-scored on
   the v2 pool (endpoint pool verdicts regenerated on v2).
5. **`docs/NEMOTRON_INSIGHTS.md` Finding 1** — updated to v2.
6. **HuggingFace MedSimp-JudgeBench** — v2 published with changelog + v1 diagnosis-label
   deprecation note. (External publish — owner credentials/action.)

## 11. Integrity rules (frozen)
- No item is τ=1 without human confirmation.
- No number is reported that is not computed from committed verdicts on the frozen v2
  stratum.
- The v1 stratum and its numbers are preserved and documented as deprecated, not erased.
- Editor/oracle prompts, seeds, and any revisions are committed and logged.
- The framing of the final result is derived from the result, after Section 8 runs.

## 12. Deliverables (filenames, produced in order)
- `docs/judgebench_v2_protocol.md` (this file — frozen on commit)
- `perturbed_calibration_set_v2.json` (+ per-item metadata: target dx, primary/secondary,
  surface forms, V1–V4 outcomes)
- `tau_v2_human_audit.(json|md)` (V4 records + confirmed-genuine rate)
- `strata_spot_audit.md` (50 each dose/lateral/negation)
- `calibration_verdicts_v2.json` (3 judges, both prompts)
- `pool_verdicts_v2` / audit_panel receipt v2
- `tau_recompute_v2_summary.json` (primary + premise-test + secondary, per Section 8)
- CHANGELOG + HF dataset-card v2 note
