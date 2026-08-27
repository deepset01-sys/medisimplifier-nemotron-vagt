# MediSimplifier v2 — Claude Code Context
## For Implementation & Code
## Last updated: August 27, 2026

---

## Active Repo (v2)
`C:\Users\User\Desktop\medisimplifier-nemotron-vagt`
`github.com/deepset01-sys/medisimplifier-nemotron-vagt`

## Reference Repo (v1 — PRIMARY REFERENCE)
`C:\Users\User\Desktop\assignment_01\medisimplifier-nebius`
`github.com/deepset01-sys/medisimplifier-nebius`

**Always check v1 repo first before writing new code.**

---

## v2 Architecture

```
PHASE 1 — Teacher Data Generation (IN PROGRESS):
  GuyDor007/medisimplifier-dataset (9,999 records)
  → Nemotron Super (Token Factory)
  → nemotron_training_references.json
    {split, index, input, claude_output, nemotron_output, error}

PHASE 2 — Fine-tuning (PENDING):
  nemotron_output from Phase 1
  → Nebius Job (H100 NVLink)
  → LoRA r=32, all_attn, 3 epochs (same as v1)
  → OpenBioLLM-8B v2 adapter → Object Storage

PHASE 3 — Evaluation (PARTIAL):
  JudgeBench 708 → OpenBioLLM v1 vs v2 (ROUGE-L)
  → 3 judges: Llama + Qwen + Nemotron Nano
  → VAGT 3-rater decomposition

PHASE 4 — Safe Endpoint v2 (PENDING):
  OpenBioLLM v2 + Nemotron Nano safety gate
  → Nebius Serverless Endpoint
```

---

## Nebius Token Factory — Model Strings (VERIFIED)

```python
NEMOTRON_NANO  = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
NEMOTRON_SUPER = "nvidia/nemotron-3-super-120b-a12b"
NEMOTRON_ULTRA = "nvidia/Nemotron-3-Ultra-550b-a55b"
LLAMA          = "meta-llama/Llama-3.3-70B-Instruct"
QWEN           = "Qwen/Qwen3-32B"

BASE_URL = "https://api.studio.nebius.ai/v1/"

# CRITICAL: Nemotron is a reasoning model
# Nemotron Nano:  max_tokens=8000 minimum
# Nemotron Super: max_tokens=16000 required
# enable_thinking: False does NOT work
# Truncation guard: treat finish_reason=="length" as ERROR even if content non-empty
```

---

## Key Data Files

### v1 repo:
```
results/nebius_evidence/
  calibration_verdicts.json      # 708 samples, Llama+Qwen verdicts (no-CoT)
  calibration_verdicts_cot.json  # 708 samples, CoT condition
  safety_results_v2.json         # 1001 samples, dual-judge
  safety_results_v3.json         # 1001 samples, CoT condition

# Root level (v1):
vagt_section.md                  # VAGT framework
vagt_estimand.md                 # Formal generative model
vagt_medsimplifier_demo.py       # Empirical validation
calculate_kappa_ci.py            # Bootstrap CI
calibration_judge_cot.py         # CoT accuracy run
power_simulation_v7.py           # RQ4 power simulation
```

### v2 repo:
```
nemotron_calibration_full.json   # 708 samples, Nemotron Nano verdicts
nemotron_references.json         # 708 JudgeBench references (Nemotron Super)
nemotron_training_references.json # 9,999 training refs (IN PROGRESS)
vagt_nemotron_results.txt        # VAGT 3-rater analysis
FINDINGS.md                      # All key findings
compare_teachers.py              # ROUGE-L Claude vs Nemotron (ready to run)
```

---

## Current Run (IN PROGRESS)
**Background ID:** b8gfgj1tg
**Script:** nemotron_training_data.py
**Task:** 9,999 records → nemotron_training_references.json
**Status:** Running (~6-8 hours total, resume-capable)

**When complete:**
1. Report: total records, errors, avg length
2. Run: python compare_teachers.py
3. Commit: nemotron_training_references.json + teacher_comparison.json

---

## v1 LoRA Config (use same for v2)
```python
peft_config = LoraConfig(
    r=32,
    lora_alpha=64,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    use_rslora=True,
)
# Epochs: 3, Batch: 4 (grad_accum=4), LR: 2e-4 cosine
# Platform: gpu-h100-sxm, 1gpu-16vcpu-200gb, 250Gi disk
```

---

## Git Identity (v2 repo)
```
user.name  = deepset01-sys
user.email = deepset01@gmail.com
```

---

## Working Methodology (NEVER DEVIATE)
1. Never fabricate results — zero tolerance
2. Show script before running — always
3. Estimate cost before large runs — always
4. Commit after each meaningful step
5. Check v1 repo before writing new code
6. Parallel workers (12 default) for Token Factory
7. Checkpoint every 50 records
8. max_tokens=16000 for Super, 8000+ for Nano
9. Truncation guard: finish_reason=="length" = ERROR

---

## Key Findings (for context)

### v1 Findings (post-challenge research):
- CoT: κ=0.1114→0.0431, Δκ=0.0682, p<0.0001
- VAGT: PABAK=0.827 vs Φ_V=0.404 on diagnosis (inversion)
- σ²_B=0.347 diagnosis no-CoT

### v2 Findings (so far):
- Nemotron Nano: recall=84.2%, FP=35.2%, balanced_acc=74.5%
- Diagnosis: Nemotron 68% vs Llama 14% vs Qwen 7%
- VAGT 3-rater: σ²_B 0.347→0.229, Φ_V +0.072
- Fleiss κ goes negative while VAGT improves — inversion confirmed
- Nemotron Super: avg 1,743 chars, 0 errors on 708 references

---

## Next Tasks (in order)

1. **Wait for run completion** (b8gfgj1tg)
   - Commit nemotron_training_references.json
   - Run compare_teachers.py

2. **Build Nebius Job for fine-tuning**
   - Same LoRA config as v1
   - Input: nemotron_output from training references
   - Reference: v1 repo jobs/ folder

3. **Evaluate v2 model**
   - ROUGE-L on JudgeBench: v1 vs v2
   - 3-judge safety panel
   - VAGT analysis

4. **Safe Endpoint v2**
   - OpenBioLLM v2 + Nemotron Nano
   - Nebius Serverless Endpoint

5. **Demo video** (< 3 min, YouTube)

---

## Hackathon Requirements
- Track: Best Apps and Agents
- Must use: NVIDIA Nemotron + Token Factory
- Deadline: October 30, 2026
- License: Apache 2.0 ✅
- Public repo ✅
- Demo video: < 3 min, YouTube
- Working demo URL required
- "What was significantly updated" section needed
