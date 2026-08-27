# MediSimplifier — Nemotron × VAGT

[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-blue)](https://nebius.com/services/token-factory)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron%203-76B900)](https://nebius.com/services/token-factory/nemotron)
[![HuggingFace Dataset](https://img.shields.io/badge/HF-Dataset-yellow)](https://huggingface.co/datasets/GuyDor007/medisimplifier-dataset)
[![JudgeBench](https://img.shields.io/badge/HF-MedSimp--JudgeBench-yellow)](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

> **v2 of [MediSimplifier](https://github.com/deepset01-sys/medisimplifier-nebius)** (🥇 First Place — Nebius Serverless AI Builders Challenge).
> This iteration replaces the proprietary teacher and the ad-hoc judge panel with **NVIDIA Nemotron** end to end, and introduces **VAGT** — a measurement framework that scores an LLM judge by agreement with *ground truth*, not agreement with other judges.

**Executive Summary:** Medical text simplification with an all-Nemotron pipeline on Nebius Token Factory — **Nemotron Super (120B-A12B)** generates reference simplifications (teacher), **Nemotron Nano (30B-A3B)** serves as a calibrated safety judge, and **VAGT (Veridicality-Anchored G-Theory)** measures judge calibration against injected-error ground truth. Headline result: on the MedSimp-JudgeBench perturbation set (n=708), Nemotron Nano catches injected errors at **84.2%** recall vs Llama-3.3-70B's 31.7% and Qwen3-32B's 55.9% — and on the hardest failure mode (silent diagnosis drop) it reaches **68%** vs 14% / 7%. Adding Nemotron as a third judge produces a **consensus-vs-veridicality inversion**: rater-agreement (Fleiss κ) goes *negative* on diagnosis while VAGT dependability (Φ_V) *rises* — the exact blind spot κ cannot see.

## What this project does

MediSimplifier simplifies medical discharge summaries to a 6th-grade reading level while preserving all critical medical information. **v2** re-tools the pipeline around NVIDIA Nemotron and adds a calibration measurement layer:

- **Teacher** — Nemotron Super generates reference simplifications (replacing Claude Opus 4.5 from v1), using the *identical* prompt from v1 ([github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius)) — ensuring a fair comparison where any difference in output quality reflects the model, not the instructions.
- **Judge** — Nemotron Nano is added as a third, calibrated safety judge alongside Llama-3.3-70B and Qwen3-32B.
- **Measurement** — VAGT decomposes judge behavior into ground-truth signal (σ²_τ), shared blind-spot bias (σ²_B), rater bias (σ²_R), and noise (σ²_N), yielding a veridicality-anchored dependability coefficient Φ_V that consensus statistics (Cohen's κ, PABAK, Krippendorff α) cannot produce.

> **What's carried from v1 vs new here:** The dataset, the fine-tuning task, the dual-judge safety design, and the perturbation benchmark (MedSimp-JudgeBench, 708 samples) are from v1. New in v2: **Nemotron Super as teacher**, **Nemotron Nano as a third calibrated judge**, and the **VAGT framework** with its 3-rater decomposition. Fine-tuning a student on Nemotron references is in progress — see [PLACEHOLDER] rows below.

## What's new in v2 (vs v1)

| | v1 (Nebius Challenge) | v2 (Nemotron × VAGT) |
|--|--|--|
| Teacher (reference generation) | Claude Opus 4.5 | **Nemotron Super** (`nemotron-3-super-120b-a12b`) |
| Safety judges | Llama-3.3-70B + Qwen3-32B | **+ Nemotron Nano** (`Nemotron-3-Nano-30B-A3B`) — 3rd, calibrated |
| Calibration measurement | Cohen's κ only | VAGT 3-rater + Nemotron Nano |
| Judge benchmark | MedSimp-JudgeBench (708, dual-judge) | Same set, **3-judge decomposition** |
| Training references | Claude Opus (9,999 records) | **Nemotron Super** (9,999 records) — `[PLACEHOLDER — run in progress]` |
| Fine-tuned student | OpenBioLLM-8B, ROUGE-L 0.6638 | `[PLACEHOLDER — Nemotron-taught student]` |
| Serving | vLLM + dual-judge guardrail | `[PLACEHOLDER — Nemotron-in-the-loop endpoint]` |

> **Note on calibration history:** PABAK, Gwet AC1, Krippendorff α, and VAGT (2-rater) were developed as part of v1's post-challenge analysis ([github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius)); v2 extends VAGT to a 3-rater panel with Nemotron Nano.

> All Nemotron inference runs on **Nebius Token Factory** (OpenAI-compatible, `https://api.studio.nebius.ai/v1/`). No standing infrastructure.

## Key findings

| Finding | Result | Status |
|--|--|--|
| Nemotron Nano judge — recall on injected errors | **84.2%** (Llama 31.7%, Qwen 55.9%) | ✅ n=708 |
| Nemotron Nano — diagnosis-drop recall (hardest mode) | **68%** (Llama 14%, Qwen 7%) | ✅ |
| Nemotron Nano — false-positive rate on clean references | **35.2%** (Llama 1.5%, Qwen 0.5%) | ✅ |
| Balanced accuracy (mean of specificity & recall) | Nemotron **74.5%** · Llama 65.1% · Qwen 77.7% | ✅ |
| VAGT inversion (diagnosis) | Fleiss κ **0.076 → −0.088** while Φ_V **0.404 → 0.476** | ✅ |
| Shared blind-spot bias reduction (diagnosis) | σ²_B **0.347 → 0.229** when Nemotron is added | ✅ |
| Nemotron Super teacher — JudgeBench references | 708 records, **0 errors**, avg 1,743 chars | ✅ |
| Nemotron Super vs Claude Opus — reference ROUGE-L | `[PLACEHOLDER]` | ⏳ |
| Nemotron Super — full training references (9,999) | `[PLACEHOLDER — run in progress]` | ⏳ |
| Nemotron-taught student — ROUGE-L / SARI / FK-Grade | `[PLACEHOLDER]` | ⏳ |

> Verified rows are computed from committed artifacts ([`nemotron_calibration_full.json`](nemotron_calibration_full.json), [`vagt_nemotron_results.txt`](vagt_nemotron_results.txt)) and reproducible via the scripts in [Reproduce](#reproduce-step-by-step). `[PLACEHOLDER]` rows depend on runs not yet complete — no numbers are invented.

## How it runs on Nebius

Every model call is a serverless Token Factory request — no reserved GPUs for the generation/judging pipeline.

Pipeline:

    Dataset (HuggingFace: GuyDor007/medisimplifier-dataset — 9,999 discharge summaries)
        |
        v
    Token Factory: Nemotron Super teacher  (nemotron_training_data.py)
        generate reference simplification per record  ->  nemotron_training_references.json
        |                                                  (claude_output + nemotron_output side by side)
        v
    [PLACEHOLDER] Nebius Job: LoRA fine-tune student on Nemotron references (H100)
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
    [PLACEHOLDER] Nebius Endpoint: Nemotron-in-the-loop Safe Simplification

> **Why Token Factory?** Nemotron Super, Nano, and Ultra are all served per-token with zero idle cost. The teacher run (519 unique calls → 708 references) cost ~$1.7 and finished in ~21 min; the judge panel and VAGT analysis add no GPU management. Model strings verified live via `/v1/models`.

## Nemotron as Teacher — the experiment

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
- **Full training references (9,999):** `[PLACEHOLDER — run in progress]`. Emits `{split, index, input, claude_output, nemotron_output, error}` per record so Claude and Nemotron outputs are directly comparable. Resume-capable (skips completed inputs).

**Qualitative example** (train/0):

| | Original | Claude Opus | Nemotron Super |
|--|--|--|--|
| Diagnosis | Retinal detachment repair | Surgery to fix a detached retina (…back of the eye) | Surgery to fix a detached retina |
| History | Congenital glaucoma | Glaucoma present since birth (…damages the eye nerve) | Glaucoma present from birth |
| Procedure | pars plana vitrectomy (PPV) | small tools through the white of the eye | eye surgery to remove gel and fix a detached retina |

**Preserved:** section structure, all measurements (20/100, 4 mmHg, 20/70). **Note:** Nemotron removed the blank lines between sections (the prompt asks for no empty lines) — closer to the guideline than the Claude reference.

> **Honest caveat:** Nemotron occasionally adds a soft clause not in the source ("…improved to 20/70, *allowing better daily function*"). Not a medical-fact hallucination, but a mild elaboration that bends the "do not add information" guideline. Frequency across the full set: `[PLACEHOLDER]`. ROUGE-L of Nemotron references against the Claude references: `[PLACEHOLDER]`.

## VAGT: When Agreement Misleads — the inversion

Consensus statistics (Cohen's κ, PABAK, Krippendorff α) measure whether judges *agree with each other*. They never measure whether judges agree with the *truth* — so they reward a shared blind spot and penalize the one judge that breaks it. **VAGT (Veridicality-Anchored G-Theory)** fixes this by anchoring to ground truth (the injected error type), decomposing each stratum into:

    consensus  c_i = mean_r X_{ir}
    shared bias b_i = c_i − τ_i ;  σ²_B = mean_i b_i² − σ²_N/R   (bias-corrected)
    rater bias  α_r = X̄_{·r} − X̄ ;  σ²_R = mean_r α_r²
    noise       ε   = X − c − α ;   σ²_N = mean ε²
    Φ_V = σ²_τ / (σ²_τ + σ²_B + (σ²_R + σ²_N)/n_r)          (higher = more dependable vs truth)

**Adding Nemotron Nano as a third rater** (n_r: 2 → 3), per injected error type (95% bootstrap point estimates, seed=42):

| Feature | Φ_V (Llama+Qwen) | Φ_V (+Nemotron) | ΔΦ_V | σ²_B (L+Q) | σ²_B (+Nemo) | Δσ²_B |
|--|--|--|--|--|--|--|
| dose | 0.743 | 0.733 | −0.010 | 0.054 | 0.047 | −0.007 |
| negation | 0.578 | 0.618 | +0.040 | 0.145 | 0.104 | −0.041 |
| lateral | 0.697 | 0.745 | +0.047 | 0.077 | 0.050 | −0.027 |
| **diagnosis** | **0.404** | **0.476** | **+0.072** | **0.347** | **0.229** | **−0.118** |

**The inversion (diagnosis).** Llama and Qwen share a blind spot: both almost never flag a silently dropped diagnosis (UNSAFE rates 7% / 3%). Adding Nemotron (47% UNSAFE on diagnosis) cuts shared bias by a third and raises Φ_V most — **yet Fleiss κ and Krippendorff α go *negative* (0.076 → −0.088).** By every agreement metric the panel looks *worse*; by veridicality it moved *closer to truth*. That is precisely the failure mode VAGT exists to expose.

> **Honest caveats:**
> - **Not a free win everywhere.** On `dose` ΔΦ_V = −0.010 (a slight loss): Llama+Qwen weren't badly blind there, so Nemotron's added rater noise outweighs the small bias gain. The panel benefits most exactly where the incumbents share a blind spot.
> - Adding a diverging rater **raises σ²_R and σ²_N** (printed per feature) — the cost side of the ledger. Φ_V nets the two effects.
> - **Complete-case:** rows where any judge returned ERROR are dropped (9–18 per feature). Counts reported in [`vagt_nemotron_results.txt`](vagt_nemotron_results.txt).
> - The VAGT framework and its formal estimand originate in v1 (`vagt_section.md`, `vagt_estimand.md`); v2 contributes the 3-rater empirical application with Nemotron.

## Medical Safety Evaluation (3 judges)

Nemotron Nano joins Llama-3.3-70B (same-family as the OpenBioLLM student) and Qwen3-32B (cross-family) as a third safety judge, all via Token Factory. Judge prompt is the v1 4-step CoT-with-anti-sycophancy prompt (`safety_eval_v2.py`), reused verbatim.

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

**Verdict distribution (n=708):** Nemotron 208 SAFE / 491 UNSAFE / 9 ERROR. Inter-judge agreement: Nemotron↔Llama 47.6% (κ=0.139), Nemotron↔Qwen 68.7% (κ=0.421).

> **Interpretation:** Nemotron Nano is a **high-sensitivity, low-specificity** judge. It catches errors the incumbents miss — dramatically so on diagnosis drops — but over-flags ~1 in 3 clean references. On *balanced* accuracy Qwen still edges ahead (77.7%) on near-perfect specificity. Nemotron is not a drop-in calibrated judge as-is; its recall edge and its over-flagging are two sides of one low threshold, and it needs threshold/prompt calibration to separate them.
> **Carried from v1:** on the free-text safety set, CoT *amplified* judge disagreement (κ 0.11 → 0.04) — see the v1 README.

## Hardware and cost

`[PLACEHOLDER — populated as runs complete]`

| Step | Service | Calls / GPU | Wall-clock | Approx. cost |
|--|--|--|--|--|
| 3-judge calibration (Nemotron Nano, n=708) | Token Factory | 708 | ~32 min | ~$0.60 † |
| Teacher references — JudgeBench (Nemotron Super) | Token Factory | 519 unique | ~21 min | ~$1.7 |
| Teacher references — full training set (9,999) | Token Factory | 9,999 | `[PLACEHOLDER]` | `[PLACEHOLDER ~$20–33]` |
| LoRA fine-tune on Nemotron references | Nebius Job (H100) | — | `[PLACEHOLDER]` | `[PLACEHOLDER]` |
| Student evaluation (ROUGE-L/SARI/BERTScore/FK) | Nebius Job (H100) | 1,001 | `[PLACEHOLDER]` | `[PLACEHOLDER]` |
| **Total** | | | | `[PLACEHOLDER]` |

> **† Judge calibration cost basis:** input tokens are *measured* — 868,486 total (mean 1,227/call), reconstructed from the exact judge prompts over the 708 records. Output tokens were **not logged** by the run; estimated at ~2.8–3.0M from the observed ~3.7–4.0k reasoning tokens/call (Nano is a reasoning model). At Nemotron Nano rates (~$0.05/1M input, ~$0.20/1M output) this gives ~$0.60. The teacher JudgeBench run (~$1.7) is likewise input-measured; Super's higher per-token rate and 16k budget dominate its cost.
> Remaining rows reflect **actual Nebius billing** once each run completes — no estimate is presented as measured.

## Reproduce step by step

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

## Project structure

    nemotron_judge_test.py         Nemotron Nano as safety judge (3-judge calibration, concurrent, checkpointed)
    vagt_nemotron_analysis.py      VAGT 3-rater decomposition (σ²_τ/σ²_B/σ²_R/σ²_N/Φ_V + Fleiss/Krippendorff, bootstrap CIs)
    nemotron_teacher.py            Nemotron Super teacher — JudgeBench references (verbatim Technion prompt)
    nemotron_training_data.py      Nemotron Super teacher — full 9,999-record training set (imports teacher prompt; resume-capable)
    nemotron_calibration_full.json 708-sample 3-judge verdicts (Llama + Qwen + Nemotron Nano)
    nemotron_references.json       708 JudgeBench reference simplifications (Nemotron Super)
    nemotron_training_references.json  9,999 training references, claude_output + nemotron_output   [PLACEHOLDER — in progress]
    vagt_nemotron_results.txt      VAGT decomposition output (per-feature, both rater sets)
    FINDINGS.md                    Full findings write-up (calibration + VAGT, with caveats)
    CLAUDE_CODE_CONTEXT.md         Implementation context (model strings, methodology, next tasks)
    requirements.txt               openai · numpy · requests · tqdm · datasets

## Dataset and models

| Resource | Link / string |
|--|--|
| Training dataset | [`GuyDor007/medisimplifier-dataset`](https://huggingface.co/datasets/GuyDor007/medisimplifier-dataset) — train 7,999 / val 999 / test 1,001 |
| Judge benchmark | [`chambul/MedSimp-JudgeBench`](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench) — 708 samples, 4 injected error types |
| Teacher model | `nvidia/nemotron-3-super-120b-a12b` (Nebius Token Factory) |
| Safety judge (new) | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| Safety judges (v1) | `meta-llama/Llama-3.3-70B-Instruct` · `Qwen/Qwen3-32B` |
| Original teacher (v1) | `claude-opus-4-5-20251101` (Anthropic) — references being replaced by Nemotron Super |
| Token Factory endpoint | `https://api.studio.nebius.ai/v1/` |
| v1 project | [github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius) 🥇 |

> Underlying clinical notes: [Asclepius-Synthetic-Clinical-Notes](https://huggingface.co/datasets/starmpcc/Asclepius-Synthetic-Clinical-Notes) (CC-BY-NC-SA-4.0) — anonymized synthetic notes, no real patient data.
> **Deployment posture:** research prototype, not clinician-validated. Nemotron references are LLM-generated, not expert-reviewed.

## License

Apache 2.0 — see [LICENSE](LICENSE).
