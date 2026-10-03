# MediSimplifier — Nemotron × VAGT

[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-blue)](https://nebius.com/services/token-factory)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron%203-76B900)](https://nebius.com/services/token-factory/nemotron)
[![HuggingFace Dataset](https://img.shields.io/badge/HF-Dataset-yellow)](https://huggingface.co/datasets/GuyDor007/medisimplifier-dataset)
[![JudgeBench](https://img.shields.io/badge/HF-MedSimp--JudgeBench-yellow)](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

> **Nebius x NVIDIA Global AI Hackathon submission by Shmulik Avraham.**
> Built on top of [MediSimplifier-Nebius](https://github.com/deepset01-sys/medisimplifier-nebius) — 🥇 First Place winner of the Nebius Serverless AI Builders Challenge.
> The Nemotron teacher pipeline, 3-judge calibration panel, VAGT measurement framework (developed as a direct response to v1's κ=0.11 finding, first applied empirically in v2), and v2 training infrastructure were built for this hackathon.

Patients go home with discharge summaries written for clinicians — dense with abbreviations and diagnoses most people cannot read. **MediSimplifier v2** rewrites them into plain language and returns a safety verdict: on 120 hand-verified silently-dropped diagnoses, under the deployed gate prompt, two standard judges (Llama-3.3-70B, Qwen3-32B) each miss ~53%; NVIDIA Nemotron Nano catches ~92% — yet agreement between the judges shows no detectable change when Nemotron is added (Fleiss κ 0.214 → 0.179; Δ −0.0356, 95% CI [−0.1310, +0.0565]), so an agreement metric would not have registered the fix.

**Nebius-native by construction.** Every stage runs on Nebius: teacher generation, the three-judge panel, calibration, and pool-verdict generation on **Token Factory** (per-token; Qwen3-32B on a dedicated Nebius endpoint); training, evaluation, and merge as **Nebius Jobs** on H100; and the live safety gate as a persistent **Nebius GPU Endpoint** (vLLM). This is the architecture, not a deployment afterthought.

**What's new in v2 — three things:**

- **The finding (measured, then stress-tested against our own error).** Two standard judges — Llama and Qwen — each miss roughly **half** of *silently dropped diagnoses* under the deployed gate prompt: on 120 hand-verified patient-invisible drops, recall is **Llama 47%, Qwen 47%** (Wilson 95% CIs 38.0–55.6%, above the 30% below which the protocol's pre-registered premise test returns *incumbent blind spot confirmed*; A5 reports the test under both prompts), versus NVIDIA **Nemotron Nano's 92%**. The two pass the same **41** drops as SAFE (34 would be expected if their misses were independent; Nano catches 33 of the 41): those 41 are the blind spot the two share. Adding Nemotron as a third rater *raises* truth-alignment, because it breaks that shared blind spot, while rater agreement shows no detectable change (Fleiss κ 0.214 → 0.179, Δ −0.0356 [−0.1310, +0.0565]; A6) — so an agreement statistic such as Cohen's κ (Project v1's only metric) would not register the gain. On the clean v2 diagnosis stratum the veridicality-anchored dependability Φ_V rises **0.476 → 0.553** (paired Δ **+0.0765**, 95% CI **[+0.0516, +0.0992]**, n = 240, 1,000 resamples) — at the benchmark's 50% drop share, under the deployed prompt; reweighted to 20% drops, the same verdicts give **+0.0066 [−0.0264, +0.0384]**, no detectable lift (A8 threat 11). **The history of this number is part of the finding, not hidden from it.** Our first, automated pass at this benchmark reported the same measurement as **+0.071 [+0.055, +0.087]** (the diagnosis stratum of 708 machine-labeled items, n = 333) — and its labels were **wrong**: hand-verifying them showed the diagnosis "positive" class was **~85% mislabeled** (128 of 150 items still contained the diagnosis; 9 were genuine drops), so the +0.071 does not measure the detection of silent drops. An earlier version of this README said that +0.071 **inverted to −0.144 [−0.195, −0.098] — REFUTED** ([`results/tau_recompute_summary.json`](results/tau_recompute_summary.json)). The sign change comes from the drop share, not the labels: the −0.144 cell has 9 drops in 333 items (2.7%), the +0.071 cell 138 in 333 (41%), and Φ_V depends on that share (A8 threats 11 and 12). Reweighted to 41% drops, the −0.144 cell gives **+0.0718 [+0.0046, +0.1154]**; reweighted to 2.7%, the +0.071 cell gives **−0.1931 [−0.2541, −0.1343]**. These figures also pair Llama's and Qwen's verdicts, stored from Project v1, with Nemotron's under a different prompt, and Llama's stored column repeats one verdict per item index. With all three judges under the deployed prompt and 41% drops, the automated labels give +0.0426 [+0.0264, +0.0593] and the hand labels +0.0323 to +0.0502 (four ways of scoring the borderline and non-drop items); three of the four CIs include zero (no detectable lift), and the fourth, +0.0502 [+0.0041, +0.0944], lies above it. At those four scorings' own 2.6–9.9% drop shares, both label sets give negative point estimates ([`results/tau_recompute_v1_matched.json`](results/tau_recompute_v1_matched.json), [`docs/judgebench_v2_protocol_erratum.md`](docs/judgebench_v2_protocol_erratum.md)). Nine genuine drops cannot settle the sign. We did not scrub the +0.071; we rebuilt the benchmark. All of this is v2's own development history — VAGT was built and first applied in *this* project; the +0.071 was our early automated result, **not** a finding from v1 (the prior serverless project, where VAGT was never run). On **120 drops each read in full and confirmed patient-invisible** (no automated accept) — 120 genuine drops rather than nine — ΔΦ_V is **+0.0765**, on labels a skeptic can open and check. Under the deployed prompt it holds on harder subsets, scored with each drop's own paired control: **+0.0656 [+0.023, +0.107]** where even the broad category is gone (47 drops), **+0.1011 [+0.053, +0.142]** on the protocol's strict tier, where the name was the only clue (30). Under the calibration prompt the strict-tier lift is not detectable (**+0.0236 [−0.015, +0.065]**; band NULL). An earlier version reported attenuation toward null on the 47; that came from scoring them against all 120 controls, which lowers prevalence from 0.50 to 0.28. Most of that attenuation is prevalence: reweighted to the same share, the full 120-drop stratum gives +0.0300 [−0.0003, +0.0578], at the edge of NULL, and the 47 sit 0.011 below the full stratum at 50% and 0.014 below it at 28% ([`results/judgebench_v2_phi_v_recompute.json`](results/judgebench_v2_phi_v_recompute.json), [`results/judgebench_v2_prevalence_sensitivity.json`](results/judgebench_v2_prevalence_sensitivity.json); A8 threat 11). We measure panel dependability with a criterion-anchored generalizability-theory decomposition (Φ_V from G-theory), anchoring to **hand-verified** error τ rather than inter-rater agreement — because agreement is not validity.
- **Nemotron as teacher and judge.** The student was fine-tuned on **7,983** references written by **Nemotron Super** (replacing Claude Opus); the safety panel adds **Nemotron Nano** as the diagnosis-drop tripwire — teacher and judge both served per-token on Nebius Token Factory. (The student base is Llama-3 OpenBioLLM; the evaluation yardstick is still the v1 Claude references.)
- **Measured, not just built.** A 708-item deployed-gate calibration, a **1,001-output** diagnosis-retention self-audit, and an independent **dual-auditor** review (Claude Sonnet 5 + Gemini 2.5 Pro) quantify how the gate actually behaves — confirming genuine diagnosis drops in only **2 of 20** flagged cases (see B5).

**Try it in ~30 seconds.** `POST /v1/simplify` with a discharge summary returns the plain-language rewrite plus a safety verdict; or run the gate on any `(original, simplified)` pair directly, no endpoint needed — full quickstart and a live `curl` in **B2**. **Two tracks follow:** **Track A — Research Design** (estimand, benchmark, protocol, VAGT derivation, per-judge calibration, the decoupling, threats to validity) and **Track B — Product Design** (the `POST /v1/simplify` contract, the decision rule with Nemotron as the diagnosis-drop tripwire, measured operating characteristics — DISAGREE false alarms (45.5% of DISAGREEs on the hand-verified v2 stratum at 50% drops, 45 of 99; 70.1–74.1% on the 708-item calibration set with its hand-audited diagnosis labels, where 34.7% fire on clean text; the share rises as real errors get rarer, see B5), ~27 s per request — Nebius deployment, and known issues, including that the Qwen judge was briefly swapped mid-project (Qwen3-32B → Qwen3-30B-A3B) but is restored to Qwen3-32B and recalibrated, see B8). This is a research prototype: unauthenticated, not clinician-validated, and not for real patient data.

## Why VAGT — the panel selection finding

That finding generalizes into a decision tool. VAGT is not just a measurement — it answers a **decision**: given a judge panel with a shared blind spot, *which judge should you add to fix it?* Adding more raters of the same kind doesn't help — shared bias doesn't shrink with panel size — so the useful question is *which* rater breaks the blind spot, and by how much. VAGT scores each candidate by the gain in truth-anchored dependability (**ΔΦ_V**) it delivers on the panel's weakest stratum, with a bootstrap confidence interval. We ran the full analysis on our own gate: incumbent panel = **Llama-3.3-70B + Qwen3-32B** (under the deployed prompt each catches 56 of the 120 silent diagnosis drops, and both pass the same 41), scoring six candidate third judges (Nemotron Nano — our first automated pass's pick — plus five alternatives) on the **120-item hand-verified v2 diagnosis stratum** (with its 120 paired clean controls).

| Candidate | Family | Size | diag ΔΦ_V | 95% CI | recall τ=1 | spec τ=0 |
|--|--|--|--|--|--|--|
| **DeepSeek-V4-Flash** | DeepSeek | — | **+0.1238** | [+0.1024, +0.1440] | 99% | 66% |
| **gpt-oss-120b** *(recommended)* | OpenAI | 120B | **+0.1220** | [+0.1000, +0.1416] | 95% | 73% |
| Nemotron-3-Ultra | NVIDIA | 550B | +0.0781 | [+0.0552, +0.1003] | 89% | 58% |
| Nemotron Nano | NVIDIA | 30B | +0.0765 | [+0.0516, +0.0992] | 92% | 56% |
| Nemotron-3-Super | NVIDIA | 120B | +0.0480 | [+0.0225, +0.0720] | 93% | 29% |
| gemma-3-27b-it | Google | 27B | +0.0066 | [−0.0108, +0.0261] | 48% | 76% |

*Each candidate added to the Llama+Qwen incumbent, on the **v2 clean 240-item diagnosis stratum** (120 hand-verified τ=1 drops + 120 paired τ=0 controls, i.e. 50% drops — DeepSeek on its 233 complete rows, 51% — and ΔΦ_V depends on that share, A8 threat 11; deployed prompt; paired 1000-iteration bootstrap 95% CI, SEED=42; [`results/judgebench_v2_pool_table.json`](results/judgebench_v2_pool_table.json), [`scripts/run_pool_judgebench_v2.py`](scripts/run_pool_judgebench_v2.py)). **DeepSeek and gpt-oss are statistically tied at the top** (overlapping CIs) and have point estimates about 1.6× Nano's and Ultra's; **gpt-oss is recommended** by the selector's reliability tie-break, which is decided by error count (gpt-oss 0, DeepSeek 7 of 240 — token-budget truncations) — a tie-break we added **after** seeing this result (see below). gemma straddles zero (null). These are per-candidate CIs vs the incumbent, not paired between-candidate tests. **Scope:** only the diagnosis stratum was rebuilt on clean labels — the automated-pass dose/negation/lateral columns are not yet re-run on clean labels, so they are omitted here. (An earlier, fully-automated pass produced this table on 708 machine-labeled items — ~85% of whose diagnosis positives were mislabeled; those numbers are superseded — see "The finding" above.) Full per-candidate verdicts in [`results/judgebench_v2_pool_<slug>.json`](results/).*

Three findings:

- **Within the Nemotron family, scale buys no *measurable* gain, 30B to 550B.** A **550B** Nemotron (Ultra, +0.0781 [+0.055, +0.100]) breaks the incumbents' diagnosis blind spot no better than a **30B** one (Nano, +0.0765 [+0.052, +0.099]) — the two CIs overlap almost entirely, statistically indistinguishable across an **18× size range**. The repair comes from the family's detection ability, already present at 30B. But note the family is no longer at the top: on clean labels **two other families out-detect both** (DeepSeek and gpt-oss, ~+0.12). (Per-candidate CIs vs the incumbent, not a paired between-candidate test — so "indistinguishable," not "proven equal.")
- **A different family can break the blind spot — and here two do it best.** OpenAI's gpt-oss-120b and DeepSeek-V4-Flash **lead the table** (~+0.12, CIs exclude 0), out-detecting the Nemotrons; Google's gemma-3-27b-it barely moves it (**+0.0066, CI [−0.011, +0.026] — straddles zero, indistinguishable from no help**) — its recall, 57 of 120, is one drop above each incumbent's 56, and it catches 11 of the 41 drops both of them pass. So a different family was *necessary but not sufficient*: it can break the blind spot (gpt-oss and DeepSeek did; gemma did not), but only if the model can actually catch the error. This is an observation on six candidates, not a general law.
- **On clean labels the recommendation changes — gpt-oss-120b, not Nemotron Nano.** Our first, automated pass recommended Nano, but that rested on the contaminated 708 machine-labeled items, where the top candidates sat in a ~+0.07 three-way tie. Rebuilt on the 120-item hand-verified v2 diagnosis stratum, two candidates lead on point estimates: **gpt-oss-120b +0.1220 [+0.1000, +0.1416]** and **DeepSeek-V4-Flash +0.1238 [+0.1024, +0.1440]** — point estimates about *1.6×* Nano's **+0.0765 [+0.0516, +0.0992]** (and Ultra's +0.0781 [+0.0552, +0.1003]). Compared on the same rows, neither leader's CI clears both Nemotrons: on all 240 rows gpt-oss's lies just above Nano's (lower bound +0.1000 vs +0.0992) and touches Ultra's (+0.1003); DeepSeek's is on its 233 completed rows, and on those rows it overlaps both (Nano's upper bound there is +0.1056, Ultra's +0.1029). gpt-oss and DeepSeek are **statistically tied** on ΔΦ_V (overlapping CIs; ~+0.104 vs +0.101 after subtracting the permutation-null baseline), so the pick is broken on **reliability, not margin**: the selector's tie-break takes the candidate with fewer ERROR verdicts — gpt-oss **0**, DeepSeek **7 of 240** — and would consult specificity (gpt-oss 73% vs DeepSeek 66%) only if the error counts were equal. **We added this tie-break after seeing the v2 result, knowing it would select gpt-oss;** the selector's earlier tie-break (higher mean ΔΦ_V) selects DeepSeek, by +0.0018 — a gap that comes from scoring DeepSeek on its 233 completed rows; on those same rows gpt-oss is within +0.0001. DeepSeek's 7 errors are a **token-budget artifact**: it was judged at `max_tokens` 4000, gpt-oss at 8000. Re-running those 7 items (3 repeats per budget) shows every failure is a call that spent its whole budget on hidden reasoning and returned no verdict (`finish_reason=length`) — 5 of 21 calls at 4000, 1 of 21 at 8000; no timeouts or API errors ([`results/judgebench_v2_deepseek_budget_check.json`](results/judgebench_v2_deepseek_budget_check.json), [`scripts/check_deepseek_budget_v2.py`](scripts/check_deepseek_budget_v2.py)). Filling the 7 items from the 8000-token re-run gives DeepSeek 0 errors and ΔΦ_V **+0.1208 [+0.1001, +0.1410]** on all 240 items; the tie-break then falls through to specificity (gpt-oss 73% vs DeepSeek 66%) and still selects gpt-oss. Read the top of the table as a tie. The order within it depends on the drop share. Each on its own rows, as the selector ranks them, gpt-oss has the higher point estimate at every share tested below 50% (1–49%; at 20%: +0.0736 vs DeepSeek's +0.0606, CIs overlapping), and on the same 233 rows it is ahead up to 50%. Below about 40% drops two terms favour it: adding DeepSeek raises the panel's bias on clean controls (which counts for more as drops get rarer) while adding gpt-oss slightly lowers it, and gpt-oss adds less rater spread (σ²_R) at every share; from about 40% to 49% the spread term alone keeps it ahead. The selector picks gpt-oss at every share from 2% to 51% (above that its pick alternates between gpt-oss and DeepSeek as their ΔΦ_V cross the selector's 0.01 rounding-bin edges; A8 threat 11), though below about 8% drops gpt-oss's own lift is a point estimate only (at 5%: +0.0229 [−0.0085, +0.0551], which includes zero; [`results/judgebench_v2_prevalence_sensitivity.json`](results/judgebench_v2_prevalence_sensitivity.json), A8 threat 11). At 50%, the lift is detection-specific (permutation-null p = 0.001) and replicates across two patient-disjoint halves (split-half **+0.122 / +0.122**, POSITIVE in both halves). Three caveats: gpt-oss-120b is **4× Nano's size (120B vs 30B)** — clean labels trade cost for materially higher detection, reversing the automated pass's "smallest-and-cheapest" tie-break — and this recommendation is **diagnosis-stratum only**; the earlier four-stratum collateral comparison (dose/negation/lateral) has not been re-run on clean data, so that cross-stratum tie-break no longer applies here. Third, gpt-oss's +0.1220 is measured on items gpt-oss itself screened: it was the benchmark's *oracle* for τ=1 acceptance (and DeepSeek-V4-Pro, the same family as DeepSeek-V4-Flash, was the *editor*), so the top of the pool ranking is partly by construction. Nano's **+0.0765** is free of this circularity — the panel judges were kept out of benchmark construction (A8 threat 10).

**Robustness — the null-rater control.** Is the diagnosis lift real detection, or just a flag-rate artifact? We test each candidate against its **own τ-blind permutation**: shuffle its verdict column across the 240 items — preserving its exact UNSAFE rate but destroying any correlation with the true label — recompute ΔΦ_V, 1,000 times ([`scripts/run_null_control_v2.py`](scripts/run_null_control_v2.py), [`results/judgebench_v2_null_control.json`](results/judgebench_v2_null_control.json)). Appending *any* column with a non-trivial flag-rate buys a little Φ_V for free — the permutation null centers at **~+0.02** for five of six candidates on this balanced stratum (gemma's: +0.006; the null is for this 50/50 composition, A8 threat 11) — so a raw ΔΦ_V near +0.02 proves nothing on its own. But the real detectors clear it: **four of six candidates lie above all 1,000 of their own shuffles** (permutation p = **0.001**, the floor at 1,000 shuffles) — Nano and Ultra by +0.023 and +0.026 over their largest shuffle, gpt-oss and DeepSeek by +0.072 and +0.073, at a **detection-corrected +0.104 / +0.101** after subtracting the flag-rate baseline. **Nemotron-Super sits at the top edge of its null:** one of its 1,000 shuffles ties its +0.048 exactly, so with ties counted by the script's ≥ rule, as gemma's 30 are, p = 0.002, below 0.05. The committed file's 0.001 for Super leaves that shuffle out: the file was generated while σ²_N was still estimated as mean ε² (A4 now divides Σε² by (N−1)(R−1)), and σ²_N cancels in Φ_V only in exact arithmetic — under the earlier estimator the tied shuffle's ΔΦ_V came out 1.1 × 10⁻¹⁶ below the real one in floating point, so the exact ≥ comparison excluded it. Re-running [`scripts/run_null_control_v2.py`](scripts/run_null_control_v2.py) now gives 0.002 for Super and changes no other value ([`scripts/check_null_control_ties_v2.py`](scripts/check_null_control_ties_v2.py), [`results/judgebench_v2_null_control_ties.json`](results/judgebench_v2_null_control_ties.json)). The one failure is the control working as intended: **gemma's +0.0066 sits *inside* its own null band [−0.010, +0.024], p = 0.449 — statistically indistinguishable from a random flagger**, exactly matching its 48% recall. That is detection you cannot fake by flagging more; the null baseline is the control showing the method rewards *detection*, not flag rate.

**Split-half replication** (deployed prompt): splitting the 120 patients 60/60 so no patient appears in both halves ([`scripts/run_split_half_v2.py`](scripts/run_split_half_v2.py), [`results/judgebench_v2_split_half.json`](results/judgebench_v2_split_half.json)), the top tier holds on **both** halves — gpt-oss **+0.122 / +0.122** and DeepSeek **+0.118 / +0.129**, POSITIVE on each; Nemotron Nano and Ultra hold too. The weaker candidates don't: Nemotron-Super is POSITIVE in one half but null in the other (CI-width at n ≈ 120), and gemma is null in both. The recommendation survives the split that matters. (Nothing is fitted on either half, so this shows the ranking is stable across patients; it is not an out-of-sample test.)

The **[`/v1/audit_panel`](#b3-api-contract)** endpoint runs exactly this analysis on any incumbent panel + candidate pool, returning the recommended judge, its ΔΦ_V, and a bootstrap CI. The **v2 recommendation is gpt-oss-120b (+0.1220, CI [+0.1000, +0.1416])** (caveats: A8 threats 10 and 11) — an offline recompute on the clean stratum in [`results/audit_panel_receipt_v2_diagnosis.json`](results/audit_panel_receipt_v2_diagnosis.json). The CPU `/v1/audit_panel` service **serves this v2 pool** and returned the same answer live — captured in [`results/audit_panel_live_receipt_v2.json`](results/audit_panel_live_receipt_v2.json) from the `audit-cpu-v2` image on 2026-09-25. It now runs the `audit-cpu-v2.1` image, built after the σ²_N estimator fix (A4), and is started for judging windows rather than always on (B2). The earlier live receipt ([`results/audit_panel_live_receipt.json`](results/audit_panel_live_receipt.json)) records the **superseded** pick from the automated pool (Nemotron Nano, +0.0706) and is preserved unchanged as a genuine capture. The endpoint re-ranks **pre-computed** verdict files (`audit_pool_v2/verdicts/`; the earlier pool stays in `audit_pool/`) on CPU in milliseconds; it does not call the candidate models live, so adding a genuinely new judge means generating its verdicts first (`gen_pool_verdicts.py`).

## What this project does

The result above is the point; this section is the package around it. The submission ships as a reproducible whole — a discharge-summary student model, the three-judge safety gate that scores its output, the VAGT measurement framework that anchors the panel to ground truth, and a live Nebius GPU Endpoint that serves the model behind the gate. The models, the MedSimp-JudgeBench benchmark, and the raw calibration verdicts are public on HuggingFace, and every stage — teach, train, evaluate, merge, deploy — rebuilds from committed configs as a Nebius Job or Token Factory call.

## What's new in v2 (vs v1)

The Nebius Serverless Challenge submission (v1) was training + serving + dual-judge safety. This v2 submission extends it with **Nemotron as teacher and third judge**, measured gate operating characteristics, and a diagnosis-retention audit:

| | v1 (Nebius Serverless Challenge 🥇) | v2 (This Hackathon) |
|--|--|--|
| Teacher model | Claude Opus 4.5 (proprietary) | ✅ Nemotron Super 120B via Token Factory |
| Training data | Claude references (9,999) | ✅ Nemotron Super references (7,983 train) |
| Student model | OpenBioLLM v1 | ✅ OpenBioLLM v2 (Nemotron-taught) |
| Safety judges | Llama + Qwen (2 judges) | ✅ + Nemotron Nano (3 judges, calibrated) |
| Judge calibration metric | Cohen's κ only | ✅ VAGT — σ²_B, σ²_R, σ²_N, Φ_V |
| Robust statistics validation | ❌ (post-submission only) | ✅ Fleiss κ and Krippendorff α recomputed on v2 clean stratum (n=240): κ 0.214 → 0.179 as Φ_V rises, a change that is not detectable (Δ −0.0356 [−0.1310, +0.0565]); near-identical on binary complete-case data, so one robustness check, not two independent ones |
| Measurement framework | Cohen's κ | ✅ VAGT — detects shared blind spots invisible to κ |
| Safe Endpoint | vLLM + dual-judge guardrail | ✅ vLLM + calibration-informed gate (2-judge rule + advisory Llama; flag / block / strict modes) |
| Gate operating characteristics | ❌ not measured | ✅ 708-item re-run through deployed gate prompt (0 ERRORs) — DISAGREE 20.8%, Qwen FP 9.5% (see B5) |
| Diagnosis-retention audit | ❌ not measured | ✅ 1,001 student outputs through gate + dual-auditor review (Claude Sonnet 5 + Gemini 2.5 Pro); 2/20 confirmed diagnosis drops (see B5) |
| Safety enforcement modes | flag/block only | ✅ + strict mode: DISAGREE blocks (Nemotron diagnosis-drop tripwire enforces) |
| VAGT panel-selection service | ❌ not built | ✅ /v1/audit_panel — callable Nebius service: given any incumbent panel + candidate pool, recommends the judge to add (ΔΦ_V on blindest stratum + bootstrap CI); 6-candidate pool validated on MedSimp-JudgeBench (see Why VAGT) |
| Judge pool experiment | ❌ not measured | ✅ 5×708 verdicts (gemma 27B / gpt-oss 120B / Nemotron Super 120B / DeepSeek Flash / Nemotron Ultra 550B) — scale flat within Nemotron family (30B ≈ 550B); Nano recommended on merit (automated calibration pass; on clean pool gpt-oss 120B and DeepSeek Flash tie at the top, ΔΦ_V +0.1220 / +0.1238) |
| Reproducibility | Public HuggingFace adapters | ✅ Public HuggingFace dataset + adapters v2 |

The novel v2 finding: VAGT decoupling — adding Nemotron Nano as third judge raises Φ_V on diagnosis (0.4764 → 0.5529, ΔΦ_V +0.0765 [+0.0516, +0.0992], at the stratum's 50% drop share — A8 threat 11) while inter-rater agreement shows no detectable change (Fleiss κ 0.214 → 0.179, Δ −0.0356 [−0.1310, +0.0565]; full decomposition in A6), so Cohen's κ — the only metric used in Project v1 — does not register the gain here.

## Choose your track

This README is organized into two tracks — read whichever fits:

- **[Track A — Research Design](#track-a--research-design)** — the estimand, MedSimp-JudgeBench, judge protocol, the VAGT decomposition, per-judge calibration, the decoupling, and threats to validity. *(For the statistician.)*
- **[Track B — Product Design](#track-b--product-design)** — the `POST /v1/simplify` contract, the safety-gate decision rule, measured operating characteristics, the model card, Nebius deployment, and known issues. *(For the developer / hackathon judge.)*

## Track A — Research Design

### A1. Question & estimand

**Research question.** Do consensus statistics — Fleiss κ, Krippendorff α — detect when adding a third judge improves a panel's accuracy against ground truth?

**Estimand.** For a panel of R raters scoring items with known ground-truth status τ ∈ {0,1} (here, whether a medical simplification was corrupted), **Φ_V** is the proportion of variance in the panel mean attributable to ground truth, after bias-correcting the raters' shared error. It answers "how much of what the panel agrees on is *truth* rather than *shared bias*" — a question κ and α cannot pose, because they never reference τ. The formal decomposition is in A4. Φ_V is defined at the stratum's corrupted share *p*, so the same panel scores differently at different shares (A8 threat 11).

**Falsifiable prediction.** Adding a rater that breaks a shared blind spot should **raise Φ_V** and **lower σ²_B** on the blind-spot stratum, and **may lower κ/α** — because the new rater necessarily disagrees with the two that share the blind spot. If instead κ/α tracked accuracy, they would *rise* whenever the panel got more accurate; VAGT predicts they can move the opposite way. A6 reports the test, at each stratum's own corrupted share (50% for the v2 diagnosis stratum); reweighted to rarer drops, the same verdicts show no detectable rise in Φ_V for Nano under the deployed prompt below about 29% drops and a fall at about 7% and below (the reweighting reports Φ_V, not σ²_B; A8 threat 11).

**VAGT origin.** VAGT was developed in the six weeks between submissions — after v1's κ=0.11 finding (July 15) and before the v2 window opened (August 26). The estimand files (`vagt_section.md`, `vagt_estimand.md`) live in the v1 repo but were not part of the v1 submission. v2 applies the decomposition to real judge verdicts, with Nemotron Nano as the third rater that makes the 3-rater decomposition possible.
### A2. Benchmark — MedSimp-JudgeBench

**Construction.** MedSimp-JudgeBench is **708 items**: **200 clean controls** (τ=0 — faithful simplifications) and **508 corrupted** (τ=1 — a single medical error injected into an otherwise-faithful simplification), spanning four error types.

**Corrupted items by error type** (counted from `nemotron_calibration_full.json`):

| Error type | Injection | Count |
|--|--|--|
| diagnosis (silent drop) | a secondary diagnosis removed without replacement | 150 |
| lateral (side swap) | a laterality / side reference swapped | 150 |
| negation (flip) | a clinical statement's polarity flipped | 113 |
| dose (10×) | a dosage scaled by 10× | 95 |
| **Total corrupted** | | **508** |

200 clean + 508 corrupted = 708.

**Operationalizing "silent drop."** A diagnosis-corrupted item removes one **secondary** diagnosis from the simplification with no replacement and no other change (automated 708-item pool construct; the v2 hand-verified stratum uses **primary**-diagnosis drops — see A6 and [`docs/judgebench_v2_protocol.md`](docs/judgebench_v2_protocol.md)) — e.g. idx 146, a Parkinson-disease discharge summary noting *"familial Parkinsonism and depression,"* where the simplification keeps the Parkinsonism but silently omits depression. That single injected change is what makes τ known by construction.

**Ground-truth coding.** Each item carries τ_i ∈ {0,1}: **τ=1** if corrupted, **τ=0** if clean. This constructed label — not any model's judgment — is the ground truth that every recall, Φ_V, and calibration figure is measured against (full coding in A4).

**Reference generation (v2).** The benchmark's reference simplifications were regenerated with Nemotron Super for v2: **519 unique calls fanned out to 708 records, 0 errors** ([`nemotron_references.json`](nemotron_references.json)). The reported calibration and pool-verdict generation judged the v1 references (`calibration_verdicts.json` — authored by the v1 teacher, Claude Opus 4.5); `nemotron_references.json` is a Nemotron-Super regeneration of those references, generated but **not** the judged text behind any reported recall or Φ_V figure.

**Provenance.** The benchmark items and perturbation types are from the v1 repo; the VAGT τ-anchoring and calibration, the hand-verified diagnosis τ, and the **Nemotron references are new in v2**. The v2 hand-verified stratum is published as [`chambul/MedSimp-JudgeBench-v2`](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench-v2) (120 τ=1 + 120 paired τ=0, plus 172 supplementary controls). Published (v1 benchmark): [`chambul/MedSimp-JudgeBench`](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench).
### A3. Judge panel & protocol

Nemotron Nano joins Llama-3.3-70B (same-family as the OpenBioLLM student) and Qwen3-32B (cross-family) as a third safety judge, all via Token Factory. Judge prompt is the 4-step CoT-with-anti-sycophancy prompt (`safety_eval_v2.py`) developed and run in v1 (Llama+Qwen dual-judge, Cohen's κ), reused verbatim for v2's VAGT calibration — VAGT is new in v2. In the automated 708-item pass only Nemotron was judged with it; Llama's and Qwen's verdicts there are stored from Project v1's calibration run (A8 threat 9).

> **Note on the Qwen judge.** All calibration, VAGT, and recall numbers in this README describe the `Qwen/Qwen3-32B` panel. The deployed gate runs the same Qwen3-32B via a dedicated Nebius endpoint — see B8.

**Judge parameters (safety_gate.py):**

| Judge | temperature | thinking | max_tokens |
|--|--|--|--|
| Llama-3.3-70B | 0 | off | 2,000 |
| Qwen3-32B | 0 | off* | 8,000 |
| Nemotron Nano | 0 | off* | 8,000 |

> *`enable_thinking=False` is set, but both **Nemotron Nano and Qwen3-32B** reason internally at inference regardless (see the reasoning-token-budget finding in [A7](#a7-results-iii--nemotron-super-as-teacher)) — only Llama does not, which is why both reasoning judges get the larger 8,000-token budget. Qwen3-32B is served via a dedicated Nebius endpoint (see B8).

> **On reasoning budget.** In the automated 708-item pass only Nemotron was judged in this project, at `max_tokens=8000`; Llama's and Qwen's verdicts are stored from Project v1's calibration run (A8 threat 9). The v2 panel ran the two reasoning judges, Qwen and Nemotron, at 8,000 under both prompts and Llama at 2,000 (deployed prompt) or 3,000 (calibration prompt) ([`scripts/run_panel_judgebench_v2.py`](scripts/run_panel_judgebench_v2.py)), so on v2 Nemotron's recall edge over Qwen is not a budget difference. Two of the three judges (Nemotron Nano, Qwen3-32B) reason internally regardless of `enable_thinking=False`; Llama does not. The deployed gate runs Llama at 2,000 and Qwen/Nemotron at 8,000 (see the A3 table).
### A4. Measurement — VAGT

Consensus statistics (Cohen's κ, PABAK, Krippendorff α) measure whether judges *agree with each other*. They never measure whether judges agree with the *truth* — so they reward a shared blind spot and penalize the one judge that breaks it. **VAGT (Veridicality-Anchored G-Theory)** fixes this by anchoring to ground truth (the injected error type), decomposing each stratum into:

    consensus  c_i = mean_r X_{ir}
    shared bias b_i = c_i − τ_i ;  σ²_B = mean_i b_i² − σ²_N/R   (bias-corrected)
    rater bias  α_r = X̄_{·r} − X̄ ;  σ²_R = mean_r α_r²
    noise       ε   = X − c − α ;   σ²_N = Σ ε² / ((N−1)(R−1))   (unbiased)
    Φ_V = σ²_τ / (σ²_τ + σ²_B + (σ²_R + σ²_N)/R)          (higher = more dependable vs truth)
    (σ²_N/R appears in both σ²_B and the denominator and cancels: Φ_V = σ²_τ / (σ²_τ + mean b² + σ²_R/R))

**Coding.** Each judge verdict is coded X_ir ∈ {0,1} with **UNSAFE = 1, SAFE = 0**; the ground-truth label is τ_i ∈ {0,1} with **corrupted = 1, clean = 0**. A stratum = the items corrupted on one feature (τ=1) plus the shared clean controls (τ=0). **R** is the number of raters (2 for Llama+Qwen, 3 with Nemotron).

**σ²_τ (target variance).** For binary τ at corrupted-prevalence *p*, σ²_τ = *p*(1−*p*) — the signal each panel is asked to track (the numerator of Φ_V and its leading denominator term). On the diagnosis stratum (*p* = 0.41) this is **0.243 [0.231, 0.249]** measured, matching the theoretical 0.41 × 0.59 = **0.242** (automated pass). Every Φ_V on the v2 hand-verified stratum in this README is at *p* = 0.50 by design (120 + 120), so σ²_τ = 0.25 there, unless stated otherwise (A8 threat 11).

**Estimation.** Φ_V is computed per stratum on **complete cases** (any-ERROR rows dropped): dose **n = 280**, negation **n = 295**, lateral **n = 341**, diagnosis **n = 333** (automated pass; on the v2 diagnosis stratum the Llama + Qwen + Nemotron panel has n = 240, with no incomplete rows). Every Δ and its 95% CI comes from a **paired item bootstrap** — 1000 resamples **over items, not raters**, seed = 42 — because the inference target is "another draw of benchmark items judged by this same panel," so items are the resampling unit.
### A5. Results I — judge calibration vs ground truth

**Ground-truth accuracy on MedSimp-JudgeBench (n=708; 200 clean controls, 508 corrupted):**

| Metric vs ground truth | Nemotron Nano | Llama-3.3-70B | Qwen3-32B |
|--|--|--|--|
| Recall on corrupted (catches injected error) | **84.2%** | 31.7% | 55.9% |
| False-positive on clean (over-flagging) | 35.2% | 1.5% | 0.5% |
| Specificity (clean) | 64.8% | 98.5% | 99.5% |
| **Balanced accuracy** | 74.5% | 65.1% | **77.7%** |

**Recall by injected error type** (diagnosis row: v2 hand-verified stratum, 120 τ=1 drops, deployed gate prompt; under the calibration prompt the same drops give 93% / 95% / 61%, [`results/judgebench_v2_panel_calib.json`](results/judgebench_v2_panel_calib.json). Dose / lateral / negation: automated calibration pass, 95 / 150 / 113 corrupted items with each judge's ERROR verdicts left out; Nano was judged under the calibration prompt and Llama's and Qwen's verdicts are stored from Project v1, [`nemotron_calibration_full.json`](nemotron_calibration_full.json). The rows differ in prompt and labels, so do not compare down a column. The automated rows also mix prompts within a row: Llama's and Qwen's stored verdicts come from Project v1's one-word prompt (threat 9), and the prompt moves recall a lot; under the deployed gate prompt, for example, Llama flags 84% / 81% / 65% of the dose, lateral and negation items, [`results/gate_calibration_full.json`](results/gate_calibration_full.json); Llama's stored column also repeats its clean-control verdict on 115 corrupted rows, which lowers its dose, lateral and negation recall here — 79.5% / 53.0% / 37.3% on the rows the repeat cannot touch (threat 9)):

| Error type | Nemotron | Llama | Qwen |
|--|--|--|--|
| diagnosis (silent drop) | **92%** | 47% | 47% |
| dose (10×) | 92% | 44% | 86% |
| lateral (side swap) | 97% | 43% | 85% |
| negation (flip) | 82% | 30% | 55% |

> **Diagnosis row = v2 hand-verified stratum (see A6).** The automated 708-item pool (before hand-verification) gave diagnosis recall 68 / 14 / 7 (Nemotron / Llama / Qwen); those labels were found ~85% mislabeled and are superseded — retained here as disclosed history only.

**Premise test (pre-registered).** Before any judge ran on the v2 drops, the protocol ([`docs/judgebench_v2_protocol.md`](docs/judgebench_v2_protocol.md) §8) set three bands for recall on the genuine drops: *incumbent blind spot confirmed* if Llama and Qwen each catch fewer than 30%, *no blind spot* if either catches at least 50%, and a *material Nemotron advantage* if Nano's recall exceeds the better incumbent's by at least 15 points with a CI excluding 0. The v2 panel ran under two prompts: the deployed gate prompt, and the calibration prompt — the CoT prompt in [`scripts/run_panel_judgebench_v2.py`](scripts/run_panel_judgebench_v2.py) (`COT_SYSTEM`, `COT_PROMPT`), sent with `enable_thinking` on ([`results/judgebench_v2_panel_calib.json`](results/judgebench_v2_panel_calib.json)). Recall on the 120 drops, with Wilson 95% CIs:

| Prompt | Llama | Qwen | Nano | Incumbent band | Nano − better incumbent (bootstrap 95% CI) |
|--|--|--|--|--|--|
| deployed gate | 56/120, 46.7% [38.0, 55.6] | 56/120, 46.7% [38.0, 55.6] | 110/120, 91.7% [85.3, 95.4] | neither | +45.0 points [+34.2, +50.0]; met: material |
| calibration | 114/120, 95.0% [89.5, 97.7] | 73/120, 60.8% [51.9, 69.1] | 112/120, 93.3% [87.4, 96.6] | no blind spot | −1.7 points [−6.7, +3.3]; not met |

Under the deployed prompt the CIs exclude the blind-spot band; *no blind spot* is not reached but not excluded, and the protocol names no outcome between the two. The two incumbents pass the same 41 drops as SAFE, against 34.1 expected if their misses were independent (one-sided Fisher p 0.0096), and Nano flags 33 of the 41. Under the calibration prompt Qwen by itself meets *no blind spot* (its CI lies above 50%), so that outcome does not rest on Llama, which flags 98 of the 120 paired controls; the incumbents share 3 misses.

False positives (controls flagged UNSAFE, Wilson 95% CIs):

| Controls | Prompt | Llama | Qwen | Nano |
|--|--|--|--|--|
| 120 paired controls (v2 run) | deployed gate | 32, 26.7% [19.6, 35.2] | 13, 10.8% [6.4, 17.7] | 53, 44.2% [35.6, 53.1] |
| 120 paired controls (v2 run) | calibration | 98, 81.7% [73.8, 87.6] | 30, 25.0% [18.1, 33.4] | 52, 43.3% [34.8, 52.3] |
| the protocol's 200 clean controls (708-item run) | deployed gate | 19, 9.5% [6.2, 14.4] | 19, 9.5% [6.2, 14.4] | 61, 30.5% [24.5, 37.2] |

The protocol names the 200 calibration clean controls for specificity; the v2 run judged the 120 paired controls instead, 28 of which are among the 200. All 200 have deployed-prompt verdicts from the earlier 708-item run ([`results/gate_calibration_full.json`](results/gate_calibration_full.json)); the other 172 have none from the v2 calibration-prompt run. The 708-item table at the top of this section comes from a different run: its Llama and Qwen columns are verdicts stored from a Project v1 run (`nemotron_judge_test.py` reads them from Project v1's `calibration_verdicts.json`), so its 1.5% and 0.5% false-positive rates, on these same 200 controls, are not comparable with any row of the table above (under the deployed prompt the two flag 19 of the 200 each).

The pre-registered expert-recoverability split goes in the predicted direction for both incumbents under both prompts: recall is lower on the 90 drops where the construction oracle (gpt-oss-120b) answered that an expert could still infer the diagnosis than on the 30 where it answered no (the protocol's strict tier, where the name was the only clue; deployed: Llama 45.6% vs 50.0%, Qwen 42.2% vs 60.0%; calibration: Llama 94.4% vs 96.7%, Qwen 57.8% vs 70.0%). Neither incumbent's gap is significant under either prompt: all four Newcombe 95% CIs include 0 (largest gap: Qwen, deployed, −17.8 points, CI −36.0 to +2.7), and the smallest one-sided Fisher p is 0.0696. Nano, which the prediction does not cover, shows a gap in the same direction under the deployed prompt (88.9% vs 100%; one-sided Fisher p 0.0493, Newcombe 95% CI −19.3 to +1.3) and none under the calibration prompt (93.3% on both). Within each stratum, scored with each drop's own paired control (50% drops, A8 threat 11), adding Nano gives ΔΦ_V +0.0695 [+0.0400, +0.0966] on the 90 and +0.1011 [+0.0530, +0.1423] on the 30 under the deployed prompt; under the calibration prompt, +0.0689 [+0.0453, +0.0946] on the 90, and on the 30 a lift that is not detectable, +0.0236 [−0.0145, +0.0651]. The bands, the Wilson interval on recall and the paired bootstrap for ΔΦ_V are the protocol's; the other intervals and tests (Wilson on false-positive rates, the bootstrap for Nano's advantage, Newcombe, Fisher) and the paired controls within strata were chosen, and all these figures computed, after the results were known ([`results/tau_recompute_v2_summary.json`](results/tau_recompute_v2_summary.json), [`scripts/build_tau_recompute_v2_summary.py`](scripts/build_tau_recompute_v2_summary.py)).

**Why not just consensus accuracy?** Because it can point the wrong way. The obvious baseline, when τ is known, is whether the panel's majority vote matches truth. Under that metric, adding Nemotron *lowers* balanced accuracy on the diagnosis stratum — **60.5% → 58.3%** ([`results/consensus_accuracy.json`](results/consensus_accuracy.json), deployed gate prompt, automated calibration pass) — because a majority vote lets the two blind incumbents outvote the one judge that catches the drop (the same reason the deployed rule is **not** a majority vote). The variance decomposition is threshold-free and points correctly on diagnosis: it *raises* Φ_V there (+0.0438 [+0.0264, +0.0595]; automated labels, A8 threat 1). On dose and lateral, where the incumbents already see, Φ_V's point estimates fall (−0.0279, −0.0173), but at these strata's own corrupted shares (32% and 43%) neither fall is detectable (95% CIs include zero), and their size and sign depend on the share: with every stratum reweighted to 30% both falls are detectable (dose −0.0324 [−0.0672, −0.000016], lateral −0.0410 [−0.0713, −0.0140]), and at 50% dose's point estimate is +0.0014 (A8 threat 12). At their own shares the decomposition detects the collateral over-flagging that majority-vote accuracy instead rewards as a rise in shared bias σ²_B on both (+0.0166 [+0.0023, +0.0318], +0.0204 [+0.0107, +0.0294]). (The figures in this paragraph are from the automated calibration pass; the clean hand-verified diagnosis ΔΦ_V is **+0.0765 [+0.0516, +0.0992]** — see A6.) Consensus accuracy tells you whether one fixed voting rule got lucky on the panel you have; Φ_V tells you whether the consensus is *systematically* closer to truth — the quantity judge-selection needs. (The balanced-accuracy comparison also shifts the vote threshold as the panel grows — "either of two" vs "two of three" — so σ²_B, being threshold-free, is the clean signal.)

**Verdict distribution (n=708):** Nemotron 208 SAFE / 491 UNSAFE / 9 ERROR. Inter-judge agreement: Nemotron↔Llama 47.6% (κ=0.139), Nemotron↔Qwen 68.7% (κ=0.421) — from [`nemotron_calibration_full.json`](nemotron_calibration_full.json) (`agreement.kappa_llama` / `agreement.kappa_qwen`).

> **Interpretation:** Nemotron Nano is a **high-sensitivity, low-specificity** judge. It catches errors the incumbents miss — dramatically so on diagnosis drops — but over-flags ~1 in 3 clean references (automated calibration pass, n=200 controls). On *balanced* accuracy Qwen still edges ahead (77.7%) on near-perfect specificity. Nemotron is not a drop-in calibrated judge as-is; its recall edge and its over-flagging are two sides of one low threshold, and it needs threshold/prompt calibration to separate them.
> **Carried from v1:** on the free-text safety set, CoT *amplified* judge disagreement (κ 0.11 → 0.04) — see the v1 README.

> **Confidence intervals:** for the v2 diagnosis stratum, per-judge recall and false-positive rates with Wilson 95% CIs, under both prompts, are in the premise test above and in [`results/tau_recompute_v2_summary.json`](results/tau_recompute_v2_summary.json) (`premise_test`), with the deployed-prompt false-positive rates on the protocol's 200 clean controls. The 708-item figures in the first two tables of this section (automated labels) are still given without CIs; Llama/Qwen ERROR counts and confusion matrices for them belong in an appendix.
### A6. Results II — the decoupling

**Adding Nemotron as a third rater** (R: 2 → 3; diagnosis row: v2 hand-verified stratum n=240, deployed gate prompt; dose/negation/lateral: automated calibration pass, Nemotron under the calibration prompt and Llama's and Qwen's verdicts stored from Project v1's calibration run (A8 threat 9); the rows differ in prompt, labels and corrupted share — dose 0.30, negation 0.34, lateral 0.43, diagnosis 0.50 — and Φ_V depends on the share, so read the paired ΔΦ_V within a row rather than comparing sizes down a column), per injected error type (1000-item bootstrap, seed=42; ΔΦ_V shows the **paired** Δ with 95% CI — see note):

| Feature | Φ_V (Llama+Qwen) | Φ_V (+Nemotron) | ΔΦ_V (paired, 95% CI) |
|--|--|--|--|
| dose | 0.743 | 0.733 | −0.013 [−0.055, +0.021] † |
| negation | 0.578 | 0.618 | +0.043 [+0.011, +0.070] |
| lateral | 0.697 | 0.745 | +0.048 [+0.019, +0.074] |
| **diagnosis** | **0.4764** | **0.5529** | **+0.0765 [+0.0516, +0.0992]** ‡ |

> ‡ **Automated-calibration-pass (superseded):** the earlier measurement on the 708-item automated pool gave diagnosis ΔΦ_V +0.071 [+0.055,+0.087] (Φ_V 0.404→0.476, n=333, 41% corrupted; +0.0762 [+0.0615, +0.0914] with the share reweighted to 50%, A8 threat 12). That pool was found to be ~85% mislabeled on diagnosis; the figure above is from the v2 hand-verified stratum (120 τ=1 + 120 paired τ=0, seed=42, n_boot=1000). See [`results/judgebench_v2_phi_v_recompute.json`](results/judgebench_v2_phi_v_recompute.json).

> **On the Δ values:** ΔΦ_V is a **paired** bootstrap Δ — 3-rater − 2-rater on the *same* complete-case items (1000 resamples, seed=42) — with 95% CI; the valid way to put an interval on a difference. **† dose** ΔΦ_V's CI straddles zero → the lone apparent loss is **not statistically significant**; the three gains (diagnosis, lateral, negation) all have ΔΦ_V CIs strictly above zero.

**The decoupling in point estimates (diagnosis) — the signature VAGT predicts.** When two judges share a blind spot, a third that breaks it *must* disagree with them on the items they miss — so inter-rater agreement can fall as veridicality rises. On diagnosis the point estimates move that way (Fleiss κ 0.214 → 0.179), but the change in agreement is not detectable (last caveat below). Under the deployed prompt Llama and Qwen each flag 56 of the 120 silently dropped diagnoses (46.7%, Wilson 95% CI 38.0–55.6%) and both pass the same 41; adding Nemotron (recall 91.7%, n=120 τ=1) raises Φ_V (0.4764 → 0.5529). By construction the judge that catches the drop must disagree with the two that miss it, so agreement-based metrics give the fix no credit even as the panel moves *closer to truth* — agreement statistics reward the blind spot; only a truth-anchored measure sees the fix.

**Φ_V = 0.5529 now exceeds 0.5** — the panel is *weakly dependable* on diagnosis under the hand-verified criterion at this stratum's 50% drop share (reweighted, the same verdicts' point estimate reaches 0.5 only between 23% and 67% drops, and Llama + Qwen alone also reach it, at most 0.5016, between 31% and 37%; [`results/judgebench_v2_prevalence_sensitivity.json`](results/judgebench_v2_prevalence_sensitivity.json), A8 threat 11); the third judge narrows the blind spot without fully closing it.

Full variance decomposition (σ²_B / σ²_R / σ²_N) and robust agreement metrics (Fleiss κ, Krippendorff α) for the automated calibration pass are in [`vagt_nemotron_results.txt`](vagt_nemotron_results.txt) (levels) and [`vagt_bootstrap_cis.json`](vagt_bootstrap_cis.json) (paired changes).

> **Caveats:**
> - **Least benefit on dose.** On `dose` ΔΦ_V = −0.013 [−0.055, +0.021] at dose's own 30% corrupted share (a slight dip, not detectable): Llama+Qwen weren't badly blind there, so Nemotron gives no detectable cut in shared bias (Δσ²_B +0.0005 [−0.012, +0.011]) while widening the spread between raters. The sign depends on the share — with every stratum reweighted to 50%, dose's ΔΦ_V is +0.0432 [+0.0074, +0.0729] — but of dose, negation and lateral, dose has the smallest point estimate at every common share up to 72% (its CI overlaps both others' at the own shares, at 30% and at 50%; A8 threat 12). The panel benefits where the incumbents share a blind spot.
> - Adding a diverging rater **raises σ²_R**, the spread between raters — the cost side Φ_V nets against the bias gain. σ²_N does not enter Φ_V (see A4). (σ²_R / σ²_N levels for the automated calibration pass are in [`vagt_nemotron_results.txt`](vagt_nemotron_results.txt).)
> - **Complete-case:** rows where any judge returned ERROR are dropped (9–18 per feature). Counts reported in [`vagt_nemotron_results.txt`](vagt_nemotron_results.txt).
> - **Fleiss κ / Krippendorff α on the v2 clean stratum** (n=240, seed=42, n_boot=1000; [`results/judgebench_v2_agreement_recompute.json`](results/judgebench_v2_agreement_recompute.json)): incumbent κ = 0.214 → 3-rater κ = 0.179 (ΔFleiss κ = −0.0356 [−0.1310, +0.0565]). The point estimate falls as Φ_V rises (+0.0765) and stays above zero, but the change is **not detectable** on clean labels. On the automated calibration pass the 3-rater κ did go negative (−0.088 [−0.143, −0.025]; paired change from Llama+Qwen −0.163 [−0.305, −0.045]; [`vagt_nemotron_results.txt`](vagt_nemotron_results.txt)), on different items (333 complete cases from the 150 automated diagnosis items and the 200 clean controls) with different verdicts ([`nemotron_calibration_full.json`](nemotron_calibration_full.json): Nemotron's under the calibration prompt, Llama's and Qwen's stored from Project v1's calibration run, A8 threat 9). κ is computed from the verdicts alone, so relabelling those 333 items with the hand audit leaves it at −0.088: the label correction does not account for the difference from the v2 stratum.
### A7. Results III — Nemotron Super as teacher

**Question:** Can Nemotron Super replace Claude Opus 4.5 as the reference-simplification teacher, using the *same* prompt?

**Method.** The teacher prompt is identical to the one used to generate the Claude Opus 4.5 reference simplifications in v1 ([github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius)) — a single user message with 9 simplification guidelines, no system prompt. Using the exact same prompt for both teachers ensures a fair comparison: any difference in output quality reflects the model, not the instructions. Only three things change from the Opus run:

| Parameter | Opus (v1) | Nemotron Super (v2) |
|--|--|--|
| Model | `claude-opus-4-5-20251101` | `nvidia/nemotron-3-super-120b-a12b` |
| `temperature` | API default | **0** (pinned for reproducibility) |
| `max_tokens` | 1024 | **16000** (see reasoning-model note) |

> **⚠️ Reasoning-model note:** Nemotron Super *thinks* before answering and emits the simplification only after. At `max_tokens=1024` (Opus's value) it spends the entire budget reasoning and returns `content=None` / `finish_reason="length"` — an empty output. At 8000 it still truncates the longest notes mid-sentence. **16000 is required.** Neither `enable_thinking:false` nor a "detailed thinking off" directive disables reasoning on Nemotron-3 — token budget is the only lever. The generator treats both `content=None` and `finish_reason="length"` as errors and retries, never saving a truncated reference.

**Status.**
- **JudgeBench references (708):** complete — 519 unique calls fanned out to 708 records, **0 errors**, avg 1,743 chars, ~21 min. ([`nemotron_references.json`](nemotron_references.json))
- **Full training references (9,999):** complete — **9,976 valid, 23 errored** (the 23 errored records were **dropped, not imputed**). Emits `{split, index, input, claude_output, nemotron_output, error}` per record so Claude and Nemotron outputs are directly comparable. Resume-capable (skips completed inputs). Published as [`chambul/medisimplifier-nemotron-dataset`](https://huggingface.co/datasets/chambul/medisimplifier-nemotron-dataset).

**Qualitative example** (train/0):

| | Original | Claude Opus | Nemotron Super |
|--|--|--|--|
| Diagnosis | Retinal detachment repair | Surgery to fix a detached retina (…back of the eye) | Surgery to fix a detached retina |
| History | Congenital glaucoma | Glaucoma present since birth (…damages the eye nerve) | Glaucoma present from birth |
| Procedure | pars plana vitrectomy (PPV) | small tools through the white of the eye | eye surgery to remove gel and fix a detached retina |

**Preserved:** section structure, all measurements (20/100, 4 mmHg, 20/70). **Note:** Nemotron removed the blank lines between sections (the prompt asks for no empty lines) — closer to the guideline than the Claude reference.

> **Caveat:** Nemotron occasionally adds a soft clause not in the source ("…improved to 20/70, *allowing better daily function*"). Not a medical-fact hallucination, but a mild elaboration that bends the "do not add information" guideline. Frequency across the full set is **unquantified — counting occurrences across all 9,976 refs is deferred to future work**. ROUGE-L of Nemotron references vs the Claude references: **0.525** (mean over 9,976 pairs; median 0.524, see [`teacher_comparison.json`](teacher_comparison.json)).

The Nemotron-taught student was evaluated on the **same GuyDor007 test set (n=1,001, Claude references)** as v1 — an apples-to-apples yardstick. Full metrics in [`results/eval_v2_results.json`](results/eval_v2_results.json).

| Metric | v1 (Claude teacher) | v2 (Nemotron teacher) |
|--|--|--|
| ROUGE-L | 0.6638 | **0.5254** |
| SARI | 73.49 | **60.36** |
| BERTScore | 0.9460 | **0.9113** |
| FK-Grade | 7.33 | **8.87** |

**Same v2 student, scored against each teacher's references** — measured against the Nemotron references it was actually trained on, every similarity metric is higher ([`results/eval_v2_nemotron_results.json`](results/eval_v2_nemotron_results.json)):

| Metric | vs Claude refs (n=1,001) | vs Nemotron refs (n=998) | Δ |
|--|--|--|--|
| ROUGE-L | 0.5254 | **0.6010** | **+0.076** |
| BERTScore | 0.9113 | **0.9321** | **+0.021** |
| SARI | 60.36 | **64.18** | **+3.82** |
| FK-Grade | 8.87 | 8.87 | ~0 |

> FK-Grade is prediction-only (reference-independent); Δ~0 confirms library consistency.

> **Output cap.** The v2 student's scores in both tables come from outputs generated with a 512-token cap (`max_new_tokens=512`); in the saved outputs, 146 of the 1,001 stopped at that cap ([`results/eval_v2_output_truncation.json`](results/eval_v2_output_truncation.json)). The live endpoint's default is 1,024 (B3).

**Training run:** LoRA (r=32, all_attn, 3 epochs) on 7,983 train / 995 val / 998 test — ~2.4 hours (8,523 s) on 1×H100, ~$9 for training alone (combined train+eval+merge GPU cost: $45.53 — see cost table). Teacher references agree with Claude's at ROUGE-L **0.525** ([`teacher_comparison.json`](teacher_comparison.json)).

> **Interpretation:** v2 ROUGE-L reflects **style divergence from Claude references, not a quality failure** — Nemotron Super produces *less* simplified references — measured FK-Grade **10.1** (Nemotron refs) vs **7.2** (Claude refs), Δ **+2.9** grade levels, both on textstat 0.7.13 over 9,976 pairs (see [`results/reference_fk_grade.json`](results/reference_fk_grade.json)) — and the student model faithfully learned this style. (The student's published FK-Grade 8.87 is a separate measurement — student output, scored with the train-v32 image's textstat — so it is not directly comparable to these reference figures.) The lower ROUGE-L/SARI is the student matching a *different teacher's style*, scored against Claude's references; it is not evidence the v2 outputs are worse, only that they are less Claude-like (and at a slightly higher reading level). Note the ~0.525 student↔Claude ROUGE-L closely tracks the ~0.525 teacher↔teacher ROUGE-L — the student inherited exactly the teacher gap.

> **Evaluation:** 1,001 test samples (GuyDor007/medisimplifier-dataset), greedy decoding, seed=42.
### A8. Threats to validity

Research-side threats to the VAGT and calibration findings. Product and operational caveats (the Qwen judge swap, DISAGREE as defense-in-depth) live in B8.

1. **Automated diagnosis labels ~85% mislabeled (disclosed and mitigated).** The 708-item automated calibration pool used programmatic perturbation to inject diagnosis drops, but hand-verification found ~85% of the automated "diagnosis positive" labels were incorrect — the perturbation deleted a cue sentence while the diagnosis name, abbreviation, or lay paraphrase remained elsewhere, so the τ=1 (patient-invisible silent drop) criterion was not met. All automated-pass diagnosis recall (68 / 14 / 7), Φ_V, and σ²_B figures are therefore computed on contaminated labels and are superseded. Mitigation: the v2 hand-verified stratum (n=120 τ=1 + 120 paired τ=0 controls) was built by manual audit; the authoritative ΔΦ_V is **+0.0765 [+0.0516, +0.0992]** at the stratum's 50% share (threat 11) — the same direction as the automated +0.071, whose magnitude is not evidence: its labels are wrong, and reweighting it from that set's 41% corrupted share to 50% (+0.0762) equalises the share only (threat 12; see A6). The automated figures are retained as disclosed history only.

2. **Reasoning vs. non-reasoning judges.** The v2 panel ran both reasoning judges at `max_tokens=8000` (A3), but Nemotron Nano and Qwen3-32B reason internally while Llama does not — so Nemotron's edge could partly reflect *reasoning capability* rather than clinical judgment. A control (Llama with visible CoT) is left as future work (see A3).

3. **Scale/family confound.** The panel mixes a 70B same-family judge (Llama-3.3-70B) with a 32B cross-family judge (Qwen3-32B) and a 30B reasoning judge (Nemotron Nano); a same-scale cross-family control (a 72B-class Qwen) was not available on Token Factory. Effects attributed to *family diversity* may therefore be partly scale effects — direction of bias unclear.

4. **Synthetic perturbations vs. real failures.** MedSimp-JudgeBench errors are programmatically injected (diagnosis drop, dose 10×, lateral swap, negation), not failures produced by a real simplifier. Recall and Φ_V measured on clean, isolated injections may not transfer to the subtler, correlated errors a deployed model makes — an external-validity limit (see B4).

5. **LLM-generated references, no expert anchor.** The reference simplifications (Claude and Nemotron teacher outputs) are LLM-generated and never clinician-reviewed; there is no human-expert gold standard for "a good simplification." Every similarity metric (ROUGE-L, SARI) and the teacher-quality comparison measures closeness to a model's style, not to expert-validated quality — "faithful" means faithful to a model. Note: the ground-truth labels τ_i (corrupted/clean) are known by construction for dose, lateral, and negation perturbations — a methodological strength; the diagnosis stratum's automated labels proved unreliable on hand-audit (~85% mislabeled, see threat #1), which is why they were rebuilt as the v2 hand-verified stratum; this reference-quality limit applies to the student evaluation metrics, not to the calibration ground truth.

6. **Complete-case deletion.** Items where any judge returned ERROR are dropped (9–18 per feature), not imputed. If ERRORs concentrate on harder items, dropping them biases Φ_V and recall optimistically (see A6).

7. **Single-seed bootstrap; power pre-registered for one test only.** All ΔΦ_V and Δκ confidence intervals come from a single-seed paired bootstrap — 1000 resamples at seed=42, over items (over patient pairs in the scoped-gate re-run); the premise-test intervals in A5 are Wilson and Newcombe. The JudgeBench v2 protocol pre-registered a sample-size target (≥ 100 genuine drops; 120 were built), not a power calculation ([`docs/judgebench_v2_protocol.md`](docs/judgebench_v2_protocol.md) §1). The scoped-gate re-run pre-registered a power calculation for its recall difference d_R only ([`docs/vagt_loop_v2_preregistration.md`](docs/vagt_loop_v2_preregistration.md) §9); its deviations log adds that its primary test (d_J ≥ +0.10 with CI lower bound > 0) was underpowered — the standard error of d_J is about 0.051, so a true +0.10 improvement would have passed only about half the time ([`results/vagt_loop_v2_deviations.md`](results/vagt_loop_v2_deviations.md)). Neither document has a power calculation for ΔΦ_V. Intervals capture sampling variability of these items only; borderline results (e.g. lateral's ΔFleiss CI straddling zero) are not backed by a powered test.

8. **Same-family judge.** Llama-3.3-70B shares a model family with the OpenBioLLM-8B student (both Llama-3-based). A same-family judge may share the student's blind spots, inflating the panel's apparent agreement with the student and overstating judge independence.

9. **Calibration prompt ≠ gate prompt.** VAGT calibration used the 4-step CoT judge prompt developed and run in v1 (`safety_eval_v2.py`, Llama+Qwen dual-judge, Cohen's κ), reused verbatim for v2's VAGT calibration — VAGT (the 3-rater Φ_V decomposition) is new in v2. In the automated pass's calibration file (`nemotron_calibration_full.json`) only Nemotron ran under that prompt: Llama's and Qwen's columns are Project v1's stored verdicts (`nemotron_judge_test.py`:13), from a Project v1 run that used a one-word prompt ([Project v1 repo, `perturbation_calibration.py`:193–227 at `dd6681b`](https://github.com/deepset01-sys/medisimplifier-nebius/blob/dd6681bed29199f7ed2f1eb10af3ad2c99b734d3/perturbation_calibration.py#L193-L227)), so the automated-pass figures pair judges under different prompts ([`docs/judgebench_v2_protocol_erratum.md`](docs/judgebench_v2_protocol_erratum.md)). Llama's stored column also repeats its clean-control verdict: on all 115 corrupted rows that share an item index with a clean control, its stored verdict equals its verdict on that control (Qwen's on 49, Nemotron's on 47; re-run under the deployed prompt, Llama's on 56), and 78 of those rows are dose, lateral or negation items (20, 34 and 24; [`results/tau_recompute_v1_matched.json`](results/tau_recompute_v1_matched.json) `idx_repeat_check`, `idx_repeat_by_error_type`). The copied verdict is SAFE on 112 of the 115, so the repeat lowers Llama's automated-pass recall: on the rows whose item index appears only once in the file, which the repeat cannot touch, Llama catches 79.5% of dose items (44.2% on all rows), 53.0% of lateral (42.7%) and 37.3% of negation (30.1%), while Qwen, Nemotron and Llama re-run under the deployed prompt show no comparable rise on those rows. Those rows are fewer (39, 83 and 59), and their Llama verdicts still come from Project v1's one-word prompt. The effect on the Φ_V, σ²_B and κ figures built on Llama's column is not measured. On the v2 stratum all three judges ran under each prompt. The deployed gate uses `safety_gate.py`'s prompt, and verdicts do not transfer item-for-item (idx 21). The reported calibration recall, Φ_V, and DISAGREE rates are therefore indicative of the calibration prompt for Nemotron and, in the automated pass, of Project v1's one-word prompt for Llama and Qwen; the gate's live operating point is measured separately (see B5). Split-half check: splitting the v2 hand-verified stratum 60/60 by patient (n=120 τ=1; [`results/judgebench_v2_split_half.json`](results/judgebench_v2_split_half.json), [`scripts/run_split_half_v2.py`](scripts/run_split_half_v2.py)) gives POSITIVE on both halves under the deployed gate prompt (ΔΦ_V **+0.0735** and **+0.0789**), consistent with the full-stratum **+0.0765 [+0.0516, +0.0992]** — the effect replicates across two patient-disjoint halves (nothing is fitted on either half, so this is not an out-of-sample test). The automated-pass split-half (ΔΦ_V **+0.052 [+0.030, +0.075]**, [`results/split_half_validation.json`](results/split_half_validation.json)) is not evidence either way: nothing was fitted on its development half, and its diagnosis labels are the automated ones — retained as disclosed history.

10. **Construction circularity in the pool ranking (v2).** The v2 diagnosis stratum was built with two models that are also pool candidates: **DeepSeek-V4-Pro** was the *editor* (it rewrote each summary to remove the diagnosis) and **gpt-oss-120b** was the *oracle* (it selected the diagnosis targets and answered the τ=1 acceptance gates — name absent, not lay-recoverable, nothing added — before human review; `scripts/build_judgebench_v2.py`). The pre-registered independence guarantee covers the **panel judges only** — Llama-3.3-70B, Qwen3-32B and Nemotron Nano were neither editor nor oracle (`docs/judgebench_v2_protocol.md`) — so Nano's ΔΦ_V +0.0765 is free of this effect. The pool ranking is not: every τ=1 item passed gpt-oss's own judgement that the diagnosis was gone, so gpt-oss's lead (+0.1220) and DeepSeek-V4-Flash's (+0.1238; same family as the editor) are partly by construction, by an unmeasured amount. Measuring it requires items built with a different oracle and editor, or labelled by humans alone.

11. **Prevalence (v2).** The v2 diagnosis stratum is 50% drops by design (120 drops, 120 paired controls), and Φ_V depends on that share: its signal term σ²_τ = p(1−p) peaks at 50%, and a judge's catches count in proportion to the drop share, its false alarms in proportion to the rest. Unless stated otherwise, every Φ_V, ΔΦ_V and band on the v2 hand-verified stratum in this README is at that 50% share (figures on DeepSeek-V4-Flash's 233 completed rows — its +0.1238 and the same-row comparisons with it — are at 51%). Reweighted to other shares (a post hoc analysis, not in the pre-registered protocol; [`results/judgebench_v2_prevalence_sensitivity.json`](results/judgebench_v2_prevalence_sensitivity.json), [`scripts/run_prevalence_sensitivity_v2.py`](scripts/run_prevalence_sensitivity_v2.py)), the same deployed-prompt verdicts give Nano a ΔΦ_V of **+0.0765** at 50%, **+0.0421** at 33% and **+0.0066 [−0.0264, +0.0384]** at 20%: its CI stays above zero only from about 29% drops up, its point estimate is below zero at 17% and below, and its CI lies wholly below zero only at about 7% and below. Nano flags 53 of the 120 clean controls (Llama 32, Qwen 13), so adding it raises the panel's bias on clean text (control-side mean b² 0.110 → 0.148; DeepSeek-V4-Flash, which also flags more controls than either incumbent, adds only 0.110 → 0.118), and that bias weighs more as drops get rarer: on bias alone the break-even is about 16% drops, and Nano's added rater spread (σ²_R) moves the zero crossing to about 18%. Under the calibration prompt, where Llama flags 98 controls, adding Nano lowers that bias and its ΔΦ_V stays above zero at all five shares tested (+0.0402 [+0.0215, +0.0615] at 20%, +0.0165 [+0.0078, +0.0281] at 5%) — a lift over weaker incumbents: that panel's Φ_V is below the deployed panel's at every share tested (0.3468 vs 0.4802 at 20%). gpt-oss-120b's point estimate stays positive at every share from 1% to 99% (**+0.0736 [+0.0414, +0.1030]** at 20%), but its CI excludes zero only from about 8% drops up — at 5% it is +0.0229 [−0.0085, +0.0551], which includes zero — and it is the selector's pick at every share from 2% to 51% (threat 10 still applies to its level). Above 51% the pick alternates: DeepSeek-V4-Flash at 52%, 60–62% and 69–96%, gpt-oss at the other shares, although DeepSeek's point estimate is the higher one at every share from 50% up. The selector ties two candidates only when their ΔΦ_V round to the same 0.01 bin (`TIE_BAND` in `src/audit_panel/selector.py`), so the pick follows the bin edges, not the size of the gap: where the two share a bin, the fewest-ERROR tie-break picks gpt-oss; where DeepSeek's rounds one bin higher, DeepSeek is picked ([`results/judgebench_v2_prevalence_sensitivity.json`](results/judgebench_v2_prevalence_sensitivity.json) `ranking.selector_pick_runs`, `ranking.top_by_delta_runs`). Recall, specificity and the false-positive rate do not depend on prevalence; Φ_V, ΔΦ_V and the share of flags that are real do (strict mode: 65.5% of flags are real drops at 50%, 32.2% at 20%; the DISAGREE branch alone: 45.5% of its flags are false alarms at 50%, 76.9% at 20%). The null-rater control's permutation null is for the 50/50 composition only. The thresholds quoted here are read off a 1% grid and can move by a point with the bootstrap convention. The reweighting assumes drops and controls behave at other shares as they do here; threat 4 still applies. B5's audit of the served model's own outputs (20 flagged cases, LLM auditors, diagnosis or medication drops; not a census) is too small to pin its drop rate down; taken at face value (its flagged-case rates applied to every flagged output, none among unflagged ones) it would be roughly 5–18% of outputs, where Nano's reweighted ΔΦ_V under the deployed prompt is near zero or below.

12. **Prevalence (automated pass).** Each automated-pass stratum is its corrupted items plus the same 200 clean controls (195 in the calibration file once rows with an ERROR verdict are dropped; Llama's column there repeats its clean-control verdict on 115 corrupted rows, which lowers its recall, threat 9; how much that moves the ΔΦ_V and σ²_B figures here is not measured), so the four strata sit at different corrupted shares: dose 0.30, negation 0.34, lateral 0.43, diagnosis 0.41 in the calibration file ([`vagt_nemotron_results.txt`](vagt_nemotron_results.txt)). Φ_V depends on the share (threat 11), so a mean over strata, a ranking of strata or a sign near zero mixes shares. Reweighting the same verdicts so that every stratum sits at one common share (post hoc; [`results/judgebench_v1_prevalence_sensitivity.json`](results/judgebench_v1_prevalence_sensitivity.json), [`scripts/run_prevalence_sensitivity_v1.py`](scripts/run_prevalence_sensitivity_v1.py)) shows which of these depend on it; the 1–99% grid gives point estimates only. In the calibration file, diagnosis is the incumbents' blindest stratum at every common share from 1% to 99%, and adding Nano cuts shared bias σ²_B most there from 5% up (at 1–4% it raises σ²_B on every stratum, least on diagnosis). Diagnosis has the largest ΔΦ_V point estimate up to 53%, and of dose, negation and lateral, dose has the smallest up to 72%. Signs near zero depend on the share: Nano's dose ΔΦ_V is −0.0127 [−0.0552, +0.0208] at dose's own 30% but +0.0432 [+0.0074, +0.0729] with every stratum at 50%. Under the deployed gate prompt its dose and lateral changes, −0.0279 [−0.0625, +0.0042] and −0.0173 [−0.0428, +0.0062] at their own 32% and 43% (not detectable), are +0.0014 and −0.0060 at 50% (not detectable) and −0.0324 [−0.0672, −0.000016] and −0.0410 [−0.0713, −0.0140] at 30%, both CIs below zero (dose's only just). In the automated pass's null-rater baseline (constant-UNSAFE and random-47% raters; [`results/null_baseline_cis.json`](results/null_baseline_cis.json)), constant-UNSAFE's mean ΔΦ_V over the four strata (no CI is computed for the mean) is −0.0631 at the strata's own shares and +0.0066 with every stratum at 50%, where its dose and lateral changes are below zero and its diagnosis change above (dose −0.0430 [−0.0935, −0.0035], lateral −0.0381 [−0.0786, −0.0059], diagnosis +0.0747 [+0.0576, +0.0879]; negation +0.0327 [−0.0037, +0.0607], not detectable). Nano's mean is positive from 25% up, constant-UNSAFE's from 49% and random-47%'s from 69%, so of those three raters Nano is the only one with a positive mean from 25% to 48%; below 25% none of the three has one. In selector.py's ranking of the automated pool with the two null raters added, constant-UNSAFE is 6th of 8 at the strata's own shares with or without the collateral key, and neither null reaches the top tie (the candidates whose blind-spot ΔΦ_V rounds to the top candidate's 0.01 bin) at those shares, at 30% or at 50% (at 50% constant-UNSAFE's +0.0747 is 0.0051 below gpt-oss's +0.0798 but rounds to the 0.07 bin); Nano is recommended at all three. With every stratum at 51% or more, constant-UNSAFE is in the top tie: at 51–54% it ranks 5th with the collateral key and 3rd without it, and from 55% to 99% the selector recommends it (without the key, from 55% to 98%). The null control therefore does not validate the collateral key. The automated diagnosis ΔΦ_V, +0.0706 at its 41%, is +0.0762 [+0.0615, +0.0914] reweighted to 50%, beside v2's +0.0765 (deployed prompt) and +0.0591 (calibration prompt) at 50%; the labels, items and prompt pairings differ (threat 1; the automated file pairs Nano under the calibration prompt with Llama and Qwen verdicts stored from Project v1), so this equalises the share only. The reweighting assumes corrupted and clean items behave at other shares as they do here.

### A9. Reproduce the analysis

**Environment:** Python 3.11+ (`docker/Dockerfile.cpu` uses `python:3.11-slim`) · `pip install -r requirements.txt` installs openai, numpy, requests, tqdm — enough for the safety gate and the judge/VAGT scripts. The endpoint and tests also need fastapi, pydantic, httpx, uvicorn and pytest; training, evaluation and data prep use the pinned [`docker/requirements_train.txt`](docker/requirements_train.txt) (torch, transformers, peft, datasets) inside the train image.
**Auth:** `export NEBIUS_API_KEY=<your-token-factory-key>`

```bash
git clone https://github.com/deepset01-sys/medisimplifier-nemotron-vagt.git
cd medisimplifier-nemotron-vagt
pip install -r requirements.txt

# 0. Confirm the Nemotron model strings are live on your account
python nemotron_judge_test.py --list-models

# 1. Nemotron Nano as a safety judge (smoke test, then full 708)
python nemotron_judge_test.py --n 20                       # smoke
python nemotron_judge_test.py --n 708 --workers 12 \
       --output nemotron_calibration_full.json             # full 3-judge set

# 2. VAGT 3-rater decomposition (reads the calibration file above)
python vagt_nemotron_analysis.py > vagt_nemotron_results.txt
python scripts/run_prevalence_sensitivity_v1.py   # offline → step 2's ΔΦ_V, the gate-prompt file and the null-rater control with every stratum at one common corrupted share (post hoc; A8 threat 12)

# 2b. Automated-pass diagnosis re-score with the 150 hand labels (offline, committed files only; post hoc)
python scripts/run_tau_recompute_v1.py                   # → results/tau_recompute_v1_matched.json; asserts every tau_recompute_summary.json cell

# 3. Nemotron Super teacher — JudgeBench references (519 unique -> 708 records)
python nemotron_teacher.py --list-models                   # verify Super string
python nemotron_teacher.py --limit 5 --max-tokens 16000    # smoke
python nemotron_teacher.py --workers 12 --max-tokens 16000 \
       --output nemotron_references.json

# 4. Nemotron Super teacher — full training set (9,999, resume-capable)
python nemotron_training_data.py --limit 5                 # smoke
python nemotron_training_data.py --workers 12              # full run (resumes on restart)

# 5. Clean-stratum pipeline (v2 hand-verified, 120 τ=1 + 120 τ=0)
#    Inputs (committed): results/judgebench_v2_tau1_final.json,
#                        results/judgebench_v2_clean_controls.json,
#                        results/judgebench_v2_panel_gate.json,
#                        results/judgebench_v2_panel_calib.json
python scripts/run_pool_judgebench_v2.py --analyze-only  # rebuild table from committed pool files → results/judgebench_v2_pool_table.json
python scripts/run_phi_v_recompute.py                    # → ΔΦ_V +0.0765 [+0.0516, +0.0992] (deployed_full)
python scripts/run_split_half_v2.py                      # → both halves POSITIVE (+0.0735, +0.0789)
python scripts/run_null_control_v2.py                    # → null-rater control (a re-run gives Super p 0.002; the committed file keeps 0.001, see its tie note)
python scripts/check_null_control_ties_v2.py             # → exact ties in that null (Super: 1 tie, p 0.002 counted)
python scripts/recount_disagree_708_hand_labels.py       # → 708-set DISAGREE false-alarm share with the 150 hand labels (70.1% / 74.1%, deployed prompt)
python scripts/run_prevalence_sensitivity_v2.py          # → ΔΦ_V reweighted to 50/33/20/10/5% drops and a 1–99% grid (post hoc; A8 threat 11)
python scripts/build_tau_recompute_v2_summary.py         # → results/tau_recompute_v2_summary.json: protocol §8 premise test and expert-recoverability split (reads the pool, Φ_V, split-half, null and prevalence outputs above)
python scripts/check_deepseek_budget_v2.py --selftest    # offline, committed files only: DeepSeek's committed row + the 128-fill bound on its 7 ERROR items
python scripts/check_deepseek_budget_v2.py --phases A    # live (NEBIUS_API_KEY + the same local raw-note inputs as run_pool): those 7 items at max_tokens 4000 vs 8000

# 6. Scoped-gate experiment on v2 (pre-registered, git-enforced); the offline commands need the same local raw-note inputs as run_pool
python scripts/run_vagt_loop_v2.py --selftest               # offline: reproduces the committed Nano ΔΦ_V +0.0765 [+0.0516, +0.0992]
python scripts/run_vagt_loop_v2.py --analyze-only           # rebuild results/vagt_loop_v2_summary.json from the calls file
git rev-parse d69f506:docs/vagt_loop_v2_preregistration.md  # must equal run_meta.prereg_blob in that summary
```

> **Git-enforced pre-registration (v2 scoped-gate re-run):** the design, thresholds and analysis were committed (`d69f506`) before any call. The runner refuses the full run unless the pre-registration note and the runner are committed and unmodified, and it records their git blob ids and HEAD in the results. Anyone can check `git rev-parse d69f506:docs/vagt_loop_v2_preregistration.md` against `run_meta.prereg_blob`.

> **Reasoning-model reminder:** all Nemotron generation uses `--max-tokens 16000` (Super) / `8000+` (Nano). Too small a budget returns empty output — the scripts flag and retry, never save a truncated result. Runs checkpoint every 50 records; `nemotron_training_data.py` resumes from the output file.

**Expected cost:** $1.63 calibration (708×3 judges), ~$1.7 JudgeBench refs (519 calls), $75.51 full teacher run (9,999 calls).

## Track B — Product Design

### B1. What you get & who it's for

**Two products, one safety layer.**

1. **Safe simplification** — send a discharge summary to `POST /v1/simplify`; receive a ~9th-grade
   rewrite (FK-Grade 8.87) plus the safety gate's verdict. Three judges return verdicts; **two decide**
   (Qwen3-32B + Nemotron Nano) and Llama-3.3-70B is advisory. Choose `safety_mode`: `flag` (warn),
   `block` (withhold UNSAFE/ERROR), or `strict` (also withhold DISAGREE). The gate also runs on its own
   (`evaluate_safety(original, simplified)`) to check any third-party simplifier's output.
2. **Judge-panel selection** — send a judge panel to `POST /v1/audit_panel`; receive which judge to add
   to fix the panel's blind spot, with its expected Φ_V gain and a bootstrap CI. On the hand-verified
   v2 diagnosis stratum, the Llama+Qwen panel's answer is **gpt-oss-120b, +0.1220 [+0.1000, +0.1416]**
   (statistically tied with DeepSeek-V4-Flash; chosen by a fewest-errors tie-break added after the v2 result was known; the lift is for the stratum's 50% drop share, A8 threat 11). Pure CPU over pre-computed verdicts.

**Intended users.** A developer wrapping or evaluating a medical text simplifier (product 1); anyone
choosing which LLM judges to trust for a safety check (product 2).

**How you can try it** (details in B2):

| Tier | What runs | Cost to try |
|--|--|--|
| Public demo | [Public demo](https://deepset01-sys.github.io/medisimplifier-nemotron-vagt/) + `/v1/audit_panel` on a CPU service (`audit-cpu-v2.1`), started for judging windows; while it is stopped the demo shows the committed v2 receipt | nothing — no account, no GPU |
| On-demand | `/v1/simplify` + gate on a Nebius GPU Endpoint (endpoint-v5) + dedicated judge endpoints | start the endpoints (B2 Tier 2, B7) |
| Library | `evaluate_safety` from `src/safety_gate.py` | a Nebius API key + the dedicated Qwen3-32B endpoint running (Llama's dedicated endpoint for its advisory verdict) |

**What it is *not*.**
- **Not clinician-validated** — a research prototype, not a medical device.
- **Not authenticated** — do not route real patient data through it.
- **Not scale-to-zero** — the GPU endpoint is a persistent Nebius GPU Endpoint, stopped between demos (not a serverless auto-waking service). The CPU `/v1/audit_panel` service is also started for judging windows and stopped between them.

**Pipeline 1 — training, deployment, and the first (automated) calibration.** Training/calibration: Token Factory (serverless, per-token). Deployed endpoint: persistent Nebius GPU Endpoint (see B7). The calibration and VAGT steps at the bottom are the **automated 708-item pass**; its diagnosis labels were later found ~85% wrong and are superseded by Pipeline 2 (A6, A8).

    Dataset (HuggingFace: GuyDor007/medisimplifier-dataset — 9,999 discharge summaries)
        |
        v
    Token Factory: Nemotron Super teacher  (nemotron_training_data.py)
        generate reference simplification per record  ->  nemotron_training_references.json
        |                                                  (claude_output + nemotron_output side by side)
        v
    Nebius Job: LoRA fine-tune student on Nemotron references (H100, r=32 all_attn, 3 epochs)  ->  adapter (bucket)
        |
        v
    Nebius Job: Evaluation (full metrics in A7)
        |
        v
    Nebius Job: Merge adapter → chambul/MediSimplifier-OpenBioLLM-v2-merged (HuggingFace)
        |
        v
    Token Factory: 3-judge safety evaluation  (nemotron_judge_test.py)   [automated 708-item pass]
        Llama-3.3-70B + Qwen3-32B + Nemotron Nano  ->  nemotron_calibration_full.json
        |
        v
    VAGT decomposition  (vagt_nemotron_analysis.py)                      [automated 708-item pass]
        {sigma_tau, sigma_B, sigma_R, sigma_N, Phi_V} + Fleiss/Krippendorff  ->  vagt_nemotron_results.txt
        |
        v
    Nebius Endpoint: Safe Simplification Endpoint v5
        POST /v1/simplify → vLLM + calibration-informed gate (2-judge rule + advisory Llama)
        (endpoint tested; redeploy via safe_endpoint_v2.yaml)

**Pipeline 2 — the hand-verified v2 benchmark and panel selection** (source of the current headline numbers):

    Hand audit of the 150 automated "dropped diagnosis" items  ->  results/tau_hand_labels_150.json
        (128 still contained the diagnosis)  ->  re-score: results/tau_recompute_summary.json
        (9 genuine drops: too few to show the sign; same share and one prompt: results/tau_recompute_v1_matched.json)
        |
        v
    Rebuild: 120 hand-verified primary-diagnosis drops + 120 paired controls  (build_judgebench_v2.py)
        ->  results/judgebench_v2_tau1_final.json + results/judgebench_v2_clean_controls.json
        |
        v
    Gate panel on the 240 items, deployed prompt  (run_panel_judgebench_v2.py)
        Llama + Qwen (Token Factory dedicated endpoints) + Nemotron Nano  ->  results/judgebench_v2_panel_gate.json
        |
        v
    6-candidate pool + VAGT  (run_pool_judgebench_v2.py, run_phi_v_recompute.py)
        ->  results/judgebench_v2_pool_table.json, results/judgebench_v2_phi_v_recompute.json
        checks: null control (run_null_control_v2.py) + split-half (run_split_half_v2.py)
        |
        v
    Serving pool  (build_audit_pool_v2.py  ->  audit_pool_v2/, self-verified vs the pool table)
        |
        v
    CPU service: /v1/audit_panel  (audit-cpu-v2.1, started for judging windows)  ->  public demo (GitHub Pages)
        live receipt: results/audit_panel_live_receipt_v2.json  (captured from audit-cpu-v2)

**Validation pipeline** (post-deployment measurement):

    Token Factory + Dedicated Endpoint: gate calibration (708 items, gate prompt)
        run_gate_calibration.py  ->  results/gate_calibration_full.json
        (DISAGREE 20.8%, Qwen FP 9.5% under gate prompt — see B5)
        |
        v
    Token Factory + Dedicated Endpoint: student self-audit (1,001 test outputs)
        run_student_audit.py  ->  results/student_audit.json
        (SAFE 47.4% / flagged 52.0%, plus 0.6% ERROR — see B5)
        |
        v
    External APIs: dual-auditor diagnosis-retention review (30-case sample, seed=42)
        llm_review_audit.py  ->  results/student_audit_review.json
        (Claude Sonnet 5 + Gemini 2.5 Pro; 2/20 confirmed diagnosis drops — see B5)

### B2. Quickstart

#### Tier 1 — Public demo (no setup)

**🔗 Live demo:** https://deepset01-sys.github.io/medisimplifier-nemotron-vagt/

**Two live interactive elements** (CPU, no GPU):
1. **"Run audit_panel live →"** — the deterministic VAGT recommendation for *our* gate panel (Llama + Qwen) on the 240-item hand-verified diagnosis stratum: **gpt-oss-120b, +0.122, CI [0.100, 0.142]** (at the stratum's 50% drop share, A8 threat 11) — statistically tied with DeepSeek-V4-Flash, chosen on reliability (0 errors vs 7) by a tie-break added after the v2 result was known. Same answer every call.
2. **"Try a different panel"** — pick any **2+ of the 8** pooled judges and VAGT recommends which judge to add for *your* panel (the recommendation changes with the panel).

No account, no GPU, nothing to install.

**Serves `/v1/audit_panel` only** — pure CPU over pre-computed verdicts. No GPU and no key (backed by the CPU service `chambul/medisimplifier:audit-cpu-v2.1`, serving `audit_pool_v2/`). The service is started for judging windows and stopped between them; while it is stopped, the live button reports it unavailable and the page shows the committed v2 receipt.

#### Tier 2 — Full pipeline (GPU, on-demand)

The full simplify-and-gate pipeline uses **three** Nebius endpoints — two used by the deployed endpoint-v5 image, plus a third used by the current gate code — all started from the Nebius Console (see [REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) for redeploy instructions). Qwen3-32B + Nemotron decide the verdict and Llama is advisory; Nemotron runs serverless and needs no endpoint:

1. **endpoint-v5** (H100, ~10–15 min cold start) — serves `POST /v1/simplify` (student rewrite). Its `POST /v1/audit_panel` still serves the **earlier automated pool** (the v5 image predates the v2 pool); for the current v2 answer use the Tier 1 service.
2. **qwen3-32b-judge** (dedicated endpoint) — supplies the Qwen verdict. Without it, `qwen_verdict = ERROR`, and the gate's decision rule (Qwen3-32B + Nemotron decide) cannot be applied.
3. **Llama-3.3-70B dedicated endpoint** (`dedicated/meta-llama/Llama-3.3-70B-Instruct-KrpmhZ`) — advisory only. The current gate code routes Llama here because serverless Llama returns 403 on this account; the endpoint-v5 image predates this change and still calls serverless Llama, so its Llama verdict will be `ERROR` (not verified live) — consensus is unaffected.

> **Live endpoint (Nebius GPU Endpoint — application-tunnel URL, stopped between demos):**
> https://port8000-vjbksde9vzhgtcx.tunnel.applications.eu-north1.nebius.cloud
> When running, a request returns in ~24–27s (3-judge gate latency — Nemotron serverless, Qwen on a Token Factory dedicated endpoint — not a serverless cold-start wake); retry once if no response in 60s. A stopped endpoint first loads vLLM (~10–15 min).

Two ways to call it: the hosted endpoint (**Path 1**), or the safety gate directly on any `(original, simplified)` pair (**Path 2**).

**Path 1 — `POST /v1/simplify`.** Live call to the hosted Safe Endpoint v5 (real response below):
```bash
curl -X POST https://port8000-vjbksde9vzhgtcx.tunnel.applications.eu-north1.nebius.cloud/v1/simplify \
  -H "Content-Type: application/json" \
  -d '{"text": "Patient presented with acute myocardial infarction. Prescribed metformin 1000mg BID. Diagnosis of type 2 diabetes mellitus confirmed.", "safety_mode": "flag"}'
```
Response (captured live from endpoint-v5, `sha256:0e40cff4…`, 2026-09-09; committed at [`results/endpoint_v5_smoke_test.json`](results/endpoint_v5_smoke_test.json) — `simplified_text` truncated here):
```json
{
  "simplified_text": "The patient came in with a heart attack. The patient was given metformin 1000mg twice a day. The patient was found to have type 2 diabetes, a condition where blood sugar is too high. … [truncated]",
  "blocked": false,
  "safety": {"llama_verdict": "SAFE", "qwen_verdict": "SAFE", "nemotron_verdict": "SAFE", "blocked": false, "consensus": "SAFE", "warning": null},
  "latency_ms": {"vllm_ms": 1121, "total_ms": 23845}
}
```
The full rewrite also repeats source sections ("Hospital Course", "Discharge Summary") and adds admission/discharge statements that are not in the input; the gate passes it because it checks for dropped content, not added content (B8 item 6).

**Path 2 — gate-only quickstart.** The gate scores any `(original, simplified)` pair directly, without the endpoint. Here it flags a simplification that drops a diagnosis (the UNSAFE path):
```python
from src.safety_gate import evaluate_safety   # requires NEBIUS_API_KEY + the Qwen3-32B dedicated endpoint running
original   = "Patient has acute MI, type 2 diabetes mellitus, and hypertension. HbA1c 9.2%."
simplified = "Patient had a heart attack and high blood pressure. Follow up in 2 weeks."  # diabetes + HbA1c dropped
print(evaluate_safety(original, simplified))
# → illustrative output (not a committed capture):
#   {'llama_verdict': 'UNSAFE', 'qwen_verdict': 'UNSAFE', 'nemotron_verdict': 'UNSAFE',
#    'blocked': False, 'consensus': 'UNSAFE', 'warning': None}
```
The expected result: all three judges catch the dropped diagnosis → consensus **UNSAFE**. (This drop is overt enough that all three flag it; the **DISAGREE** branch fires on subtler drops only Nemotron catches — see [the safety gate (B4)](#b4-the-safety-gate--how-a-verdict-is-produced).)

> This is the gate's second product use case — evaluating a third-party simplifier's output, not just MediSimplifier's own.

### B3. API contract

**`POST /v1/simplify`** — request body (JSON):

| Field | Type | Required | Default | Notes |
|--|--|--|--|--|
| `text` | string | yes | — | the medical text to simplify |
| `safety_mode` | string | no | `"flag"` | `"flag"`, `"block"`, or `"strict"` — see below |

Maximum input length and input language are **not formally constrained** in the current implementation.

**`safety_mode` values:**
- `"flag"` (default) — returns simplified text even if UNSAFE; adds `warning` field
- `"block"` — sets `blocked: true` and nulls `simplified_text` when consensus is UNSAFE or ERROR
- `"strict"` — blocks on UNSAFE, DISAGREE, or ERROR; the Nemotron diagnosis-drop tripwire (DISAGREE) enforces rather than warns. Trade-off: under the deployed gate prompt, **45.5% of DISAGREEs are false alarms** on the hand-verified v2 stratum (45 of 99). On the automated 708-item set 34.7% fire on clean text (51 of 147), and **70.1% are false alarms** if a DISAGREE on a diagnosis item whose diagnosis the hand audit found still present counts as one (74.1% if the borderline items count too; see B5). These shares depend on how common real errors are: 72% of the 708 items are corrupted (automated labels, all four error types; 51.8–53.7% carry a genuine error by the hand labels), and v2 is 50% drops. At a matched 50%, the 708 set's automated-label rates would give 57.4% (73.1–75.5% with the hand labels); at 20% drops, v2's give 76.9% ([`results/judgebench_v2_prevalence_sensitivity.json`](results/judgebench_v2_prevalence_sensitivity.json); A8 threat 11).

**Block mode does NOT block DISAGREE** — a DISAGREE verdict returns `blocked: false` with the `warning` field set; only **UNSAFE** and **ERROR** are blocked. A caller relying on `block` to suppress every non-SAFE output must handle DISAGREE explicitly: it is a defense-in-depth flag, not a hard block (see the B4 scope note). Use `strict` mode to block DISAGREE.

**Response contract:**
```json
{
  "simplified_text": "...",
  "blocked": false,
  "safety": {
    "llama_verdict": "SAFE|UNSAFE|ERROR",
    "qwen_verdict": "SAFE|UNSAFE|ERROR",
    "nemotron_verdict": "SAFE|UNSAFE|ERROR",
    "blocked": false,
    "consensus": "SAFE|UNSAFE|DISAGREE|ERROR",
    "warning": null
  },
  "latency_ms": {
    "vllm_ms": 428,
    "total_ms": 26975
  }
}
```

**`GET /health`** — readiness probe. Returns:
```json
{"vllm": true, "token_factory": true, "audit_panel": true, "ready": true}
```
On the CPU audit_panel service, `/health` also names the served pool:
```json
{"service": "audit_panel-cpu", "audit_panel": true, "pool_loaded": true, "benchmark": "MedSimp-JudgeBench-v2", "ready": true, "pool_error": null}
```

**Error semantics:**
- **`consensus: "ERROR"`** — a judge call failed or timed out — e.g. a stopped Token Factory dedicated endpoint (each judge bounds its HTTP call at 60 s with 3 retries, then returns `ERROR`).
- **Fail-safe:** an `ERROR` consensus blocks in `block` mode (same as UNSAFE).
- **`warning`** — set only on a DISAGREE verdict (`"diagnosis-drop risk"`); `null` for every other verdict.

#### `POST /v1/audit_panel`

Given an incumbent judge panel and a candidate pool, ranks the candidates and recommends the single judge to add that best raises truth-anchored dependability (Φ_V) on the panel's **blindest stratum** (the v2 pool has one stratum, diagnosis). Pure CPU over the committed pre-scored verdict pool — **no live judge calls**. The served pool is selected by `AUDIT_POOL_DIR` (unset → the earlier `audit_pool/`; the CPU image sets `audit_pool_v2`). Request body (JSON):

| Field | Type | Required | Default | Notes |
|--|--|--|--|--|
| `incumbent_panel` | string[] | yes | — | ≥2 pooled model ids (the current panel) |
| `candidate_pool` | string[] | yes | — | model ids to rank as the added rater; must be an explicit list. Unknown ids are returned in `unseen_candidates`, never ranked |
| `benchmark` | string | no | the served pool | `"MedSimp-JudgeBench-v2"` or `"MedSimp-JudgeBench"`; if given and it doesn't match the pool this service loaded → **400** |
| `bootstrap_iters` | int | no | 1000 | paired-bootstrap resamples for the recommended candidate's CI |
| `seed` | int | no | 42 | bootstrap seed (chained-rng — reproduces the committed receipt) |

```bash
curl -X POST <BASE_URL>/v1/audit_panel -H "Content-Type: application/json" \
  -d '{"incumbent_panel": ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen3-32B"],
       "candidate_pool": ["nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "google/gemma-3-27b-it",
                          "openai/gpt-oss-120b", "nvidia/nemotron-3-super-120b-a12b",
                          "deepseek-ai/DeepSeek-V4-Flash-0731", "nvidia/Nemotron-3-Ultra-550b-a55b"]}'
```

Response — `benchmark` (the pool that answered), an `incumbent` summary (per-stratum Φ_V, σ²_B, blindest stratum), the full `candidates_ranked` list, and a `recommendation`:

| Field | Notes |
|--|--|
| `recommendation.model` | the recommended judge to add |
| `recommendation.target_blind_spot` | the panel's blindest stratum (e.g. `diagnosis`) |
| `recommendation.expected_Phi_V_lift` | ΔΦ_V point estimate on that stratum, at the corrupted share of the rows it is computed on (v2: 50%; 51% for DeepSeek-V4-Flash's 233 complete rows; A8 threat 11) |
| `recommendation.ci_95` | bootstrap 95% CI for the lift |
| `recommendation.tied_top_candidates` | candidates whose blind-spot ΔΦ_V rounds to the same 0.01 bin as the top candidate's (`TIE_BAND` = 0.01; bins round(ΔΦ_V/0.01)·0.01), treated as a statistical tie. Bin edges are fixed, so candidates less than 0.01 apart can land in different bins and not tie: reweighted to other drop shares, the v2 pick alternates between gpt-oss-120b and DeepSeek-V4-Flash above 51% (A8 threat 11) |
| `recommendation.selected_among_ties_by` | tie-break rule: least collateral on non-blind strata (multi-stratum pools), then fewest ERROR verdicts, then specificity on clean controls (the two reliability keys were added for the v2 pool after its result was known) |
| `recommendation.caveat` | any stratum whose ΔΦ_V CI straddles zero |
| `candidates_ranked[]` | full pool ranking, by 0.01 bin of blind-spot ΔΦ_V and by the tie-break within a bin (per-stratum ΔΦ_V + Δσ²_B per candidate, plus `error_rows` and `specificity_clean` used by the tie-break) |

Live receipt, v2 pool (Llama+Qwen incumbent, 6-candidate pool → recommends **gpt-oss-120b**, +0.122, CI **[0.100, 0.142]**, tied with DeepSeek-V4-Flash, gemma ranked last): [`results/audit_panel_live_receipt_v2.json`](results/audit_panel_live_receipt_v2.json). The same request against the earlier automated pool recommended Nemotron Nano, +0.0706 at that pool's 41% diagnosis share (A8 threat 12) — preserved in [`results/audit_panel_live_receipt.json`](results/audit_panel_live_receipt.json).

### B4. The safety gate — how a verdict is produced

The three judges are called via Token Factory (Nemotron serverless; Qwen — and Llama in the current code — on dedicated endpoints); the verdict follows a **calibration-informed decision rule** (`safety_gate.py`) over the Qwen and Nemotron verdicts:

| Qwen ↓ / Nemotron → | Nemotron SAFE | Nemotron UNSAFE |
|--|--|--|
| **Qwen SAFE** | SAFE | DISAGREE — "diagnosis-drop risk" |
| **Qwen UNSAFE** | UNSAFE | UNSAFE |

Plus: **ERROR** in Qwen or Nemotron → **ERROR** (fail-safe; blocks in block mode). **Llama's verdict is returned but does not enter the rule — advisory only, shown for transparency and v1 continuity.** ("Calibration-informed," not "VAGT-calibrated": VAGT *measured* the panel; it did not set a threshold — Nemotron still needs threshold/prompt calibration, per A5.) The decision rule's "trust Qwen's 0.5% FP specificity" justification is from the calibration file, whose Qwen verdicts are stored from Project v1's calibration run (A8 threat 9); under the deployed gate prompt Qwen's FP is 9.5% (see B5).

**Why this rule (automated 708-item set, deployed gate prompt; [`results/gate_calibration_full.json`](results/gate_calibration_full.json)):**

| Strategy | Recall (508 corrupted) | FP (200 clean) | Flag rate | Bal. acc |
|--|--|--|--|--|
| **Qwen + Nemotron (deployed rule)** | **82.1%** (417/508) | 35.0% (70/200) | 68.8% | 73.5% |
| 3-way majority (≥2 UNSAFE) | 68.1% (346/508) | 10.0% (20/200) | 51.7% | 79.1% |
| Nemotron only | 79.5% (404/508) | 30.5% (61/200) | 65.7% | 74.5% |
| Qwen only | 63.2% (321/508) | 9.5% (19/200) | 48.0% | 76.8% |
| Llama only | 61.2% (311/508) | 9.5% (19/200) | 46.6% | 75.9% |

The deployed rule **maximizes recall (82.1%)** (by construction: it flags whenever Nemotron or Qwen does) — the priority for a diagnosis-drop tripwire, where a missed corruption costs more than a false alarm a reader can dismiss. The price is the highest clean false-positive rate (35.0%). **3-way majority** wins on balanced accuracy (79.1%) but sacrifices 14 points of recall: requiring two UNSAFE votes lets the two lower-recall judges (Llama 61.2%, Qwen 63.2%) outvote Nemotron on drops only it catches. **This is why Llama stays advisory** — adding its vote via majority would *lower* recall to 68.1%. The asymmetric rule keeps Nemotron's recall edge (the DISAGREE branch = Nemotron-alone UNSAFE), while Qwen's UNSAFE adds a few high-specificity catches on top (82.1% > Nemotron's 79.5% alone, on the automated set).

**v2 recheck** (hand-verified, 120 drops + 120 paired controls, deployed prompt; [`results/judgebench_v2_panel_gate.json`](results/judgebench_v2_panel_gate.json)): the deployed rule and Nemotron alone both catch 110/120 (91.7%), while 3-way majority catches 77/120 (64.2%) — so **under the deployed gate prompt** Llama stays advisory. On these genuine drops Qwen adds no recall over Nemotron, only false positives (58 vs 53 of 120). Under the calibration prompt the majority penalty nearly vanishes: 114 vs 115 of 120 ([`results/judgebench_v2_panel_calib.json`](results/judgebench_v2_panel_calib.json)).

**Why the gate keeps Nemotron Nano although the audit panel recommends gpt-oss-120b:** every v2 drop first passed gpt-oss's own judgement, as the construction oracle, that the diagnosis was gone, so its lead on this stratum is partly by construction, by an unmeasured amount (A8 threat 10); Nano's figures are free of that effect, and gpt-oss's latency and cost inside the gate have not been measured.

**DISAGREE branch — worked example (gate-level, real benchmark item).** A real MedSimp-JudgeBench diagnosis-stratum item run through the live 3-judge gate (`evaluate_safety`, Nebius Token Factory; captured 2026-09-02, when all three judges ran serverless and Qwen at 2,000 tokens — before the current dedicated-endpoint gate). The hand audit confirms the drop: idx 146 is ABSENT — depression genuinely removed — in [`results/tau_hand_labels_150.json`](results/tau_hand_labels_150.json):

| Field | Value |
|--|--|
| Input | idx 146 — Parkinson-disease discharge summary noting *"familial Parkinsonism and depression"*; the simplification keeps Parkinsonism but **silently omits depression** |
| Verdicts | Llama **SAFE** · Qwen **SAFE** · Nemotron **UNSAFE** |
| Consensus | **DISAGREE** |
| Warning | "diagnosis-drop risk" |

A dropped diagnosis a two-judge panel would have shipped; the third judge catches it. Captured verdict: [`results/disagree_case_gate.json`](results/disagree_case_gate.json).

> **Scope.** *Real:* the gate, the three Token Factory judge calls, and the verdicts. *Synthetic:* the input — the failing simplification is a **benchmark perturbation, not MediSimplifier's own output**. Our model's **confirmed self-drops are few** — a dual-auditor sample of flagged outputs confirmed a genuine diagnosis drop in only **2 of 20 flagged cases** (10%; 6 contested pending physician review, see B5) — so this failure is hard to elicit from `/v1/simplify`; we source it from MedSimp-JudgeBench and run it through the real gate. The DISAGREE branch is therefore a **defense-in-depth** path against a downstream or third-party simplifier feeding the gate — not a routinely-triggered path on our own model's output. The gate returns only a verdict (not Nemotron's rationale), so we attribute the flag to the item's single injected diagnosis drop (depression) — the only diagnosis-level change in the perturbation. idx 21 (the primary candidate) returned all-SAFE through the live gate despite UNSAFE in calibration — confirming that calibration verdicts do not transfer verbatim across prompts; we report the first item that actually split.

### B5. Operating characteristics

**DISAGREE rate (calibration verdicts).** The DISAGREE rule (Nemotron UNSAFE + Qwen SAFE) fires on **203/708 (28.7%)** of MedSimp-JudgeBench items — **136 on corrupted items** (81 of them diagnosis items, of which the hand audit confirms 5 as genuine drops, 13 counting borderline items) plus **67 on clean controls**, so **1 in 3 DISAGREEs (33.0%) fires on clean text** at this set's 72% corrupted share (automated labels, all four error types; that share depends on it, Nemotron's 35.2% clean false-positive rate does not), and **66.5% are false alarms** if a DISAGREE on a diagnosis item whose diagnosis is still present counts as one (70.4% if the borderline items count too; recount below the table). This is the rate in the calibration file, where Nemotron ran under the calibration prompt and Qwen's verdicts are stored from Project v1's calibration run (A8 threat 9), neither of them the deployed gate prompt (cf. idx 21, see Scope note in B4); the **deployed gate's** shares are measured directly below — **34.7% on clean text (51 / 147)** and 70.1–74.1% with the hand audit, close to these calibration figures.

**In plain terms:** under the deployed gate prompt, the Llama + Qwen pair says SAFE unanimously on 25.8% of corrupted items in the automated set (131/508). On the hand-verified v2 drops it's 41 of 120 (34.2%); each judge alone misses 64 of 120 (53.3%). Nemotron catches 110 of 120. The cost is false alarms: 45.5% of DISAGREEs on v2 fire on clean text, at 50% drops. On the automated set 34.7% do, at 72% corrupted items; that share is lower because of the higher prevalence (at a matched 50% its automated-label rates would give 57.4%) and because it counts every DISAGREE on a corrupted item as a catch (with the hand-audited diagnosis labels, 70.1–74.1% are false alarms, 73.1–75.5% at a matched 50%). Both matched figures are above v2's 45.5%, so the two sets' underlying rates differ (recount below the table). With 20% drops, v2's rates imply 76.9% ([`results/judgebench_v2_prevalence_sensitivity.json`](results/judgebench_v2_prevalence_sensitivity.json)).

**Deployed gate operating characteristics** (gate prompt, n=708, 0 ERRORs, Qwen3-32B via dedicated endpoint; full verdicts in [`results/gate_calibration_full.json`](results/gate_calibration_full.json)):

| | Calibration file (Nemotron: calibration prompt; Llama, Qwen: stored Project v1 verdicts) | Gate prompt (deployed) |
|--|--|--|
| DISAGREE rate (at 72% corrupted, automated labels) | 28.7% (203/708) | 20.8% (147/708) |
| Nemotron recall (automated labels) | 84.2% | 79.5% |
| Qwen recall (automated labels) | 55.9% | 63.2% |
| Llama recall (automated labels) | 31.7% | 61.2% |
| Qwen FP (clean) | 0.5% | 9.5% |
| DISAGREEs on clean text (clean/total; at 72% corrupted, automated labels) | 33.0% (67/203) | 34.7% (51/147) |
| DISAGREE false-alarm share, hand-audited diagnosis labels (PRESENT; PRESENT or BORDERLINE counted as no error) | 66.5% (135/203); 70.4% (143/203) | 70.1% (103/147); 74.1% (109/147) |

**Recounted with the hand audit.** The clean-text shares count every DISAGREE on a corrupted item as a genuine catch. The hand audit of the 150 automated diagnosis items ([`results/tau_hand_labels_150.json`](results/tau_hand_labels_150.json)) found the diagnosis still present in 128, borderline in 13 and absent in 9; each had a sentence removed, and PRESENT means the diagnosis is still in the text. The DISAGREEs include 60 of these items under the gate prompt (52 present, 6 borderline, 2 absent) and 81 in the calibration verdicts (68, 8, 5). Counting a DISAGREE on an item whose diagnosis is still present as a false alarm, as option B of the τ re-score does ([`results/tau_recompute_summary.json`](results/tau_recompute_summary.json)), the gate prompt's share is **70.1%** (103/147), and **74.1%** (109/147) with the borderline items counted as well; the calibration verdicts' share is 66.5% (135/203) and 70.4% (143/203). On these labels 51.8–53.7% of the 708 items carry a genuine error, not 72%. Reweighted to 50%, the gate prompt's share is 73.1–75.5%, still above v2's 45.5%. The gap is in the DISAGREE rate on items with a genuine error: 10.4–11.6% here (38 of 367; 44 of 380) against 45.0% on v2 (54 of 120), while on items without one it is 31.4–32.0% (103 of 328; 109 of 341) against 37.5% (45 of 120). Most of this set's genuine errors are negation, lateral and dose items, and Qwen flags most of those itself, so the gate returns UNSAFE rather than DISAGREE on them (288 of 358). Those three error types were not hand-audited and keep their automated labels ([`scripts/recount_disagree_708_hand_labels.py`](scripts/recount_disagree_708_hand_labels.py), [`results/disagree_708_hand_label_recount.json`](results/disagree_708_hand_label_recount.json)).

Under the deployed gate prompt Llama and Qwen are more sensitive and less specific than in the calibration file, whose Llama and Qwen columns hold verdicts stored from Project v1's calibration run (A8 threat 9). For Llama this is not a clean prompt effect: on all 115 corrupted rows that share an item index with a clean control, its stored verdict repeats its verdict on that control ([`results/tau_recompute_v1_matched.json`](results/tau_recompute_v1_matched.json) `idx_repeat_check`), so its recall rise (31.7%→61.2%) mixes the prompt change with that repetition. Qwen's FP rise (0.5%→9.5%) means the '0.5% FP specificity anchor' in the decision rule reflects the calibration harness, not the deployed gate.

**Split-half checks (stability, not out-of-sample).** *Decision rule* (automated 708-item set, deployed prompt, stratified 50/50 split by record, seed=42; [`results/split_half_validation.json`](results/split_half_validation.json)): the deployed rule is the recall-maximizer on both halves — **80.8%** and **83.4%** (82.1% on all 708) — and 3-way majority still wins balanced accuracy on both; see the v2 recheck in B4. This is not an out-of-sample test: nothing is fitted on either half, the rule was designed on these same 708 items, and it flags whenever Nemotron or Qwen does, so its recall is at least theirs by construction. *Nemotron's added value* (hand-verified v2 stratum, split 60/60 by patient, deployed prompt; [`results/judgebench_v2_split_half.json`](results/judgebench_v2_split_half.json)): ΔΦ_V(Nemotron | Llama+Qwen) is **+0.0735 [+0.036, +0.104]** and **+0.0789 [+0.047, +0.109]** on the two halves — positive on both, consistent with the full-stratum +0.0765.

All three judges run in parallel (ThreadPoolExecutor, max_workers=3) via Token Factory (Nemotron serverless; Qwen on a dedicated endpoint) — latency ≈ max(judges), not the sum (~24–27 s total).

**Student self-audit — does the served model itself drop diagnoses?** We ran all **1,001** v2 student test simplifications back through the deployed gate: it flagged **521 (52.0%)** as potentially lossy (DISAGREE + UNSAFE). That high rate is expected — the gate scores "preserves *all* critical information," which any simplification can fail without dropping a diagnosis, and its clean false-positive rate is ~35% on the automated controls and 48% on the v2 paired controls (58 of 120); where genuine drops are rare, most of its flags are expected to be false alarms (A8 threat 11). To separate genuine diagnosis/medication drops from ordinary simplification, we drew a **30-case sample** (10 UNSAFE + 10 DISAGREE + 10 SAFE controls, seed=42) and ran a **dual-auditor** review — two independent auditors from different model families, **Claude Sonnet 5 (Anthropic) and Gemini 2.5 Pro (Google)**, neither in the gate nor the teacher pipeline — classifying each. On the 20 flagged cases they **agreed on 14/20 (70%)**: **12/20 general simplification** (nothing clinically needed lost), **2/20 a genuine diagnosis drop** confirmed by both (idx 174, 44), and **6/20 contested**, now awaiting physician adjudication (reserved `human_judgment` fields in [`results/student_audit_review.json`](results/student_audit_review.json); guide in [`docs/ADJUDICATION_BRIEF.md`](docs/ADJUDICATION_BRIEF.md)). Agreement means the same category: idx 529 counts among the 12, since both auditors chose general simplification, but Gemini also flagged a dropped medication. Neither auditor found a dropped diagnosis or medication in any of the 10 SAFE controls. So the gate's 52% flag rate reflects the inherent readability-vs-completeness trade-off of simplification, **not** systematic diagnosis loss: diagnosis drops are **10–30% of flagged cases** (2/20 confirmed by both auditors, 6/20 flagged by either), and any diagnosis-or-medication drop flagged by either auditor is **up to 40%** (8/20, including idx 529, counted as agreement above), pending review. The result cuts both ways — our model does **not** reliably self-drop diagnoses (DISAGREE fired on 265 of 1,001 real outputs, but in the audited sample most flags were general simplification), yet it is **not** flawless either, which is precisely why the gate monitors every rewrite. *(A 30-case sample, seed=42, LLM-assisted + human adjudication — not extrapolated as a census of the 521.)* All 1,001 outputs above are the saved evaluation outputs, generated with a 512-token cap; 146 of them stopped at it ([`results/eval_v2_output_truncation.json`](results/eval_v2_output_truncation.json)), and the live endpoint's default is 1,024 (B3). Five of the 30 audited outputs stopped at that cap (idx 193, 174, 56, 393, 395), all among the 20 flagged, including idx 174, one of the two confirmed drops named earlier in this paragraph.

### B6. Model card — the served student

v2 uses the winning configuration from v1 ablation (r=32, all_attn, seed=42, 3 epochs). No additional ablation was run — the v1 winner reproduced on **Nebius H100 within a ROUGE-L delta of 1.6–5.0%** of the original **Technion H200** runs (across 3 v1 models: OpenBioLLM −1.6%, Mistral-7B −3.7%, BioMistral −5.0%; see the [v1 reproduction table](https://github.com/deepset01-sys/medisimplifier-nebius)) and transfers directly to the Nemotron-taught dataset.

Base model loaded in **4-bit NF4 QLoRA** (`BitsAndBytesConfig`: `load_in_4bit=True`, `bnb_4bit_quant_type='nf4'`, double-quant, `compute_dtype=bfloat16`). The merge step loads the base **unquantized (fp16)** — not 4-bit — for merge fidelity.

| Parameter | Value | Source |
|-----------|-------|--------|
| rank | 32 | v1 ablation winner |
| modules | all_attn (q+k+v+o) | v1 ablation winner |
| epochs | 3 | v1 full training |
| seed | 42 | v1 convention |
| lora_alpha | 64 | 2r, per rsLoRA |
| lora_dropout | 0.05 | v1 convention |
| use_rslora | True | rank-stabilized LoRA |

> **What the endpoint serves:** The Safe Endpoint v5 serves the v2 (Nemotron-taught) student behind the safety gate (diagnosis-drop detection) — v2's contribution is the VAGT research pipeline and the safety gate, **not a readability improvement**. For maximum readability the v1 student is simpler (FK-Grade 7.33 vs v2's 8.87); but v2's endpoint is the research/safety demo, and that is what is served.

> **Adapter provenance:** `chambul/MediSimplifier-OpenBioLLM-v2-merged` merges the Nebius-trained LoRA adapter (`medisimplifier-adapters-v2/adapter/`, r=32, all_attn, 3 epochs) with the base model. ROUGE-L 0.5254 documented in [`results/eval_v2_results.json`](results/eval_v2_results.json).

### B7. Deployment on Nebius

The LoRA adapter is merged into the base model before serving:

1. Run merge job (Nebius Job):
   `jobs/job_merge_v2.yaml` — reads from `medisimplifier-adapters-v2/adapter/`, writes merged model to bucket via `aws s3 cp`

2. Publish to HuggingFace:
   `chambul/MediSimplifier-OpenBioLLM-v2-merged` (public — no bucket credentials required to reproduce)

3. Deploy Safe Endpoint v5 (Nebius GPU Endpoint):
   `endpoint-v5` image (see docs/REPRODUCIBILITY.md) — vLLM loads model from HuggingFace, judges via Token Factory with `NEBIUS_API_KEY` (Qwen on a dedicated endpoint that must be running — B9)

```bash
# Step 1: Merge (Nebius Job)
# Submit jobs/job_merge_v2.yaml via Nebius Console

# Step 1b: Download merged model from bucket
aws s3 sync s3://medisimplifier-adapters-v2/merged_openbio_v2/ \
  /tmp/merged_openbio_v2/ \
  --endpoint-url https://storage.eu-north1.nebius.cloud \
  --region eu-north1

# Step 2: Publish to HuggingFace
huggingface-cli upload \
  chambul/MediSimplifier-OpenBioLLM-v2-merged \
  /tmp/merged_openbio_v2/

# Step 3: Deploy endpoint
# Deploy via Nebius Console → AI Services → Endpoints → Create Endpoint (see B9 + docs/REPRODUCIBILITY.md for the verified CLI command)
# Requires: NEBIUS_API_KEY, HF_TOKEN
```

Note: Judges reproducing the endpoint load directly from `chambul/MediSimplifier-OpenBioLLM-v2-merged` on HuggingFace — no bucket credentials required.

> **Why Token Factory?** Nemotron Super and Nano are both served per-token with zero idle cost. The teacher JudgeBench-reference run (519 unique calls → 708 references) cost ~$1.7 and finished in ~21 min (Nebius Console; billing export pending — #12); the judge panel and VAGT analysis add no GPU management. Model strings verified live via `/v1/models`.

> **Dedicated judge endpoints (Token Factory; configuration and pricing from the Nebius Console):** Qwen3-32B (H100 NVLink, eu-north1, $0.07/min) and Llama-3.3-70B (H200 NVLink, us-central1, $0.08/min) — stop between uses. Endpoint IDs in `src/safety_gate.py:15-17`.

Full adapter storage flow → [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)

### B8. Known issues & operating caveats

1. **Qwen judge swap — RESOLVED.** `Qwen/Qwen3-32B` was removed from Token Factory's serverless catalog mid-project; the gate now runs the same model via a dedicated Nebius endpoint (`dedicated/Qwen/Qwen3-32B-AcpEMaRtFNy6`). Calibration re-run confirmed 0 ERRORs and measured the gate's actual operating characteristics (see B5).
2. **Prompt drift.** Calibration used a different prompt than the deployed gate (idx 21 returned all-SAFE through the live gate despite UNSAFE in calibration — confirming verdicts do not transfer verbatim across prompts). Rates are therefore reported per prompt: calibration-prompt rates (A5) and deployed-gate-prompt rates (B4, B5).
3. **endpoint-v5 serves the earlier pool.** Its `POST /v1/audit_panel` answers from the earlier automated pool (the v5 image predates `audit_pool_v2/`); the CPU service (B2 Tier 1) serves v2.
4. **Llama routing.** Serverless Llama-3.3-70B returns 403 on this account, so the current gate code calls a dedicated endpoint (`src/safety_gate.py:15`). The endpoint-v5 image still calls serverless Llama, so its advisory Llama verdict will be `ERROR`; consensus is unaffected.
5. **Model-catalog volatility.** The Token Factory serverless catalog changed mid-project (item 1); [`results/models_verified.json`](results/models_verified.json) is a snapshot, not a guarantee. Dedicated endpoints pin a model.
6. **The gate checks for dropped content, not added content.** The endpoint-v5 capture in B2 adds admission/discharge statements not in the input and still passes SAFE.

### B9. Reproduce the deployment

**Environment:** Python 3.11+ (`docker/Dockerfile.cpu` uses `python:3.11-slim`) · `pip install -r requirements.txt` installs openai, numpy, requests, tqdm — enough for the safety gate and the judge/VAGT scripts. The endpoint and tests also need fastapi, pydantic, httpx, uvicorn and pytest; training, evaluation and data prep use the pinned [`docker/requirements_train.txt`](docker/requirements_train.txt) (torch, transformers, peft, datasets) inside the train image.
**Auth:** `export NEBIUS_API_KEY=<your-token-factory-key>`

#### Nebius Jobs (Console)

Submit each job via Nebius Console → AI Services → Jobs → Create Job:

| Job | Config file | Expected output |
|-----|-------------|-----------------|
| Training | `jobs/job_train_v2.yaml` | adapter in `medisimplifier-adapters-v2/adapter/` |
| Evaluation | `jobs/job_eval_v2.yaml` | `rouge_l: 0.5254` in `results/eval_v2_results.json` |
| Nemotron-refs eval | `jobs/job_eval_v2_nemotron_refs.yaml` | `rouge_l: 0.6010` in `results/eval_v2_nemotron_results.json` |
| Merge | `jobs/job_merge_v2.yaml` | merged model in bucket + published to HF |

Merge job requires: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (Nebius S3 keys — create at IAM → Service Accounts → Access keys).

The merged model is publicly available — no training required to test the endpoint:
`chambul/MediSimplifier-OpenBioLLM-v2-merged`

#### Nebius Endpoint (deploy the Safe Endpoint v5)

The Safe Endpoint is a **Nebius AI *Endpoint*** — not a Job. Deploy it via **Console → AI Services → Endpoints → Create Endpoint** (image, preset, command, and env from `jobs/safe_endpoint_v2.yaml`), or with the **verified CLI command** in [docs/REPRODUCIBILITY.md → Deploy the endpoint](docs/REPRODUCIBILITY.md).

- **Image:** `chambul/medisimplifier:endpoint-v5@sha256:0e40cff4…` — public Docker Hub, digest-pinned (no `--registry-*` auth needed).
- **Prerequisites:** `NEBIUS_API_KEY`, `HF_TOKEN`, and the **Qwen3-32B judge dedicated endpoint must be running** (`dedicated/Qwen/Qwen3-32B-…`) — otherwise the gate returns `ERROR` on the Qwen verdict (see B7/B8). The endpoint-v5 image calls serverless Llama — see B8 item 4.
- **Verify:** `GET /health` → `{"audit_panel": true, "ready": true}`

## Hardware and cost

Actual Nebius billing for v2 (all figures from Nebius Console):

| Step | Service | Usage | Cost |
|------|---------|-------|------|
| Nemotron Super teacher (9,999 calls) | Token Factory | 83.90M output tokens | $75.51 |
| Nemotron Nano calibration + student self-audit (708 × 3 judges + 1,001 × 3) | Token Factory | 3.22M input + 8.23M output tokens | $2.17 |
| Llama (endpoint smoke tests) | Token Factory | 3.03M input + 0.12M output | $0.44 |
| Gate calibration — Llama + Nemotron Nano (708 items, per-token share) | Token Factory | 1.28M input + 1.10M output | $0.46 |
| Dedicated Endpoint (Qwen3-32B judge) | Dedicated Endpoint | 22.67 GPU hours | $91.80 |
| Audit-pool candidates (5×708: Ultra/Super/gpt-oss/DeepSeek/gemma) | Token Factory | ~14M output tokens | $8.74 |
| H100 NVLink (training + eval + merge) | Jobs | 11.82 GPU hours | $45.53 |
| CPU + RAM | Jobs | 629.52 vCPU / 2,518.07 GiB hours | $15.61 |
| Disk + Object Storage | Storage | 76,542.64 GiB hours | $7.84 |
| **Total v2 (Nebius)** | | | **$248.10** |

*Note: the gate calibration's Qwen3-32B calls ran on the dedicated endpoint — that share is inside the $91.80 row. External API costs (dual-auditor review: Claude Sonnet 5 + Gemini 2.5 Pro, ~60 calls) are estimated at ~$1–2 and not included in the Nebius total.*

**Training run (verified from `logs/train_v2.json.gz`, Nebius Job `aijob-e00rwxv72fe81f54we`):**

```
2026-08-28 13:45:40  MediSimplifier Training — openbio
                     LoRA: r=32, modules=all_attn, rsLoRA=True
                     Epochs: 3 | Trainable params: 27,262,976 (0.60%)
2026-08-28 14:42:51  epoch 1.0 | eval_loss 0.8496
2026-08-28 15:30:09  epoch 2.0 | eval_loss 0.8378
2026-08-28 16:17:32  epoch 3.0 | eval_loss 0.8610
2026-08-28 16:17:35  train_runtime 8523.36s | train_loss 0.7803
```

> **Checkpoint selection:** training runs `save_strategy='epoch'` with `load_best_model_at_end=True` on `eval_loss` — so the saved adapter is the **epoch-2** checkpoint (eval_loss 0.8378), the best, **not** the epoch-3 overfit (0.8610). `merge_adapter.py` merges that saved adapter.

H100 NVLink rate: ~$3.85/hr on Nebius eu-north1.
Training: ~2.4h (8,523s), 3 epochs, seed=42.
The dedicated Qwen3-32B endpoint ($91.80, 22.67 GPU hours) is the single largest line — left running across the gate calibration and student self-audit. Nemotron Super teacher generation is $75.51 (16,000-token reasoning budget per call). Llama and Nemotron Nano are per-token serverless; both the dedicated Qwen endpoint and the vLLM student host are stopped between demos to avoid idle GPU-hour billing.

## Project structure

```
src/
  train.py                       LoRA training — runs as Nebius Job (--dataset flag added for v2)
  evaluate.py                    Metrics: ROUGE-L, SARI, BERTScore, FK-Grade
  merge_adapter.py               Merge LoRA adapter into base model → HuggingFace publish
  safe_endpoint.py               Safe Simplification Endpoint v5 — FastAPI: vLLM + calibration-informed gate (2-judge rule + advisory Llama)
  cpu_endpoint.py                CPU-only audit_panel service — FastAPI: /v1/audit_panel + /health ONLY (no vLLM, no gate, no key)
  safety_gate.py                 calibration-informed safety gate — Qwen + Nemotron Nano decide, Llama advisory (Qwen3-32B and Llama-3.3-70B via Token Factory dedicated endpoints)
  serve_vllm.py                  vLLM inference server (legacy standalone)
  run_gate_calibration.py        708-item calibration through the deployed gate prompt → gate_calibration_full.json
  run_student_audit.py           1,001 v2 student outputs → gate (2-judge rule + advisory Llama; student self-audit) → student_audit.json
  sample_audit_review.py         build 30-case review template (seed=42) + score judgments
  llm_review_audit.py            dual-auditor review (Claude Sonnet 5 + Gemini 2.5 Pro) of flagged cases
  measure_reference_fk.py        FK-Grade of Claude vs Nemotron reference sets → reference_fk_grade.json
  eval_vs_nemotron_refs.py       Evaluate student vs Nemotron references
  run_disagree_capture.py        Capture live DISAGREE case from endpoint
  audit_panel/                   /v1/audit_panel service (Steps 1-6):
    vagt_core.py                 generalized VAGT decomposition (σ²/Φ_V + paired bootstrap CIs)
    pool_loader.py               load a verdict pool + ground truth (merge by row_id)
    selector.py                  blind-spot-first ranking; pool-derived strata; ties (the top candidate's 0.01 bin) → least collateral, then reliability (errors, specificity)
    schemas.py                   FastAPI request/response models
    router.py                    POST /v1/audit_panel route (mounted in safe_endpoint.py + cpu_endpoint.py; AUDIT_POOL_DIR selects the pool)
    build_pool.py                reshape calibration → audit_pool/ (lossless, self-validating)
    gen_pool_verdicts.py         Step 6: generate a candidate's 708-row verdicts (dual-registry)
docker/
  Dockerfile.train               Builds train-v29/v30/v31/v32 (cryptography==48.0.1 pinned)
  Dockerfile.endpoint            Safe Endpoint v5 image (endpoint-v5)
  Dockerfile.cpu                 CPU-only audit_panel image (audit-cpu-v2.1; ships both pools, serves audit_pool_v2/; no vLLM/torch/CUDA)
jobs/
  job_train_v2.yaml              v2 fine-tuning job (train-v29, sha256:bbbf6df1..., Nemotron dataset, adapters-v2 bucket)
  job_eval_v2.yaml               v2 evaluation job (train-v30, sha256:6c3cd4cd..., GuyDor007 test)
  job_eval_v2_nemotron_refs.yaml v2 Nemotron-refs eval job (train-v32, sha256:2c95dfef..., aijob-e00gz7bez5pwq35fze)
  job_merge_v2.yaml              v2 merge job (train-v31, sha256:9d832391..., adapter → bucket → HuggingFace)
  safe_endpoint_v2.yaml          Safe Endpoint v5 deployment config (endpoint-v5 image; adds /v1/audit_panel)
scripts/
  start_endpoint.sh              Boot vLLM + Safe Endpoint v5 API (inside endpoint-v5 image)
  start_cpu_endpoint.sh          Boot the CPU-only audit_panel service (uvicorn cpu_endpoint:app)
  build_physician_review.py      Build blinded 50-case physician spreadsheet (seed=42)
  merge_physician_labels.py      Merge physician labels → human-anchored τ + inter-rater κ
  compute_pool_cis.py            Per-candidate paired bootstrap CIs (all 5 pool candidates × 4 strata; automated pass)
  compute_null_baseline.py       Null-rater baseline (constant-UNSAFE + random-47%), per stratum at each stratum's own corrupted share (automated pass; A8 threat 12)
  compute_split_half.py          Split-half stability check under the deployed gate prompt (automated pass; not out-of-sample)
  compute_consensus_accuracy.py  Consensus-accuracy baseline vs Φ_V decomposition (majority-vote bal-acc; automated pass)
  run_vagt_loop_experiment.py    VAGT prescribes-then-verifies loop: A0 gate-prompt vs A1 scoped-D1 Nemotron on the diagnosis stratum (n=350; pre-registered thresholds; paired bootstrap; Llama/Qwen held fixed) — automated labels; superseded by run_vagt_loop_v2.py
  run_vagt_loop_v2.py            Scoped-gate experiment on the v2 stratum (240 items × 2 arms × 4 calls, token ladder, placebo noise check); refuses the full run unless the pre-registration and this runner are committed and unmodified, and records their blob ids + HEAD
  build_audit_pool_v2.py         Build audit_pool_v2/ from the committed v2 results; self-verifies vs judgebench_v2_pool_table.json
  build_judgebench_v2.py         JudgeBench v2 diagnosis-drop generator (candidate primary-diagnosis drops + auto-gates; every accepted item human-reviewed)
  verify_tau.py                  LLM-assisted triage harness for the 150-item hand audit of the automated diagnosis labels (human audits every call)
  run_tau_recompute_v1.py        Automated-pass re-score with the hand audit: reproduces tau_recompute_summary.json, rebuilds it with all three judges under one prompt, reweights to 41%/50% drops, shuffled-Nemotron null (post hoc)
  run_panel_judgebench_v2.py     3-judge gate panel over the 240 v2 items (deployed + calibration prompts)
  run_pool_judgebench_v2.py      6-candidate pool ΔΦ_V on the v2 stratum (--analyze-only rebuilds the table offline)
  run_phi_v_recompute.py         Φ_V recompute on the hand-verified v2 stratum (full cells + two subsets — category hidden (47) and the protocol's strict tier (30) — each with paired and all-120 controls)
  build_tau_recompute_v2_summary.py  Protocol §12 deliverable: premise test (recall, false positives, Wilson CIs, bands), expert-recoverability split, primary and secondary (delivered after the results were known)
  run_null_control_v2.py         τ-blind permutation null for the pool ΔΦ_V (N_PERM=1000)
  check_null_control_ties_v2.py  Exact ties between each real ΔΦ_V and its permutation null; p with ties counted and excluded, and under both σ²_N estimators
  recount_disagree_708_hand_labels.py  708-set DISAGREE false-alarm share recounted with the 150 hand labels (PRESENT; PRESENT or BORDERLINE as no error)
  run_prevalence_sensitivity_v2.py  ΔΦ_V and Φ_V reweighted to 50/33/20/10/5% drops and a 1–99% grid, and the gate's share of real flags at the five shares (post hoc; A8 threat 11)
  run_prevalence_sensitivity_v1.py  Automated-pass ΔΦ_V (calibration file, gate file, null-rater control) with every stratum at one common corrupted share, and the selector with the two null raters added (post hoc; A8 threat 12)
  run_split_half_v2.py           Patient-level 60/60 split-half validation of the pool ΔΦ_V
  check_deepseek_budget_v2.py    DeepSeek's 7 ERROR items re-run at max_tokens 4000 vs 8000 (finish_reason, usage, selector effect)
  measure_output_truncation.py   Which saved evaluation outputs stopped at the 512-token cap, and the gate's flags on them (offline) → eval_v2_output_truncation.json
logs/
  train_v2.json.gz               v2 training log — Nebius Job aijob-e00rwxv72fe81f54we, 8,523s, per-epoch eval_loss
docs/
  ADJUDICATION_BRIEF.md          unified 50-case blinded physician protocol (5 categories matching VAGT strata, spreadsheet recording)
  NEMOTRON_INSIGHTS.md           five mechanism-backed findings from working with Nemotron Nano + Super (diversity judge, budget, logprobs, paraphrase-null, teacher gap)
  REPRODUCIBILITY.md             container image digests + adapter storage flow + rebuild steps
  judgebench_v2_protocol.md      FROZEN pre-registration for the diagnosis-stratum rebuild (committed before any judge ran)
  judgebench_v2_protocol_erratum.md  Erratum to the frozen protocol: §0 "+0.071 reversed to −0.144" and §7 "apples-to-apples with the +0.071" (2026-09-29)
  vagt_loop_v2_preregistration.md  Git-enforced pre-registration of the v2 scoped-gate experiment (committed d69f506 before any call; its blob id is recorded in the results)
app/
  demo.jsx                       React single-page demo — Act 1 (gate catches drop) + Act 2 (audit_panel leaderboard)
  index.html                     Vite entry point
  src/main.jsx                   React mount
  src/index.css                  Minimal CSS reset (clinical layout)
  package.json                   Pinned deps (React 19, Vite 8)
  package-lock.json              Pinned dependency tree (npm install reproducibility)
  vite.config.js                 Vite config — conditional base (dev=/ prod=/medisimplifier-nemotron-vagt/) + /v1 proxy
  README.md                      Clone-and-run instructions (npm install && npm run dev)
.github/
  workflows/deploy.yml           GitHub Actions — build app/ (Vite) → gh-pages → public demo URL
audit_pool/
  ground_truth.json              708-item ground truth (τ labels, stratum, row_id) — earlier automated pool (superseded on diagnosis)
  candidates.yaml                pool manifest (pooled + pending candidates)
  verdicts/                      per-judge 708-row verdict files (8: 3 incumbents + 5 additional models)
audit_pool_v2/                   v2 hand-verified pool — served by the CPU /v1/audit_panel service
  ground_truth.json              240 items: 120 τ=1 primary-diagnosis drops + 120 τ=0 paired controls
  candidates.yaml                manifest + v2 provenance (generated)
  verdicts/                      per-judge 240-row verdict files (same 8 models, deployed gate prompt)
tests/
  test_audit_panel.py            25-test suite: v1 historical lock (Nano, [0.0552, 0.0866]) + v2 pool (gpt-oss, [0.1000, 0.1416], reliability tie-break) + mechanics
nemotron_judge_test.py           Nemotron Nano as safety judge (3-judge calibration, checkpointed)
nemotron_teacher.py              Nemotron Super teacher — JudgeBench references
nemotron_training_data.py        Nemotron Super teacher — full 9,999-record training set (resume-capable)
vagt_nemotron_analysis.py        VAGT 3-rater decomposition (σ²_τ/σ²_B/σ²_R/σ²_N/Φ_V + bootstrap CIs)
compare_teachers.py              ROUGE-L comparison: Claude Opus vs Nemotron Super references
nemotron_calibration_full.json   708-sample 3-judge verdicts (Llama + Qwen + Nemotron Nano; automated 708-item pass)
nemotron_references.json         708 JudgeBench references (Nemotron Super; generated, not used in any reported number — A2)
teacher_comparison.json          ROUGE-L 0.525 Claude vs Nemotron (9,976 pairs)
results/eval_v2_results.json     v2 eval: ROUGE-L 0.5254 / SARI 60.36 / BERTScore 0.9113 / FK 8.87
results/eval_v2_nemotron_results.json  v2 eval vs Nemotron refs: ROUGE-L 0.6010 / BERTScore 0.9321 / SARI 64.18 (n=998)
results/student_predictions.json       the 1,001 saved v2 evaluation outputs (index, input, prediction, Claude reference); input to the self-audit, the 30-case review, the physician sheet, the v2 panel run and the truncation count
results/eval_v2_output_truncation.json  146 of the 1,001 stopped at the 512-token cap (139 mid-sentence); the gate flags 69.9% of those vs 49.4% of complete outputs
results/endpoint_smoke_test.json       earlier SAFE capture (pre-v5, no capture metadata; superseded by endpoint_v5_smoke_test.json)
results/models_verified.json           both Nemotron model strings verified via /v1/models
results/disagree_case_gate.json        gate-level DISAGREE capture — JudgeBench idx 146, Nemotron UNSAFE / Llama+Qwen SAFE
results/gate_calibration_full.json     708-item deployed-gate calibration (0 ERRORs; DISAGREE 20.8%, Qwen FP 9.5%)
results/student_audit.json             1,001 student outputs through the gate (SAFE 47.4% / flagged 52.0%, plus 0.6% ERROR)
results/student_audit_review.json      30-case dual-auditor review (Claude + Gemini; 2/20 confirmed diagnosis drops; human_judgment on 6 contested)
results/reference_fk_grade.json        FK-Grade: Claude refs 7.2 / Nemotron refs 10.08 (Δ+2.88, textstat 0.7.13, n=9,976)
results/pool_candidate_cis.json        Per-candidate ΔΦ_V + 95% CI (all 6 candidates × 4 strata; automated pass)
results/null_baseline_cis.json         Null-rater control, automated pass: mean ΔΦ_V over the four strata at their own corrupted shares (0.30–0.43; no CI for the mean) constant-UNSAFE −0.063, random-47% −0.037, Nemotron +0.037; with every stratum reweighted to 50%, constant-UNSAFE's is +0.0066 (A8 threat 12)
results/judgebench_v1_prevalence_sensitivity.json  Automated-pass ΔΦ_V with every stratum at one common corrupted share (50%, 30%, 1–99% grid), null-rater means, selector with the two null raters added (post hoc; A8 threat 12)
results/split_half_validation.json     Automated-pass split-half (decision rule; diagnosis result superseded — see A8)
results/consensus_accuracy.json        Consensus-accuracy vs Φ_V, automated pass (majority-vote bal-acc drops on diagnosis 60.5%→58.3%)
results/vagt_loop_summary.json         v1 VAGT loop, automated labels (disclosed history): ΔJ (Youden) −0.083 [−0.240,+0.069], all 3 thresholds fail; inconclusive on its 8–21 hand-labelled genuine drops — superseded by vagt_loop_v2_*
results/vagt_loop_A0.json              Per-item A0 arm (deployed gate prompt) verdicts — same-harness baseline
results/vagt_loop_A1.json              Per-item A1 arm (scoped D1 rubric) verdicts + source_items_count/defects — paraphrase-FP evidence (e.g. idx 12: "leukemia"→"fast-growing blood cancer" flagged as dropped)
results/vagt_loop_v2_summary.json      Scoped gate on v2 (pre-registered, git-enforced; run_meta = HEAD d69f506 + blob ids): guardrail PASS ΔR +0.019 [−0.031,+0.069]; primary FAIL ΔJ +0.046 [−0.060,+0.154]; driver FAIL ΔF −0.027 [−0.129,+0.077]
results/vagt_loop_v2_calls.json        All 1,920 calls with every attempt (budget step, finish_reason, tokens, time) and A1's cited defects
results/vagt_loop_v2_pilot.json        Cost pilot: 20 calls on non-analysed controls, projected $1.03
results/vagt_loop_v2_deviations.md     Deviations log: 4 gaps, none changes a verdict; blob ids of the imported code and inputs
results/physician_review.csv           Blinded 50-case physician spreadsheet (seed=42; 6 contested + 44 stratified)
results/physician_review_KEY.csv       De-blinding key (Case# → orig_index → stratum → source)
results/audit_panel_live_receipt.json  Live /v1/audit_panel receipt, earlier automated pool (superseded: Nano, +0.0706, CI [0.0552, 0.0866])
results/audit_panel_live_receipt_v2.json  Live /v1/audit_panel receipt, v2 pool (gpt-oss-120b, +0.122, CI [0.100, 0.142])
results/tau_hand_labels_150.json       Hand audit of the 150 automated "dropped diagnosis" items (128 PRESENT / 9 ABSENT / 13 BORDERLINE)
results/tau_recompute_summary.json     Automated labels re-scored with the hand audit: primary cell ΔΦ_V −0.1438 [−0.1945, −0.0979] at 2.7% drops against the +0.0706's 41%, Llama/Qwen and Nemotron under different prompts; the sign change comes from the drop share, not the labels (dated correction in the file)
results/tau_recompute_v1_matched.json  That re-score reproduced, rebuilt with all three judges under the deployed prompt, reweighted to 41% and 50% drops, with a shuffled-Nemotron null (post hoc)
results/judgebench_v2_tau1_final.json  v2 stratum: 120 hand-verified primary-diagnosis drops (τ=1)
results/judgebench_v2_clean_controls.json  292 controls: 120 primary-paired (used) + 172 supplementary
results/judgebench_v2_panel_gate.json  240-item panel, deployed gate prompt (0 ERROR)
results/judgebench_v2_panel_calib.json 240-item panel, calibration prompt
results/judgebench_v2_phi_v_recompute.json  Φ_V on v2: deployed full +0.0765 [+0.0516, +0.0992]
results/judgebench_v2_pool_table.json  6-candidate pool on v2 (gpt-oss +0.1220, DeepSeek +0.1238, …)
results/judgebench_v2_pool_<model>.json  per-candidate 240-row verdicts (5 files)
results/judgebench_v2_null_control.json  τ-blind permutation null per candidate
results/judgebench_v2_null_control_ties.json  exact ties in that null per candidate (Super: 1 tie, p 0.002 counted / 0.001 excluded)
results/disagree_708_hand_label_recount.json  708-set DISAGREE false-alarm share with the hand labels: 70.1% / 74.1% deployed, 66.5% / 70.4% calibration
results/judgebench_v2_prevalence_sensitivity.json  ΔΦ_V and Φ_V reweighted to 50/33/20/10/5% drops and a 1–99% grid, and gate operating characteristics at the five shares (post hoc; A8 threat 11)
results/judgebench_v2_split_half.json  patient-level split-half per candidate
results/tau_recompute_v2_summary.json  Protocol §8 premise test (deployed prompt: neither band; calibration prompt: NO BLIND SPOT), false positives incl. the protocol's 200 clean controls, expert-recoverability split
results/judgebench_v2_agreement_recompute.json  Fleiss/Krippendorff on v2 (incumbent vs +Nemotron)
results/audit_panel_receipt_v2_diagnosis.json  Offline v2 receipt: gpt-oss-120b +0.1220 [0.1000, 0.1416]
results/gate_calibration_full.INVALID-qwen-removal.json  Archived invalid gate run (146 Qwen ERRORs from the Qwen3-32B removal mid-run; 47880b9)
results/endpoint_v5_smoke_test.json    endpoint-v5 smoke test (SAFE capture; honest note on non-determinism)
vagt_nemotron_results.txt        VAGT decomposition output (per-feature, both rater sets; automated 708-item pass)
vagt_bootstrap_cis.json               paired-Δ 95% CIs, automated pass (+0.071 [+0.055,+0.087] on diagnosis, superseded — A6)
FINDINGS.md                      Automated-pass findings write-up (2026-08-27; diagnosis results superseded — A6/A8)
requirements.txt                 openai · numpy · requests · tqdm (training deps: docker/requirements_train.txt)
CLAUDE_CODE_CONTEXT.md           Implementation context for Claude Code (model strings, paths)
prepare_hf_dataset.py            Prepare and publish HuggingFace dataset
docker/build_and_push.sh         Legacy build script — builds/pushes train-v28 to Docker Hub only (later images built manually; see REPRODUCIBILITY.md)
docker/requirements_train.txt    Pinned training dependencies (cryptography==48.0.1)
```

Note: `nemotron_training_references.json` (58MB) is gitignored — data available as `chambul/medisimplifier-nemotron-dataset` on HuggingFace.

Full container image digests and rebuild steps → [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)

## Dataset and models

> **Note on HuggingFace accounts:** The original dataset and Technion-era adapters are published under **GuyDor007** (Guy Dor, Technion co-author). All v2 artifacts are under **chambul / deepset01-sys** (Shmulik Avraham).

| Resource | Link / string | License |
|--|--|--|
| Source dataset | [`GuyDor007/medisimplifier-dataset`](https://huggingface.co/datasets/GuyDor007/medisimplifier-dataset) — 9,999 samples (train 7,999 / val 999 / test 1,001), public (Claude references) | — |
| Nemotron training dataset | [`chambul/medisimplifier-nemotron-dataset`](https://huggingface.co/datasets/chambul/medisimplifier-nemotron-dataset) — 7,983 train / 995 val / 998 test (9,976 valid after teacher filtering) | CC-BY-NC-SA-4.0 (inherited; not yet on HF card) |
| Judge benchmark (v1, automated labels) | [`chambul/MedSimp-JudgeBench`](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench) — 708 samples, 4 error types, **2-judge** verdicts (Llama-3.3-70B + Qwen3-32B); Claude Opus 4.5 references. Diagnosis-drop labels are automated and ~85% mislabeled (A8) — the published card carries no such caveat. Nemotron verdicts are in this repo (`nemotron_calibration_full.json`), not on HF. | CC-BY-NC-SA-4.0 |
| Judge benchmark v2 | [`chambul/MedSimp-JudgeBench-v2`](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench-v2) — 412 items: 120 hand-verified primary-diagnosis drops + 120 paired controls (headline) + 172 supplementary controls; configs `drops` / `controls`; built by `scripts/build_hf_judgebench_v2.py` (source text joined and verified 412/412); pre-registration: `docs/judgebench_v2_protocol.md`. ⚠️ gpt-oss-120b and DeepSeek-family judges are favoured by construction (A8 threat 10) | CC-BY-NC-SA-4.0 |
| Merged Model v2 | [`chambul/MediSimplifier-OpenBioLLM-v2-merged`](https://huggingface.co/chambul/MediSimplifier-OpenBioLLM-v2-merged) — OpenBioLLM-8B v2 (base: `aaditya/Llama3-OpenBioLLM-8B`), ready for vLLM | [Llama 3 Community License](https://llama.meta.com/llama3/license/) |
| Merged Model v1 | [`chambul/MediSimplifier-OpenBioLLM-merged`](https://huggingface.co/chambul/MediSimplifier-OpenBioLLM-merged) — v1 baseline | — |
| Adapters (Technion-era) | [`GuyDor007/MediSimplifier-LoRA-Adapters`](https://huggingface.co/GuyDor007/MediSimplifier-LoRA-Adapters) | — |
| Teacher model | `nvidia/nemotron-3-super-120b-a12b` (Token Factory) | — |
| Safety judge (new) | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (Token Factory) | — |
| Safety judges (v1) | `meta-llama/Llama-3.3-70B-Instruct` · `Qwen/Qwen3-32B` — Token Factory dedicated endpoints in the current gate (`src/safety_gate.py:15-17`) | — |
| Judge-pool candidates (`/v1/audit_panel`) | `openai/gpt-oss-120b` (**v2 recommendation**) · `deepseek-ai/DeepSeek-V4-Flash-0731` · `nvidia/Nemotron-3-Ultra-550b-a55b` · `nvidia/nemotron-3-super-120b-a12b` · `google/gemma-3-27b-it` (+ Nemotron Nano) — Token Factory | — |
| Token Factory endpoint | `https://api.studio.nebius.ai/v1/` | — |
| Docker images | Training/eval/merge + Safe Endpoint v5 + CPU `audit-cpu-v2.1` → [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) | — |
| v1 project | [github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius) 🥇 | — |

> Underlying clinical notes: [Asclepius-Synthetic-Clinical-Notes](https://huggingface.co/datasets/starmpcc/Asclepius-Synthetic-Clinical-Notes) (CC-BY-NC-SA-4.0) — anonymized synthetic notes, no real patient data. CC-BY-NC-SA-4.0 restricts commercial use and requires derivatives to share under the same license.

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Future Work & Limitations

**Deployment Posture:** MediSimplifier v2 is a research prototype — not validated for clinical use. The Safe Simplification Endpoint v5 is unauthenticated demo infrastructure (as is the CPU `/v1/audit_panel` service) — do not route real patient data through it. Nemotron Super references in the training set are LLM-generated, not clinician-validated. ROUGE-L measures similarity to these LLM-generated references, not to human-expert output quality.

| Area | Limitation | Future Work |
|------|-----------|-------------|
| Teacher | Nemotron Super references not expert-reviewed | Human-expert validation of teacher quality |
| Training | No ablation on Nemotron dataset — used v1 winner config directly | Ablation study on Nemotron-taught dataset |
| Safety | Nemotron Nano over-flags clean text: 35.2% (calibration prompt) / 30.5% (gate prompt) on the 200 automated clean controls; **44.2% (53/120) on the v2 paired controls**. A substantial share reflects paraphrase-mismatch: correctly-simplified diagnoses (e.g. "leukemia" → "fast-growing blood cancer") flagged as dropped. Scoping the prompt to diagnosis drops neither costs recall nor measurably helps (pre-registered v2 re-run, 120 drops × 4 calls: ΔJ +0.046 [−0.060, +0.154], within call-to-call noise; results/vagt_loop_v2_summary.json). | Semantic grounding — verify whether the plain phrase is clinically equivalent to the technical term (medical NLI or physician judgment). On v2 (at its 50% drop share) the τ-blind permutation null confirms the lift is detection, not flag-rate (results/judgebench_v2_null_control.json); at rarer drops the over-flagging cost grows (A8 threat 11). |
| Safety | Diagnosis-drop detection measured on hand-verified (author-verified, not clinician-verified) labels: Nemotron 91.7% vs Llama 46.7% / Qwen 46.7% (v2, deployed prompt). The automated 68%/14%/7% is superseded (A8). | Physician-labeled validation: blinded 50-case sheet + merge pipeline committed (def028d, 0d75341; docs/ADJUDICATION_BRIEF.md); **no labels returned yet** (0/50). |
| VAGT | Single-seed paired bootstrap CIs for ΔΦ_V and Δκ (seed=42, 1,000 resamples, over items; over patient pairs in the scoped-gate re-run); A5's premise-test intervals are Wilson and Newcombe. The v2 benchmark's size was a pre-registered target (≥ 100 drops), not a power calculation; the scoped-gate re-run pre-registered one for its recall difference only (A8 threat 7) | On v2: per-candidate CIs (results/judgebench_v2_pool_table.json), τ-blind permutation null (results/judgebench_v2_null_control.json), patient-level split-half (results/judgebench_v2_split_half.json). No power analysis for ΔΦ_V yet; the scoped-gate primary (d_J) was underpowered for a +0.10 effect (results/vagt_loop_v2_deviations.md). |
| VAGT | v2 figures are at the stratum's 50% drop share, and Φ_V and ΔΦ_V depend on it (under the deployed prompt Nano's ΔΦ_V is +0.0066 at 20% drops; B5's small audit, taken at face value, puts the served model near 5–18% drops; A8 threat 11) | Measure the served model's real drop rate and report Φ_V at it |
| VAGT | Applied to one benchmark: 2-judge incumbent + 6 candidates, any 2+ judge panel via `/v1/audit_panel` (vagt_core generalized, 4f8688a); formal estimand developed post-v1 submission | Formal publication of the VAGT estimand; replication on a second benchmark/domain |
| Safety | The gate checks for dropped content, not added content (B8 item 6) | Addition/hallucination check |
| Benchmark | v2 rebuilt the **diagnosis** stratum only; dose/negation/lateral keep automated labels (A8) | Hand-verify the other strata |
| Benchmark | JudgeBench v2 is published (`chambul/MedSimp-JudgeBench-v2`), but the v1 card (`chambul/MedSimp-JudgeBench`) still has no label caveat (Dataset and models) | Correct the v1 card |
| Product | `/v1/audit_panel` ranks a fixed, pre-computed pool; a new judge needs its verdicts generated first | Live scoring of new judges |
| Deployment | endpoint-v5's `/v1/audit_panel` serves the earlier pool (B8 item 3) | Rebuild endpoint-v5 on the v2 pool |

**Addressed in this submission:** scale/family confound — pool experiment across 5 families and scales, confirmed on v2 (results/judgebench_v2_pool_table.json).
