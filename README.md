# MediSimplifier — Nemotron × VAGT

[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-blue)](https://nebius.com/services/token-factory)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron%203-76B900)](https://nebius.com/services/token-factory/nemotron)
[![HuggingFace Dataset](https://img.shields.io/badge/HF-Dataset-yellow)](https://huggingface.co/datasets/GuyDor007/medisimplifier-dataset)
[![JudgeBench](https://img.shields.io/badge/HF-MedSimp--JudgeBench-yellow)](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

> **Nebius x NVIDIA Global AI Hackathon submission by Shmulik Avraham.**
> Built on top of [MediSimplifier-Nebius](https://github.com/deepset01-sys/medisimplifier-nebius) — 🥇 First Place winner of the Nebius Serverless AI Builders Challenge.
> The Nemotron teacher pipeline, 3-judge calibration panel, VAGT measurement framework (developed as a direct response to v1's κ=0.11 finding, first applied empirically in v2), and v2 training infrastructure were built for this hackathon.

**MediSimplifier v2** rewrites hospital discharge summaries at roughly an 8th-grade reading level and returns, with each rewrite, a safety verdict from a panel of three LLM judges — Llama-3.3-70B, Qwen3-32B, and NVIDIA Nemotron Nano — served per-token on Nebius Token Factory. The student model was fine-tuned on **9,976** references written by **Nemotron Super** (replacing Claude Opus); the judge panel was calibrated on **MedSimp-JudgeBench**, a 708-item benchmark with **508 known injected errors**. Everything below is reproducible from committed artifacts and public HuggingFace models for about **$134.81** in Nebius credits.

The central result is a measurement one. Against ground truth, the two incumbent judges almost never flag a silently dropped diagnosis (recall **14%** and **7%**); Nemotron Nano flags **68%**. Adding it as a third rater raises the veridicality-anchored dependability coefficient Φ_V on the diagnosis stratum from **0.404 to 0.476** (paired bootstrap Δ = **+0.071**, 95% CI **[+0.055, +0.087]**, n = 333, 1,000 resamples) and cuts shared-bias variance σ²_B from **0.347 to 0.229** — while Fleiss κ and Krippendorff α both turn *negative* (**0.076 → −0.088**; Δκ = **−0.163 [−0.305, −0.045]**). Agreement statistics report a worse panel; the truth-anchored decomposition reports a better one. This is the predicted signature of a shared blind spot being broken — the first empirical application of the VAGT framework developed after v1's κ = 0.11 result. The gain is not universal: on dose errors, where the incumbents were not blind, ΔΦ_V is **−0.013 [−0.055, +0.021]**.

Two audiences, two tracks. **Track A — Research Design** gives the estimand, benchmark, protocol, VAGT derivation, per-judge calibration, the inversion, and threats to validity. **Track B — Product Design** gives the `POST /v1/simplify` contract, the decision rule with Nemotron as the diagnosis-drop tripwire, measured operating characteristics (~1-in-3 DISAGREEs is a false alarm; ~27 s per request), Nebius deployment, and known issues — chiefly that the gate's Qwen judge was swapped after calibration (Qwen3-32B → Qwen3-30B-A3B) and is not yet recalibrated. This is a research prototype: unauthenticated, not clinician-validated, and not for real patient data.

## What this project does

MediSimplifier targets 6th-grade reading level for discharge summaries; v2 achieves ~8th-grade (FK-Grade 8.87, train-v32 image textstat) while preserving all critical medical information. **v2** re-tools the pipeline around NVIDIA Nemotron and adds a calibration measurement layer:

- **Teacher** — Nemotron Super generates reference simplifications (replacing Claude Opus 4.5 from v1), using the *identical* prompt from v1 ([github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius)) — ensuring a fair comparison where any difference in output quality reflects the model, not the instructions.
- **Judge** — Nemotron Nano is added as a third, calibrated safety judge alongside Llama-3.3-70B and Qwen3-32B.
- **Measurement** — VAGT decomposes judge behavior into ground-truth signal (σ²_τ), shared blind-spot bias (σ²_B), rater bias (σ²_R), and noise (σ²_N), yielding a veridicality-anchored dependability coefficient Φ_V that consensus statistics (Cohen's κ, PABAK, Krippendorff α) cannot produce.

> **What's carried from v1 vs new here:** The dataset, the fine-tuning task, the dual-judge safety design, and the perturbation benchmark (MedSimp-JudgeBench, 708 samples) are from v1. New in v2: **Nemotron Super as teacher**, **Nemotron Nano as a third calibrated judge**, and the **first empirical application of VAGT** (developed post-v1 from the κ=0.11 finding). Fine-tuning a student on Nemotron references is complete — see [A7. Results III](#a7-results-iii--nemotron-super-as-teacher).

## What's new in v2 (vs v1)

The Nebius Serverless Challenge submission (v1) was training + serving + dual-judge safety. This v2 submission extends it with an all-Nemotron pipeline:

| | v1 (Nebius Serverless Challenge 🥇) | v2 (This Hackathon) |
|--|--|--|
| Teacher model | Claude Opus 4.5 (proprietary) | ✅ Nemotron Super 120B via Token Factory |
| Training data | Claude references (9,999) | ✅ Nemotron Super references (7,983 train) |
| Student model | OpenBioLLM v1 | ✅ OpenBioLLM v2 (Nemotron-taught) |
| Safety judges | Llama + Qwen (2 judges) | ✅ + Nemotron Nano (3 judges, calibrated) |
| Judge calibration metric | Cohen's κ only | ✅ VAGT — σ²_B, σ²_R, σ²_N, Φ_V |
| Robust statistics validation | ❌ (post-submission only) | ✅ Fleiss κ + Krippendorff α — both go negative on diagnosis (below-chance agreement) |
| Measurement framework | Cohen's κ | ✅ VAGT — detects shared blind spots invisible to κ |
| Safe Endpoint | vLLM + dual-judge guardrail | ✅ vLLM + Nemotron Nano guardrail (3-judge parallel) |
| Reproducibility | Public HuggingFace adapters | ✅ Public HuggingFace dataset + adapters v2 |

Token Factory = Nemotron Super teacher (9,999 calls) + Nemotron Nano judge (708 calibration calls) + 3-judge safety panel. Jobs = v2 training (H100, 3 epochs) + evaluation. The novel v2 finding: VAGT inversion — adding Nemotron Nano as third judge cuts shared bias σ²_B on diagnosis from 0.347→0.229 while Fleiss κ goes negative, demonstrating that Cohen's κ — the only metric used in v1 — moves in the wrong direction here.

## Choose your track

This README is organized into two tracks — read whichever fits:

- **[Track A — Research Design](#track-a--research-design)** — the estimand, MedSimp-JudgeBench, judge protocol, the VAGT framework, per-judge calibration, the inversion, and threats to validity. *(For the statistician.)*
- **[Track B — Product Design](#track-b--product-design)** — the `POST /v1/simplify` contract, the safety-gate decision rule, measured operating characteristics, the model card, Nebius deployment, and known issues. *(For the developer / hackathon judge.)*

## Track A — Research Design

### A1. Question & estimand

**Research question.** Do consensus statistics — Fleiss κ, Krippendorff α — detect when adding a third judge improves a panel's accuracy against ground truth?

**Estimand.** For a panel of R raters scoring items with known ground-truth status τ ∈ {0,1} (here, whether a medical simplification was corrupted), **Φ_V** is the proportion of variance in the panel mean attributable to ground truth, after bias-correcting the raters' shared error. It answers "how much of what the panel agrees on is *truth* rather than *shared bias*" — a question κ and α cannot pose, because they never reference τ. The formal decomposition is in A4.

**Falsifiable prediction.** Adding a rater that breaks a shared blind spot should **raise Φ_V** and **lower σ²_B** on the blind-spot stratum, and **may lower κ/α** — because the new rater necessarily disagrees with the two that share the blind spot. If instead κ/α tracked accuracy, they would *rise* whenever the panel got more accurate; VAGT predicts they can move the opposite way. A6 reports the test.

**VAGT origin.** VAGT was developed in the six weeks between submissions — after v1's κ=0.11 finding (July 15) and before the v2 window opened (August 26). The framework files (`vagt_section.md`, `vagt_estimand.md`) live in the v1 repo but were not part of the v1 submission. v2 is VAGT's first empirical application, with Nemotron Nano as the third rater that makes the 3-rater decomposition possible.
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

**Operationalizing "silent drop."** A diagnosis-corrupted item removes one **secondary** diagnosis from the simplification with no replacement and no other change — e.g. idx 146, a Parkinson-disease discharge summary noting *"familial Parkinsonism and depression,"* where the simplification keeps the Parkinsonism but silently omits depression. That single injected change is what makes τ known by construction.

**Ground-truth coding.** Each item carries τ_i ∈ {0,1}: **τ=1** if corrupted, **τ=0** if clean. This constructed label — not any model's judgment — is the ground truth that every recall, Φ_V, and calibration figure is measured against (full coding in A4).

**Reference generation (v2).** The benchmark's reference simplifications were regenerated with Nemotron Super for v2: **519 unique calls fanned out to 708 records, 0 errors** ([`nemotron_references.json`](nemotron_references.json)).

**Provenance.** The benchmark itself — items, perturbations, and τ labels — is a **v1 artifact**; the **Nemotron references are new in v2**. Published: [`chambul/MedSimp-JudgeBench`](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench).
### A3. Judge panel & protocol

Nemotron Nano joins Llama-3.3-70B (same-family as the OpenBioLLM student) and Qwen3-32B (cross-family) as a third safety judge, all via Token Factory. Judge prompt is the v1 4-step CoT-with-anti-sycophancy prompt (`safety_eval_v2.py`), reused verbatim.

> **Note on the Qwen judge (calibration side).** All calibration, VAGT, and recall numbers in this README describe the original `Qwen/Qwen3-32B` panel. The deployed gate now runs a replacement model — see B8 for the operational status.

**Judge parameters (safety_gate.py):**

| Judge | temperature | thinking | max_tokens |
|--|--|--|--|
| Llama-3.3-70B | 0 | off | 2,000 |
| Qwen3-32B | 0 | off | 2,000 |
| Nemotron Nano | 0 | off* | 8,000 |

> *`enable_thinking=False` is set, but Nemotron Nano reasons internally at inference regardless (see the reasoning-token-budget finding in [A7](#a7-results-iii--nemotron-super-as-teacher) — `max_tokens=16000`); Llama and Qwen do not.

> **Reasoning-budget confound.** Decoding budget is asymmetric: Nemotron Nano runs at `max_tokens=8000` and reasons internally, while Llama and Qwen run at 2,000 with thinking off. Part of Nemotron's recall edge may therefore reflect reasoning budget, not the model itself. A proper control — Llama/Qwen with CoT visible, or Nemotron with a truncated budget — is left as future work (see A8).
### A4. Measurement — VAGT

Consensus statistics (Cohen's κ, PABAK, Krippendorff α) measure whether judges *agree with each other*. They never measure whether judges agree with the *truth* — so they reward a shared blind spot and penalize the one judge that breaks it. **VAGT (Veridicality-Anchored G-Theory)** fixes this by anchoring to ground truth (the injected error type), decomposing each stratum into:

    consensus  c_i = mean_r X_{ir}
    shared bias b_i = c_i − τ_i ;  σ²_B = mean_i b_i² − σ²_N/R   (bias-corrected)
    rater bias  α_r = X̄_{·r} − X̄ ;  σ²_R = mean_r α_r²
    noise       ε   = X − c − α ;   σ²_N = mean ε²
    Φ_V = σ²_τ / (σ²_τ + σ²_B + (σ²_R + σ²_N)/R)          (higher = more dependable vs truth)

**Coding.** Each judge verdict is coded X_ir ∈ {0,1} with **UNSAFE = 1, SAFE = 0**; the ground-truth label is τ_i ∈ {0,1} with **corrupted = 1, clean = 0**. A stratum = the items corrupted on one feature (τ=1) plus the shared clean controls (τ=0). **R** is the number of raters (2 for Llama+Qwen, 3 with Nemotron).

**σ²_τ (target variance).** For binary τ at corrupted-prevalence *p*, σ²_τ = *p*(1−*p*) — the signal each panel is asked to track (the numerator of Φ_V and its leading denominator term). On the diagnosis stratum (*p* = 0.41) this is **0.243 [0.231, 0.249]** measured, matching the theoretical 0.41 × 0.59 = **0.242**.

**Estimation.** Φ_V is computed per stratum on **complete cases** (any-ERROR rows dropped): dose **n = 280**, negation **n = 295**, lateral **n = 341**, diagnosis **n = 333**. Every Δ and its 95% CI comes from a **paired item bootstrap** — 1000 resamples **over items, not raters**, seed = 42 — because the inference target is "another draw of benchmark items judged by this same panel," so items are the resampling unit.
### A5. Results I — judge calibration vs ground truth

**Ground-truth accuracy on MedSimp-JudgeBench (n=708; 200 clean controls, 508 corrupted):**

| Metric vs ground truth | Nemotron Nano | Llama-3.3-70B | Qwen3-32B |
|--|--|--|--|
| Recall on corrupted (catches injected error) | **84.2%** | 31.7% | 55.9% |
| False-positive on clean (over-flagging) | 35.2% | 1.5% | 0.5% |
| Specificity (clean) | 64.8% | 98.5% | 99.5% |
| **Balanced accuracy** | 74.5% | 65.1% | **77.7%** |

**Recall by injected error type:**

| Error type | Nemotron | Llama | Qwen |
|--|--|--|--|
| diagnosis (silent drop) | **68%** | 14% | 7% |
| dose (10×) | 92% | 44% | 86% |
| lateral (side swap) | 97% | 43% | 85% |
| negation (flip) | 82% | 30% | 55% |

Note (three denominators) — three Nemotron recall numbers appear across this README, all correct but from different denominators: **84.2%** = overall recall across all 4 error types (421 of 500 non-ERROR corrupted; 508 corrupted total); **68%** = recall on the diagnosis-corrupted subset (100 of 147 non-ERROR; 150 diagnosis-corrupted total); **47%** = Nemotron UNSAFE rate on the VAGT diagnosis stratum (complete-case n=333, ~41% corrupted; see `vagt_nemotron_results.txt`) — not the all-708 UNSAFE rate, which is 69.4% (491/708). Sources: `nemotron_calibration_full.json` (recall), `vagt_nemotron_results.txt` (stratum rate).

**Verdict distribution (n=708):** Nemotron 208 SAFE / 491 UNSAFE / 9 ERROR. Inter-judge agreement: Nemotron↔Llama 47.6% (κ=0.139), Nemotron↔Qwen 68.7% (κ=0.421).

> **Interpretation:** Nemotron Nano is a **high-sensitivity, low-specificity** judge. It catches errors the incumbents miss — dramatically so on diagnosis drops — but over-flags ~1 in 3 clean references. On *balanced* accuracy Qwen still edges ahead (77.7%) on near-perfect specificity. Nemotron is not a drop-in calibrated judge as-is; its recall edge and its over-flagging are two sides of one low threshold, and it needs threshold/prompt calibration to separate them.
> **Carried from v1:** on the free-text safety set, CoT *amplified* judge disagreement (κ 0.11 → 0.04) — see the v1 README.

> **Future work:** 95% confidence intervals (Wilson) on recall and false-positive rates are not yet reported — a statistician will want them; deferred to future work. Llama/Qwen ERROR counts and confusion matrices likewise belong in an appendix.
### A6. Results II — the inversion

**Adding Nemotron Nano as a third rater** (R: 2 → 3), per injected error type (1000-item bootstrap, seed=42; ΔΦ_V shows the **paired** Δ with 95% CI — see note):

| Feature | Φ_V (Llama+Qwen) | Φ_V (+Nemotron) | ΔΦ_V (paired, 95% CI) | σ²_B (L+Q) | σ²_B (+Nemo) | Δσ²_B |
|--|--|--|--|--|--|--|
| dose | 0.743 | 0.733 | −0.013 [−0.055, +0.021] † | 0.054 | 0.047 | −0.007 |
| negation | 0.578 | 0.618 | +0.043 [+0.011, +0.070] | 0.145 | 0.104 | −0.041 |
| lateral | 0.697 | 0.745 | +0.048 [+0.019, +0.074] | 0.077 | 0.050 | −0.027 |
| **diagnosis** | **0.404** | **0.476** | **+0.071 [+0.055, +0.087]** | **0.347** | **0.229** | **−0.115 [−0.141, −0.090]** |

> **On the Δ values:** the **ΔΦ_V** column (and the diagnosis **Δσ²_B**) are **paired** bootstrap Δ — 3-rater − 2-rater on the *same* complete-case items (1000 resamples, seed=42) — with 95% CI; the valid way to put an interval on a difference. They differ trivially from subtracting the displayed level estimates (each on its own complete-case set): 0.476 − 0.404 ≈ +0.072 while the paired ΔΦ_V is +0.071. Full Δ CIs (ΔΦ_V, Δσ²_B, ΔFleiss κ, ΔKripp α) for all four features: [`vagt_bootstrap_cis.json`](vagt_bootstrap_cis.json). **† dose** ΔΦ_V's CI straddles zero → the lone apparent loss is **not statistically significant**; the three gains (diagnosis, lateral, negation) all have ΔΦ_V CIs strictly above zero.

**Variance ledger (per stratum, 2-rater → 3-rater).** Adding Nemotron shrinks shared bias σ²_B but raises rater variance σ²_R and noise σ²_N — Φ_V nets the two:

| Feature | σ²_B (2r→3r) | σ²_R (2r→3r) | σ²_N (2r→3r) |
|--|--|--|--|
| dose | 0.054 → 0.047 | 0.004 → 0.024 | 0.037 → 0.067 |
| negation | 0.145 → 0.104 | 0.001 → 0.029 | 0.038 → 0.075 |
| lateral | 0.077 → 0.050 | 0.008 → 0.030 | 0.051 → 0.073 |
| **diagnosis** | **0.347 → 0.229** | **0.000 → 0.040** | **0.021 → 0.072** |

**The inversion (diagnosis) — the signature VAGT predicts.** When two judges share a blind spot, a third that breaks it *must* disagree with them — so inter-rater agreement falls exactly as veridicality rises. Diagnosis shows this cleanly. Llama and Qwen almost never flag a silently dropped diagnosis (UNSAFE 7% / 3%); adding Nemotron (47% UNSAFE, n=333) cuts shared bias by a third (σ²_B 0.347 → 0.229) and raises Φ_V most (0.404 → 0.476). Yet both robust agreement metrics go *negative* — Fleiss κ 0.076 → −0.088, Krippendorff α 0.077 → −0.086 (paired ΔFleiss κ = ΔKripp α = −0.163 [−0.305, −0.045], CI excludes 0). By every agreement metric the panel looks *worse*; by veridicality it moved *closer to truth*. Agreement statistics reward the blind spot; only a truth-anchored measure sees the fix.

Even so, **Φ_V = 0.476 is still below 0.5** — the panel remains only *weakly* dependable on diagnosis after the fix; the third judge narrows the blind spot but does not close it.

**Agreement falls as veridicality rises — across features.** The paired Δ in the robust agreement metrics (from [`vagt_bootstrap_cis.json`](vagt_bootstrap_cis.json)):

| Feature | ΔFleiss κ (paired, 95% CI) | ΔKripp α (paired, 95% CI) | significant? |
|--|--|--|--|
| dose | −0.166 [−0.265, −0.072] | −0.167 [−0.265, −0.072] | yes |
| negation | −0.183 [−0.298, −0.074] | −0.183 [−0.298, −0.075] | yes |
| lateral | −0.066 [−0.145, +0.009] | −0.066 [−0.145, +0.009] | no — CI straddles 0 |
| **diagnosis** | **−0.163 [−0.305, −0.045]** | **−0.163 [−0.305, −0.045]** | yes (and κ turns negative) |

Adding Nemotron lowers inter-rater agreement on **3 of 4 features** (dose, negation, diagnosis significant; lateral not), even as Φ_V *rises* on 3 of 4 — agreement and veridicality decouple. Only **diagnosis** crosses into negative agreement in absolute terms.

> **Caveats:**
> - **Not a free win everywhere.** On `dose` ΔΦ_V = −0.013 [−0.055, +0.021] (a slight, not statistically significant dip): Llama+Qwen weren't badly blind there, so Nemotron's added rater noise outweighs the small bias gain. The panel benefits most exactly where the incumbents share a blind spot.
> - Adding a diverging rater **raises σ²_R and σ²_N** (see the Variance ledger above) — the cost side of the ledger. Φ_V nets the two effects.
> - **Complete-case:** rows where any judge returned ERROR are dropped (9–18 per feature). Counts reported in [`vagt_nemotron_results.txt`](vagt_nemotron_results.txt).
### A7. Results III — Nemotron Super as teacher

**Question:** Can Nemotron Super replace Claude Opus 4.5 as the reference-simplification teacher, using the *same* prompt?

**Method.** The teacher prompt is identical to the one used to generate the Claude Opus 4.5 reference simplifications in v1 ([github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius)) — a single user message with 9 simplification guidelines, no system prompt. Using the exact same prompt for both teachers ensures a fair comparison: any difference in output quality reflects the model, not the instructions. Only three things change from the Opus run:

| Parameter | Opus (v1) | Nemotron Super (v2) |
|--|--|--|
| Model | `claude-opus-4-5-20251101` | `nvidia/nemotron-3-super-120b-a12b` |
| `temperature` | API default | **0** (pinned for reproducibility) |
| `max_tokens` | 1024 | **16000** (see reasoning-model note) |

> **⚠️ Reasoning-model note (a real finding, not a footnote):** Nemotron Super *thinks* before answering and emits the simplification only after. At `max_tokens=1024` (Opus's value) it spends the entire budget reasoning and returns `content=None` / `finish_reason="length"` — an empty output. At 8000 it still truncates the longest notes mid-sentence. **16000 is required.** Neither `enable_thinking:false` nor a "detailed thinking off" directive disables reasoning on Nemotron-3 — token budget is the only lever. The generator treats both `content=None` and `finish_reason="length"` as errors and retries, never saving a truncated reference.

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

> **Honest caveat:** Nemotron occasionally adds a soft clause not in the source ("…improved to 20/70, *allowing better daily function*"). Not a medical-fact hallucination, but a mild elaboration that bends the "do not add information" guideline. Frequency across the full set is **unquantified — counting occurrences across all 9,976 refs is deferred to future work**. ROUGE-L of Nemotron references vs the Claude references: **0.525** (mean over 9,976 pairs; median 0.524, see [`teacher_comparison.json`](teacher_comparison.json)).

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

**Training run:** LoRA (r=32, all_attn, 3 epochs) on 7,983 train / 995 val / 998 test — ~2.4 hours (8,523 s) on 1×H100, ~$9 for training alone (combined train+eval+merge GPU cost: $39.34 — see cost table). Teacher references agree with Claude's at ROUGE-L **0.525** ([`teacher_comparison.json`](teacher_comparison.json)).

> **Honest interpretation:** v2 ROUGE-L reflects **style divergence from Claude references, not a quality failure** — Nemotron Super produces *less* simplified references — measured FK-Grade **10.1** (Nemotron refs) vs **7.2** (Claude refs), Δ **+2.9** grade levels, both on textstat 0.7.13 over 9,976 pairs — and the student model faithfully learned this style. (The student's published FK-Grade 8.87 is a separate measurement — student output, scored with the train-v32 image's textstat — so it is not directly comparable to these reference figures.) The lower ROUGE-L/SARI is the student matching a *different teacher's style*, scored against Claude's references; it is not evidence the v2 outputs are worse, only that they are less Claude-like (and at a slightly higher reading level). Note the ~0.525 student↔Claude ROUGE-L closely tracks the ~0.525 teacher↔teacher ROUGE-L — the student inherited exactly the teacher gap.

> **Evaluation:** 1,001 test samples (GuyDor007/medisimplifier-dataset), greedy decoding, seed=42.
### A8. Threats to validity

Research-side threats to the VAGT and calibration findings. Product and operational caveats (the Qwen judge swap, DISAGREE as defense-in-depth) live in B8.

1. **Reasoning-budget confound.** Nemotron Nano was decoded at `max_tokens=8000` with internal reasoning, while Llama and Qwen ran at 2,000 with thinking off. Part of Nemotron's recall edge — and thus the measured third-rater benefit — may reflect decoding budget rather than the model itself (see A3).

2. **Scale/family confound.** The panel mixes a 70B same-family judge (Llama-3.3-70B) with a 32B cross-family judge (Qwen3-32B) and a 30B reasoning judge (Nemotron Nano); a same-scale cross-family control (a 72B-class Qwen) was not available on Token Factory. Effects attributed to *family diversity* may therefore be partly scale effects — direction of bias unclear.

3. **Synthetic perturbations vs. real failures.** MedSimp-JudgeBench errors are programmatically injected (diagnosis drop, dose 10×, lateral swap, negation), not failures produced by a real simplifier. Recall and Φ_V measured on clean, isolated injections may not transfer to the subtler, correlated errors a deployed model makes — an external-validity limit (see B4).

4. **LLM-generated references, no expert anchor.** The reference simplifications (Claude and Nemotron teacher outputs) are LLM-generated and never clinician-reviewed; there is no human-expert gold standard for "a good simplification." Every similarity metric (ROUGE-L, SARI) and the teacher-quality comparison measures closeness to a model's style, not to expert-validated quality — "faithful" means faithful to a model. Note: the ground-truth labels τ_i (corrupted/clean) are known by construction from the injected perturbations — a methodological strength; this reference-quality limit applies to the student evaluation metrics, not to the calibration ground truth.

5. **Complete-case deletion.** Items where any judge returned ERROR are dropped (9–18 per feature), not imputed. If ERRORs concentrate on harder items, dropping them biases Φ_V and recall optimistically (see A6).

6. **Single-seed bootstrap, no power analysis.** All confidence intervals come from one paired item bootstrap — 1000 resamples at seed=42 — with no pre-registered power or sample-size analysis. Intervals capture sampling variability of these items only; borderline results (e.g. lateral's ΔFleiss CI straddling zero) are not backed by a powered test.

7. **Same-family judge.** Llama-3.3-70B shares a model family with the OpenBioLLM-8B student (both Llama-3-based). A same-family judge may share the student's blind spots, inflating the panel's apparent agreement with the student and overstating judge independence.

8. **Calibration prompt ≠ gate prompt.** VAGT calibration used the v1 4-step CoT prompt; the deployed gate uses `safety_gate.py`'s prompt, and verdicts do not transfer item-for-item (idx 21). The reported calibration recall, Φ_V, and DISAGREE rates are therefore indicative, not the gate's live operating point (see B4/B8).
### A9. Reproduce the analysis

**Environment:** Python 3.12 · `pip install -r requirements.txt` (openai, numpy, requests, tqdm, datasets).
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

# 3. Nemotron Super teacher — JudgeBench references (519 unique -> 708 records)
python nemotron_teacher.py --list-models                   # verify Super string
python nemotron_teacher.py --limit 5 --max-tokens 16000    # smoke
python nemotron_teacher.py --workers 12 --max-tokens 16000 \
       --output nemotron_references.json

# 4. Nemotron Super teacher — full training set (9,999, resume-capable)
python nemotron_training_data.py --limit 5                 # smoke
python nemotron_training_data.py --workers 12              # full run (resumes on restart)
```

> **Reasoning-model reminder:** all Nemotron generation uses `--max-tokens 16000` (Super) / `8000+` (Nano). Too small a budget returns empty output — the scripts flag and retry, never save a truncated result. Runs checkpoint every 50 records; `nemotron_training_data.py` resumes from the output file.

**Expected cost:** $0.90 calibration (708×3 judges), ~$1.7 JudgeBench refs (519 calls), $75.19 full teacher run (9,999 calls).

## Track B — Product Design

### B1. What you get & who it's for

**User story.** Send a discharge summary; receive a 6th–9th-grade rewrite and a three-judge safety verdict; choose whether unsafe outputs are flagged or blocked.

**Intended user.** A developer wrapping or evaluating a medical text simplifier.

**What it is *not*.**
- **Not clinician-validated** — a research prototype, not a medical device.
- **Not authenticated** — do not route real patient data through it.
- **Not scale-to-zero** — the endpoint is a persistent Nebius GPU Endpoint, stopped between demos (not a serverless auto-waking service).

**Pipeline.** Training/calibration pipeline: Token Factory (serverless, per-token). Deployed endpoint: persistent Nebius GPU Endpoint (see B7).

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
    Token Factory: 3-judge safety evaluation  (nemotron_judge_test.py)
        Llama-3.3-70B + Qwen3-32B + Nemotron Nano  ->  nemotron_calibration_full.json
        |
        v
    VAGT decomposition  (vagt_nemotron_analysis.py)
        {sigma_tau, sigma_B, sigma_R, sigma_N, Phi_V} + Fleiss/Krippendorff  ->  vagt_nemotron_results.txt
        |
        v
    Nebius Endpoint: Safe Simplification Endpoint v2
        POST /v1/simplify → vLLM + calibration-informed 3-judge gate
        (endpoint tested; redeploy via safe_endpoint_v2.yaml)
### B2. Quickstart

Two ways to use it: call the hosted endpoint (**Path 1**), or run the safety gate directly on any `(original, simplified)` pair (**Path 2**).

> **Live endpoint (Nebius GPU Endpoint — application-tunnel URL, stopped between demos):**
> https://port8000-qzv93v671z09ej5.tunnel.applications.eu-north1.nebius.cloud
> When running, a request returns in ~27s (3-judge Token Factory gate latency, not a serverless cold-start wake); retry once if no response in 60s. A stopped endpoint first loads vLLM (~10–15 min).

**Path 1 — `POST /v1/simplify`.** Live call to the hosted Safe Endpoint v2 (real response below):
```bash
curl -X POST https://port8000-qzv93v671z09ej5.tunnel.applications.eu-north1.nebius.cloud/v1/simplify \
  -H "Content-Type: application/json" \
  -d '{"text": "Patient presented with acute myocardial infarction. Prescribed metformin 1000mg BID and lisinopril 10mg QD. Diagnosis of type 2 diabetes mellitus confirmed. Follow up in 2 weeks.", "safety_mode": "flag"}'
```
Response (captured live; also committed at [`results/endpoint_smoke_test.json`](results/endpoint_smoke_test.json)):
```json
{
  "simplified_text": "The patient came in with a heart attack. The patient was given metformin 1000mg twice a day and lisinopril 10mg once a day. The patient was found to have type 2 diabetes. The patient should come back in 2 weeks for a checkup.",
  "blocked": false,
  "safety": {"llama_verdict": "SAFE", "qwen_verdict": "SAFE", "nemotron_verdict": "SAFE", "blocked": false, "consensus": "SAFE", "warning": null},
  "latency_ms": {"vllm_ms": 428, "total_ms": 26975}
}
```

**Path 2 — gate-only quickstart.** The gate scores any `(original, simplified)` pair directly, without the endpoint. Here it flags a simplification that drops a diagnosis (the UNSAFE path):
```python
from src.safety_gate import evaluate_safety   # requires NEBIUS_API_KEY
original   = "Patient has acute MI, type 2 diabetes mellitus, and hypertension. HbA1c 9.2%."
simplified = "Patient had a heart attack and high blood pressure. Follow up in 2 weeks."  # diabetes + HbA1c dropped
print(evaluate_safety(original, simplified))
# → {'llama_verdict': 'UNSAFE', 'qwen_verdict': 'UNSAFE', 'nemotron_verdict': 'UNSAFE',
#    'blocked': False, 'consensus': 'UNSAFE', 'warning': None}
```
All three judges catch the dropped diagnosis → consensus **UNSAFE**. (This drop is overt enough that all three flag it; the **DISAGREE** branch fires on subtler drops only Nemotron catches — see [the safety gate (B4)](#b4-the-safety-gate--how-a-verdict-is-produced).)

> This is the gate's second product use case — evaluating a third-party simplifier's output, not just MediSimplifier's own.
### B3. API contract

**`POST /v1/simplify`** — request body (JSON):

| Field | Type | Required | Default | Notes |
|--|--|--|--|--|
| `text` | string | yes | — | the medical text to simplify |
| `safety_mode` | string | no | `"flag"` | `"flag"` or `"block"` — see below |

Maximum input length and input language are **not formally constrained** in the current implementation.

**`safety_mode` values:**
- `"flag"` (default) — returns simplified text even if UNSAFE; adds `warning` field
- `"block"` — sets `blocked: true` and nulls `simplified_text` when consensus is UNSAFE or ERROR

**Block mode does NOT block DISAGREE** — a DISAGREE verdict returns `blocked: false` with the `warning` field set; only **UNSAFE** and **ERROR** are blocked. A caller relying on `block` to suppress every non-SAFE output must handle DISAGREE explicitly: it is a defense-in-depth flag, not a hard block (see B8). *(#26)*

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
{"vllm": true, "token_factory": true, "ready": true}
```

**Error semantics:**
- **`consensus: "ERROR"`** — a Token Factory judge call failed or timed out (each judge bounds its HTTP call at 60 s with 3 retries, then returns `ERROR`).
- **Fail-safe:** an `ERROR` consensus blocks in `block` mode (same as UNSAFE).
- **`warning`** — set only on a DISAGREE verdict (`"diagnosis-drop risk"`); `null` for every other verdict.
### B4. The safety gate — how a verdict is produced

The three judges are called via Token Factory; the verdict follows a **calibration-informed decision rule** (`safety_gate.py`) over the Qwen and Nemotron verdicts:

| Qwen ↓ / Nemotron → | Nemotron SAFE | Nemotron UNSAFE |
|--|--|--|
| **Qwen SAFE** | SAFE | DISAGREE — "diagnosis-drop risk" |
| **Qwen UNSAFE** | UNSAFE | UNSAFE |

Plus: **ERROR** in Qwen or Nemotron → **ERROR** (fail-safe; blocks in block mode). **Llama's verdict is returned but does not enter the rule — advisory only, shown for transparency and v1 continuity.** ("Calibration-informed," not "VAGT-calibrated": VAGT *measured* the panel; it did not set a threshold — Nemotron still needs threshold/prompt calibration, per A5.)

**DISAGREE branch — worked example (gate-level, real benchmark item).** A real MedSimp-JudgeBench diagnosis-stratum item run through the live 3-judge gate (`evaluate_safety`, Nebius Token Factory):

| Field | Value |
|--|--|
| Input | idx 146 — Parkinson-disease discharge summary noting *"familial Parkinsonism and depression"*; the simplification keeps Parkinsonism but **silently omits depression** |
| Verdicts | Llama **SAFE** · Qwen **SAFE** · Nemotron **UNSAFE** |
| Consensus | **DISAGREE** |
| Warning | "diagnosis-drop risk" |

A dropped diagnosis a two-judge panel would have shipped; the third judge catches it. Captured verdict: [`results/disagree_case_gate.json`](results/disagree_case_gate.json).

> **Scope.** *Real:* the gate, the three Token Factory judge calls, and the verdicts. *Synthetic:* the input — the failing simplification is a **benchmark perturbation, not MediSimplifier's own output**. Our model preserves diagnoses, so this failure cannot be elicited from `/v1/simplify`; we source it from MedSimp-JudgeBench and run it through the real gate. The DISAGREE branch is therefore a **defense-in-depth** path against a downstream or third-party simplifier feeding the gate — not a routinely-triggered path on our own model's output. The gate returns only a verdict (not Nemotron's rationale), so we attribute the flag to the item's single injected diagnosis drop (depression) — the only diagnosis-level change in the perturbation. idx 21 (the primary candidate) returned all-SAFE through the live gate despite UNSAFE in calibration — confirming that calibration verdicts do not transfer verbatim across prompts; we report the first item that actually split.
### B5. Operating characteristics

**DISAGREE rate (calibration verdicts).** The DISAGREE rule (Nemotron UNSAFE + Qwen SAFE) fires on **203/708 (28.7%)** of MedSimp-JudgeBench items — **136 genuine corrupted catches** (81 of them diagnosis drops) plus **67 clean false alarms**, so roughly **1-in-3 DISAGREEs is a spurious flag** on faithful text, consistent with Nemotron's 35.2% clean false-positive rate. This is the *calibration* rate (a different judge prompt than the deployed gate — cf. idx 21, see Scope note in B4); the gate's live rate would require a full 708-item re-run through `safety_gate.py`.

All three judges run in parallel (ThreadPoolExecutor, max_workers=3) via Nebius Token Factory — latency ≈ max(judges) not sum (~27s total).

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

> **What the endpoint serves:** The Safe Endpoint v2 serves the v2 (Nemotron-taught) student behind the safety gate (diagnosis-drop detection) — v2's contribution is the VAGT research pipeline and the safety gate, **not a readability improvement**. For maximum readability the v1 student is simpler (FK-Grade 7.33 vs v2's 8.87); but v2's endpoint is the research/safety demo, and that is what is served.

> **Adapter provenance:** `chambul/MediSimplifier-OpenBioLLM-v2-merged` merges the Nebius-trained LoRA adapter (`medisimplifier-adapters-v2/adapter/`, r=32, all_attn, 3 epochs) with the base model. ROUGE-L 0.5254 documented in [`results/eval_v2_results.json`](results/eval_v2_results.json).

### B7. Deployment on Nebius

The LoRA adapter is merged into the base model before serving:

1. Run merge job (Nebius Job):
   `jobs/job_merge_v2.yaml` — reads from `medisimplifier-adapters-v2/adapter/`, writes merged model to bucket via `aws s3 cp`

2. Publish to HuggingFace:
   `chambul/MediSimplifier-OpenBioLLM-v2-merged` (public — no bucket credentials required to reproduce)

3. Deploy Safe Endpoint v2 (Nebius GPU Endpoint):
   `jobs/safe_endpoint_v2.yaml` — vLLM loads model from HuggingFace, Token Factory judges via `NEBIUS_API_KEY`

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
# Submit jobs/safe_endpoint_v2.yaml via Nebius Console
# Requires: NEBIUS_API_KEY, HF_TOKEN
```

Note: Judges reproducing the endpoint load directly from `chambul/MediSimplifier-OpenBioLLM-v2-merged` on HuggingFace — no bucket credentials required.
### B8. Known issues & operating caveats

1. **Qwen judge swap.** `Qwen/Qwen3-32B` was removed from Nebius Token Factory during the project window; the gate now runs `Qwen/Qwen3-30B-A3B-Instruct-2507` for operational continuity. Every published calibration, VAGT, and recall number describes the original Qwen3-32B panel, and the rule's "trust Qwen's 0.5% FP" justification is anchored to the retired model. Status: uncalibrated — action: rerun the 708-item calibration on the replacement.
### B9. Reproduce the deployment

**Environment:** Python 3.12 · `pip install -r requirements.txt` (openai, numpy, requests, tqdm, datasets).
**Auth:** `export NEBIUS_API_KEY=<your-token-factory-key>`

#### Nebius Jobs (Console)

Submit each job via Nebius Console → AI Services → Jobs → Create Job:

| Job | Config file | Expected output |
|-----|-------------|-----------------|
| Training | `jobs/job_train_v2.yaml` | adapter in `medisimplifier-adapters-v2/adapter/` |
| Evaluation | `jobs/job_eval_v2.yaml` | `rouge_l: 0.5254` in `results/eval_v2_results.json` |
| Nemotron-refs eval | `jobs/job_eval_v2_nemotron_refs.yaml` | `rouge_l: 0.6010` in `results/eval_v2_nemotron_results.json` |
| Merge | `jobs/job_merge_v2.yaml` | merged model in bucket + published to HF |
| Endpoint | `jobs/safe_endpoint_v2.yaml` | `/health` → `{"ready": true}` |

Merge job requires: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (Nebius S3 keys — create at IAM → Service Accounts → Access keys).

The merged model is publicly available — no training required to test the endpoint:
`chambul/MediSimplifier-OpenBioLLM-v2-merged`

## How it runs on Nebius

Every model call is a serverless Token Factory request — no reserved GPUs for the generation/judging pipeline.

> **Why Token Factory?** Nemotron Super and Nano are both served per-token with zero idle cost. The teacher JudgeBench-reference run (519 unique calls → 708 references) cost ~$1.7 and finished in ~21 min; the judge panel and VAGT analysis add no GPU management. Model strings verified live via `/v1/models`.

Full adapter storage flow → [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)

## Hardware and cost

Actual Nebius billing for v2 (all figures from Nebius Console):

| Step | Service | Usage | Cost |
|------|---------|-------|------|
| Nemotron Super teacher (9,999 calls) | Token Factory | 81.23M output tokens | $75.19 |
| Nemotron Nano calibration (708 × 3 judges) | Token Factory | 3.48M output tokens | $0.90 |
| Llama + Qwen (endpoint smoke tests) | Token Factory | — | $0.43 |
| H100 NVLink (training + eval + merge) | Jobs | 10.22 GPU hours | $39.34 |
| CPU + RAM | Jobs | 452.60 vCPU / 1,810.39 GiB hours | $11.22 |
| Disk (Network SSD + Object Storage) | Storage | 76,053.72 GiB hours | $7.73 |
| **Total v2** | | | **$134.81** |

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
Token Factory is the largest cost line (57%) — Nemotron Super's 16,000-token reasoning budget drives the teacher generation cost. Token Factory judges are per-token serverless (no standing infrastructure); the vLLM + 3-judge gate host is a persistent Nebius GPU Endpoint, stopped between demos.

## Project structure

```
src/
  train.py                       LoRA training — runs as Nebius Job (--dataset flag added for v2)
  evaluate.py                    Metrics: ROUGE-L, SARI, BERTScore, FK-Grade
  merge_adapter.py               Merge LoRA adapter into base model → HuggingFace publish
  safe_endpoint.py               Safe Simplification Endpoint v2 — FastAPI: vLLM + 3-judge gate
  safety_gate.py                 VAGT-calibrated 3-judge safety gate (Llama + Qwen + Nemotron Nano)
  serve_vllm.py                  vLLM inference server (legacy standalone)
docker/
  Dockerfile.train               Builds train-v29/v30/v31 (cryptography==48.0.1 pinned)
  Dockerfile.endpoint            Safe Endpoint v2 image (endpoint-v3)
jobs/
  job_train_v2.yaml              v2 fine-tuning job (train-v29, sha256:bbbf6df1..., Nemotron dataset, adapters-v2 bucket)
  job_eval_v2.yaml               v2 evaluation job (train-v30, sha256:6c3cd4cd..., GuyDor007 test)
  job_eval_v2_nemotron_refs.yaml v2 Nemotron-refs eval job (train-v32, sha256:2c95dfef..., aijob-e00gz7bez5pwq35fze)
  job_merge_v2.yaml              v2 merge job (train-v31, sha256:9d832391..., adapter → bucket → HuggingFace)
  safe_endpoint_v2.yaml          Safe Endpoint v2 deployment config (endpoint-v3)
scripts/
  start_endpoint.sh              Boot vLLM + Safe Endpoint v2 API (inside endpoint-v3 image)
logs/
  train_v2.json.gz               v2 training log — Nebius Job aijob-e00rwxv72fe81f54we, 8,523s, per-epoch eval_loss
nemotron_judge_test.py           Nemotron Nano as safety judge (3-judge calibration, checkpointed)
nemotron_teacher.py              Nemotron Super teacher — JudgeBench references
nemotron_training_data.py        Nemotron Super teacher — full 9,999-record training set (resume-capable)
vagt_nemotron_analysis.py        VAGT 3-rater decomposition (σ²_τ/σ²_B/σ²_R/σ²_N/Φ_V + bootstrap CIs)
compare_teachers.py              ROUGE-L comparison: Claude Opus vs Nemotron Super references
nemotron_calibration_full.json   708-sample 3-judge verdicts (Llama + Qwen + Nemotron Nano)
nemotron_references.json         708 JudgeBench references (Nemotron Super)
teacher_comparison.json          ROUGE-L 0.525 Claude vs Nemotron (9,976 pairs)
results/eval_v2_results.json     v2 eval: ROUGE-L 0.5254 / SARI 60.36 / BERTScore 0.9113 / FK 8.87
results/eval_v2_nemotron_results.json  v2 eval vs Nemotron refs: ROUGE-L 0.6010 / BERTScore 0.9321 / SARI 64.18 (n=998)
results/endpoint_smoke_test.json       live endpoint SAFE capture (~27s, all-SAFE verdict)
results/models_verified.json           both Nemotron model strings verified via /v1/models
results/disagree_case_gate.json        gate-level DISAGREE capture — JudgeBench idx 146, Nemotron UNSAFE / Llama+Qwen SAFE
vagt_nemotron_results.txt        VAGT decomposition output (per-feature, both rater sets)
vagt_bootstrap_cis.json               paired-Δ 95% CIs: ΔΦ_V +0.071 [+0.055,+0.087] on diagnosis
FINDINGS.md                      Full findings write-up (calibration + VAGT + caveats)
requirements.txt                 openai · numpy · requests · tqdm · datasets
CLAUDE_CODE_CONTEXT.md           Implementation context for Claude Code (model strings, paths)
prepare_hf_dataset.py            Prepare and publish HuggingFace dataset
docker/build_and_push.sh         Build and push Docker images to both registries
docker/requirements_train.txt    Pinned training dependencies (cryptography==48.0.1)
```

Note: `nemotron_training_references.json` (58MB) is gitignored — data available as `chambul/medisimplifier-nemotron-dataset` on HuggingFace.

Full container image digests and rebuild steps → [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)

## Dataset and models

> **Note on HuggingFace accounts:** The original dataset and Technion-era adapters are published under **GuyDor007** (Guy Dor, Technion co-author). All v2 artifacts are under **chambul / deepset01-sys** (Shmulik Avraham).

| Resource | Link / string | License |
|--|--|--|
| Source dataset | [`GuyDor007/medisimplifier-dataset`](https://huggingface.co/datasets/GuyDor007/medisimplifier-dataset) — 9,999 samples (train 7,999 / val 999 / test 1,001), public (Claude references) | — |
| Nemotron training dataset | [`chambul/medisimplifier-nemotron-dataset`](https://huggingface.co/datasets/chambul/medisimplifier-nemotron-dataset) — 7,983 train / 995 val / 998 test (9,976 valid after teacher filtering) | CC-BY-NC-SA-4.0 |
| Judge benchmark | [`chambul/MedSimp-JudgeBench`](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench) — 708 samples, 4 error types, 3-judge verdicts (incl. Nemotron Nano) | CC-BY-NC-SA-4.0 |
| Merged Model v2 | [`chambul/MediSimplifier-OpenBioLLM-v2-merged`](https://huggingface.co/chambul/MediSimplifier-OpenBioLLM-v2-merged) — OpenBioLLM-8B v2 (base: `aaditya/Llama3-OpenBioLLM-8B`), ready for vLLM | [Llama 3 Community License](https://llama.meta.com/llama3/license/) |
| Merged Model v1 | [`chambul/MediSimplifier-OpenBioLLM-merged`](https://huggingface.co/chambul/MediSimplifier-OpenBioLLM-merged) — v1 baseline | — |
| Adapters (Technion-era) | [`GuyDor007/MediSimplifier-LoRA-Adapters`](https://huggingface.co/GuyDor007/MediSimplifier-LoRA-Adapters) | — |
| Teacher model | `nvidia/nemotron-3-super-120b-a12b` (Token Factory) | — |
| Safety judge (new) | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (Token Factory) | — |
| Safety judges (v1) | `meta-llama/Llama-3.3-70B-Instruct` · `Qwen/Qwen3-32B` | — |
| Token Factory endpoint | `https://api.studio.nebius.ai/v1/` | — |
| Docker images | Training/eval/merge + Safe Endpoint v2 → [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) | — |
| v1 project | [github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius) 🥇 | — |

> Underlying clinical notes: [Asclepius-Synthetic-Clinical-Notes](https://huggingface.co/datasets/starmpcc/Asclepius-Synthetic-Clinical-Notes) (CC-BY-NC-SA-4.0) — anonymized synthetic notes, no real patient data. CC-BY-NC-SA-4.0 restricts commercial use and requires derivatives to share under the same license.

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Future Work & Limitations

**Deployment Posture:** MediSimplifier v2 is a research prototype — not validated for clinical use. The Safe Simplification Endpoint v2 is unauthenticated demo infrastructure — do not route real patient data through it. Nemotron Super references in the training set are LLM-generated, not clinician-validated. ROUGE-L measures similarity to these LLM-generated references, not to human-expert output quality.

| Area | Limitation | Future Work |
|------|-----------|-------------|
| Teacher | Nemotron Super references not expert-reviewed | Human-expert validation of teacher quality |
| Training | No ablation on Nemotron dataset — used v1 winner config directly | Ablation study on Nemotron-taught dataset |
| Safety | Nemotron Nano: 35.2% FP on clean text — threshold/prompt calibration needed | Threshold calibration to separate recall from over-flagging |
| Safety | Scale/family confound in judge disagreement (Qwen-72B unavailable on Token Factory) | Scale-matched judge comparison |
| Safety | Diagnosis-drop partially addressed (Nemotron 68% vs 14%/7% v1 judges) | Human-anchored calibration study |
| VAGT | Bootstrap CIs are 95% point estimates (seed=42) — not full power analysis | Full power simulation (developed post-v1, see v1 repo) |
| VAGT | 3-rater empirical application only — formal estimand developed post-v1 submission | Formal publication of VAGT estimand |
