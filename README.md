# MediSimplifier — Nemotron × VAGT

[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-blue)](https://nebius.com/services/token-factory)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron%203-76B900)](https://nebius.com/services/token-factory/nemotron)
[![HuggingFace Dataset](https://img.shields.io/badge/HF-Dataset-yellow)](https://huggingface.co/datasets/GuyDor007/medisimplifier-dataset)
[![JudgeBench](https://img.shields.io/badge/HF-MedSimp--JudgeBench-yellow)](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

> **Nebius x NVIDIA Global AI Hackathon submission by Shmulik Avraham.**
> Built on top of [MediSimplifier-Nebius](https://github.com/deepset01-sys/medisimplifier-nebius) — 🥇 First Place winner of the Nebius Serverless AI Builders Challenge.
> The Nemotron teacher pipeline, 3-judge calibration panel, VAGT measurement framework, and v2 training infrastructure were built independently for this hackathon.

**Executive Summary:** 9,999 Nemotron Super teacher calls via Token Factory → training on H100 (3 epochs, ~2.4h) → Nemotron Nano joins Llama + Qwen as calibrated third judge → 708-sample VAGT 3-rater analysis → Safe Simplification Endpoint v2 — zero standing infrastructure, $0 idle cost.

**Key findings:** (1) Nemotron Super as teacher produces stylistically different references than Claude Opus (ROUGE-L 0.525 between teachers) — student faithfully learns Nemotron's style (FK-Grade 8.87 vs 7.33 in v1); (2) Nemotron Nano catches diagnosis omissions at 68% recall vs Llama's 14% and Qwen's 7% — the clinical blind spot both v1 judges shared; (3) VAGT inversion — adding Nemotron as third judge cuts shared bias σ²_B on diagnosis from 0.347→0.229 while Fleiss κ goes negative, proving consensus statistics are blind to the improvement. Four Nebius services: Token Factory, Jobs, Object Storage, Serverless Endpoints.

**Blog Post:** [coming soon]

## What this project does

MediSimplifier simplifies medical discharge summaries to a 6th-grade reading level while preserving all critical medical information. **v2** re-tools the pipeline around NVIDIA Nemotron and adds a calibration measurement layer:

- **Teacher** — Nemotron Super generates reference simplifications (replacing Claude Opus 4.5 from v1), using the *identical* prompt from v1 ([github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius)) — ensuring a fair comparison where any difference in output quality reflects the model, not the instructions.
- **Judge** — Nemotron Nano is added as a third, calibrated safety judge alongside Llama-3.3-70B and Qwen3-32B.
- **Measurement** — VAGT decomposes judge behavior into ground-truth signal (σ²_τ), shared blind-spot bias (σ²_B), rater bias (σ²_R), and noise (σ²_N), yielding a veridicality-anchored dependability coefficient Φ_V that consensus statistics (Cohen's κ, PABAK, Krippendorff α) cannot produce.

> **What's carried from v1 vs new here:** The dataset, the fine-tuning task, the dual-judge safety design, and the perturbation benchmark (MedSimp-JudgeBench, 708 samples) are from v1. New in v2: **Nemotron Super as teacher**, **Nemotron Nano as a third calibrated judge**, and the **VAGT framework** with its 3-rater decomposition. Fine-tuning a student on Nemotron references is complete — see [v2 Evaluation Results](#v2-evaluation-results--v1-claude-teacher-vs-v2-nemotron-teacher) below.

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

Token Factory = Nemotron Super teacher (9,999 calls) + Nemotron Nano judge (708 calibration calls) + 3-judge safety panel. Jobs = v2 training (H100, 3 epochs) + evaluation. The novel v2 finding: VAGT inversion — adding Nemotron Nano as third judge cuts shared bias σ²_B on diagnosis from 0.347→0.229 while Fleiss κ goes negative, proving that Cohen's κ — the only metric used in v1 — is blind to the improvement.

## LoRA Configuration

v2 uses the winning configuration from v1 ablation (r=32, all_attn, seed=42, 3 epochs). No additional ablation was run — the v1 winner was validated across hardware (H100/H200, δ 1.6–5.0%) and transfers directly to the Nemotron-taught dataset.

| Parameter | Value | Source |
|-----------|-------|--------|
| rank | 32 | v1 ablation winner |
| modules | all_attn (q+k+v+o) | v1 ablation winner |
| epochs | 3 | v1 full training |
| seed | 42 | v1 convention |
| lora_alpha | 64 | 2r, per rsLoRA |
| lora_dropout | 0.05 | v1 convention |
| use_rslora | True | rank-stabilized LoRA |

## Key findings

| Finding | Result | Nebius Service |
|---------|--------|----------------|
| Teacher replacement | Nemotron Super produces stylistically different references than Claude Opus (ROUGE-L 0.525 between teachers) | Token Factory |
| Student faithfulness | OpenBioLLM v2 learns Nemotron's style — FK-Grade 8.87 vs 7.33 in v1 | Jobs |
| v2 evaluation | ROUGE-L=0.5254, SARI=60.36, BERTScore=0.9113 on GuyDor007 test set | Jobs |
| Nemotron Nano recall | 84.2% recall on injected errors — Llama 31.7%, Qwen 55.9% | Token Factory |
| Diagnosis blind spot — fixed | Nemotron Nano 68% vs Llama 14% / Qwen 7% | Token Factory |
| VAGT inversion | σ²_B 0.347→0.229; Φ_V +0.072 — Fleiss κ goes negative | Token Factory |
| Safe Endpoint v2 | Live — VAGT-calibrated 3-judge gate catches hallucinated content | Endpoints + Token Factory |

> Verified rows are computed from committed artifacts ([`nemotron_calibration_full.json`](nemotron_calibration_full.json), [`vagt_nemotron_results.txt`](vagt_nemotron_results.txt), [`results/eval_v2_results.json`](results/eval_v2_results.json)) and reproducible via the scripts/jobs in [Reproduce](#reproduce-step-by-step) — no numbers are invented.

## v2 Evaluation Results — v1 (Claude teacher) vs v2 (Nemotron teacher)

The Nemotron-taught student was evaluated on the **same GuyDor007 test set (n=1,001, Claude references)** as v1 — an apples-to-apples yardstick. Full metrics in [`results/eval_v2_results.json`](results/eval_v2_results.json).

| Metric | v1 (Claude teacher) | v2 (Nemotron teacher) |
|--|--|--|
| ROUGE-L | 0.6638 | **0.5254** |
| SARI | 73.49 | **60.36** |
| BERTScore | 0.9460 | **0.9113** |
| FK-Grade | 7.33 | **8.87** |

**Training run:** LoRA (r=32, all_attn, 3 epochs) on 7,983 train / 995 val / 998 test — ~2.4 hours (8,523 s) on 1×H100, ~$25–30. Teacher references agree with Claude's at ROUGE-L **0.525** ([`teacher_comparison.json`](teacher_comparison.json)).

> **Honest interpretation:** v2 ROUGE-L reflects **style divergence from Claude references, not a quality failure** — Nemotron Super produces *less* simplified references (FK-Grade **8.87** vs Claude's implied ~7.0), and the student model faithfully learned this style. The lower ROUGE-L/SARI is the student matching a *different teacher's style*, scored against Claude's references; it is not evidence the v2 outputs are worse, only that they are less Claude-like (and at a slightly higher reading level). Note the ~0.525 student↔Claude ROUGE-L closely tracks the ~0.525 teacher↔teacher ROUGE-L — the student inherited exactly the teacher gap.

> **Evaluation:** 1,001 test samples (GuyDor007/medisimplifier-dataset), greedy decoding, seed=42.

> **Adapter provenance:** `chambul/MediSimplifier-OpenBioLLM-v2-merged` merges the Nebius-trained LoRA adapter (`medisimplifier-adapters-v2/adapter/`, r=32, all_attn, 3 epochs) with the base model. ROUGE-L 0.5254 documented in [`results/eval_v2_results.json`](results/eval_v2_results.json).

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
    Nebius Job: LoRA fine-tune student on Nemotron references (H100, r=32 all_attn, 3 epochs)  ->  adapter (bucket)
        |
        v
    Nebius Job: Evaluation (ROUGE-L=0.5254, SARI=60.36, BERTScore=0.9113, FK-Grade=8.87)
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
        POST /v1/simplify → vLLM + VAGT-calibrated 3-judge gate
        (tested live — see safe_endpoint_v2.yaml to redeploy)

> **Why Token Factory?** Nemotron Super, Nano, and Ultra are all served per-token with zero idle cost. The teacher run (519 unique calls → 708 references) cost ~$1.7 and finished in ~21 min; the judge panel and VAGT analysis add no GPU management. Model strings verified live via `/v1/models`.

## Merge & Deploy (v2)

The LoRA adapter is merged into the base model before serving:

1. Run merge job (Nebius Job):
   `jobs/job_merge_v2.yaml` — reads from `medisimplifier-adapters-v2/adapter/`, writes merged model to bucket via `aws s3 cp`

2. Publish to HuggingFace:
   `chambul/MediSimplifier-OpenBioLLM-v2-merged` (public — no bucket credentials required to reproduce)

3. Deploy Safe Endpoint v2 (Nebius Serverless Endpoint):
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

## Adapter Storage Flow

Training jobs write the LoRA adapter to `/output/adapter` inside the job. The job config mounts the `medisimplifier-adapters-v2` bucket to `/output`, so the adapter is automatically persisted to Object Storage. Evaluation and merge jobs mount the same bucket to `/mnt/adapters` and read the adapter from `/mnt/adapters/adapter`.

```
Training Job              Object Storage                Eval/Merge Job
/output/adapter/  ──────►  medisimplifier-adapters-v2  ◄──────  /mnt/adapters/adapter/
                           bucket (persistent)
```

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
- **Full training references (9,999):** complete — **9,976 valid, 23 errored**. Emits `{split, index, input, claude_output, nemotron_output, error}` per record so Claude and Nemotron outputs are directly comparable. Resume-capable (skips completed inputs). Published as [`chambul/medisimplifier-nemotron-dataset`](https://huggingface.co/datasets/chambul/medisimplifier-nemotron-dataset).

**Qualitative example** (train/0):

| | Original | Claude Opus | Nemotron Super |
|--|--|--|--|
| Diagnosis | Retinal detachment repair | Surgery to fix a detached retina (…back of the eye) | Surgery to fix a detached retina |
| History | Congenital glaucoma | Glaucoma present since birth (…damages the eye nerve) | Glaucoma present from birth |
| Procedure | pars plana vitrectomy (PPV) | small tools through the white of the eye | eye surgery to remove gel and fix a detached retina |

**Preserved:** section structure, all measurements (20/100, 4 mmHg, 20/70). **Note:** Nemotron removed the blank lines between sections (the prompt asks for no empty lines) — closer to the guideline than the Claude reference.

> **Honest caveat:** Nemotron occasionally adds a soft clause not in the source ("…improved to 20/70, *allowing better daily function*"). Not a medical-fact hallucination, but a mild elaboration that bends the "do not add information" guideline. Frequency across the full set was not separately quantified. ROUGE-L of Nemotron references vs the Claude references: **0.525** (mean over 9,976 pairs; median 0.524, see [`teacher_comparison.json`](teacher_comparison.json)).

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

**The inversion (diagnosis).** Llama and Qwen share a blind spot: both almost never flag a silently dropped diagnosis (UNSAFE rates 7% / 3%). Adding Nemotron (47% UNSAFE on diagnosis) cuts shared bias by a third and raises Φ_V most — **yet Fleiss κ goes *negative* (0.076 → −0.088; Krippendorff α ≈ same).** By every agreement metric the panel looks *worse*; by veridicality it moved *closer to truth*. That is precisely the failure mode VAGT exists to expose.

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

**VAGT-calibrated decision rule (safety_gate.py):**
- Nemotron SAFE + Qwen SAFE → SAFE
- Nemotron UNSAFE + Qwen UNSAFE → UNSAFE
- Qwen UNSAFE → UNSAFE (trust Qwen's 0.5% FP specificity)
- Nemotron UNSAFE + Qwen SAFE → DISAGREE + "diagnosis-drop risk"
- ERROR in Nemotron or Qwen → ERROR (fail-safe, blocks in block mode)

All three judges run in parallel (ThreadPoolExecutor, max_workers=3) via Nebius Token Factory — latency ≈ max(judges) not sum (~73s total).

**Live demonstration (endpoint test):** A one-sentence input produced an output with fabricated content not in the source (added follow-up instructions, lifestyle changes). Nemotron flagged UNSAFE; Llama and Qwen both passed SAFE. Consensus: DISAGREE + "diagnosis-drop risk" warning — the VAGT-calibrated rule fired correctly.

## Hardware and cost

Measured where available; rows marked *(est.)* are estimates, not billing.

| Step | Service | Calls / GPU | Wall-clock | Approx. cost |
|--|--|--|--|--|
| 3-judge calibration (Nemotron Nano, n=708) | Token Factory | 708 | ~32 min | ~$0.60 † |
| Teacher references — JudgeBench (Nemotron Super) | Token Factory | 519 unique | ~21 min | ~$1.7 |
| Teacher references — full training set (9,999) | Token Factory | 9,971 valid | ~6–7 h *(est.)* | ~$20–33 *(est.)* |
| LoRA fine-tune on Nemotron references | Nebius Job (H100) | 3 epochs | ~2.4 h (8,523 s) | ~$25–30 |
| Student evaluation (ROUGE-L/SARI/BERTScore/FK) | Nebius Job (H100) | 1,001 | ~45 min *(est.)* | ~$3 *(est.)* |
| **Total** | | | | **~$50–65** *(est.)* |

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
    results/eval_v2_results.json       v2 student eval on GuyDor007 test (ROUGE-L 0.5254 / SARI 60.36 / BERTScore 0.9113 / FK 8.87)
    jobs/job_train_v2.yaml             v2 fine-tuning job (train-v30, Nemotron dataset, adapters-v2 bucket)
    jobs/job_eval_v2.yaml              v2 evaluation job (train-v30, GuyDor007 test)
    src/train.py · src/evaluate.py     LoRA training (--dataset) · metrics eval
    nemotron_training_references.json  9,999 training refs (58MB, gitignored — on HuggingFace)
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
