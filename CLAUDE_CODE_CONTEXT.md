# MediSimplifier v2 — Claude Code Context
## For Implementation & Code
## Last updated: August 28, 2026

---

## Active Repo (v2)
`C:\Users\User\Desktop\medisimplifier-nemotron-vagt`
`github.com/deepset01-sys/medisimplifier-nemotron-vagt`

## Reference Repo (v1 — PRIMARY REFERENCE)
`C:\Users\User\Desktop\assignment_01\medisimplifier-nebius`
`github.com/deepset01-sys/medisimplifier-nebius`

---

## v2 Architecture Status

```
PHASE 1 — Teacher Data Generation (COMPLETE ✅):
  nemotron_training_references.json (9,999 records, 23 errors)
  chambul/medisimplifier-nemotron-dataset on HuggingFace ✅
  ROUGE-L Claude vs Nemotron: 0.525

PHASE 2 — Fine-tuning (NEXT 🔜):
  Job: jobs/job_train_v2.yaml
  Image: chambul/medisimplifier:train-v28@sha256:b34dca7f...
  Dataset: chambul/medisimplifier-nemotron-dataset
  Bucket: medisimplifier-adapters-v2 ← MUST CREATE FIRST

PHASE 3 — Evaluation (PARTIAL ✅):
  nemotron_calibration_full.json (708 samples, Nemotron Nano)
  vagt_nemotron_results.txt (3-rater VAGT)

PHASE 4 — Safe Endpoint v2 (PENDING)
```

---

## Nebius Token Factory — Model Strings (VERIFIED)

```python
NEMOTRON_NANO  = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
NEMOTRON_SUPER = "nvidia/nemotron-3-super-120b-a12b"
LLAMA          = "meta-llama/Llama-3.3-70B-Instruct"
QWEN           = "Qwen/Qwen3-32B"
BASE_URL       = "https://api.studio.nebius.ai/v1/"

# CRITICAL: Reasoning model token budgets:
# Nemotron Nano:  max_tokens=8000 minimum
# Nemotron Super: max_tokens=16000 required
# finish_reason=="length" = ERROR even if content non-empty
```

---

## Infrastructure Status

```
Docker image: chambul/medisimplifier:train-v28
Digest: sha256:b34dca7f8ac70ab57dc0c83cdc7b1cb408b16f518b8d1b896870caf93a56a777
HF Dataset: chambul/medisimplifier-nemotron-dataset
  train=7,983 / val=995 / test=998
  columns: instruction, input, output (GuyDor007-compatible)
  
Bucket needed: medisimplifier-adapters-v2 ← CREATE BEFORE JOB
Job YAML: jobs/job_train_v2.yaml ✅
```

---

## Nebius VM
IP: 89.169.110.156
SSH: `ssh -i C:\Users\User\.ssh\nebius_vm ubuntu@89.169.110.156`
Usage: Docker builds only (no Docker locally)

---

## v1 LoRA Config (identical for v2)
```python
LoraConfig(
    r=32, lora_alpha=64,
    target_modules=["q_proj","k_proj","v_proj","o_proj"],
    lora_dropout=0.05, bias="none",
    task_type="CAUSAL_LM", use_rslora=True
)
# Epochs: 3, Batch: 4 (grad_accum=4), LR: 2e-4 cosine
# Platform: gpu-h100-sxm, 1gpu-16vcpu-200gb, 250Gi disk
# save_safetensors=False (FUSE bucket incompatibility)
```

---

## Key Data Files

### v1 repo:
```
results/nebius_evidence/
  calibration_verdicts.json      # 708 samples, Llama+Qwen no-CoT
  calibration_verdicts_cot.json  # CoT condition
vagt_section.md, vagt_estimand.md, vagt_medsimplifier_demo.py
calculate_kappa_ci.py, calibration_judge_cot.py
power_simulation_v7.py
```

### v2 repo:
```
nemotron_calibration_full.json        # 708 samples, Nemotron Nano
nemotron_references.json              # 708 JudgeBench Nemotron refs
nemotron_training_references.json     # 9,999 training refs ✅
teacher_comparison.json               # ROUGE-L 0.525
vagt_nemotron_results.txt             # VAGT 3-rater analysis
FINDINGS.md                           # All findings
src/train.py                          # train with --dataset arg
docker/Dockerfile.train               # v2 Docker build
docker/requirements_train.txt         # Training deps
docker/build_and_push.sh             # Build script (needs VM)
jobs/job_train_v2.yaml               # Training job (digest-pinned)
compare_teachers.py                   # ROUGE-L comparison
prepare_hf_dataset.py                 # HF dataset builder
```

---

## Next Tasks (in order)

1. **Security** (URGENT):
   - Rotate Nebius API key
   - Rotate HuggingFace token

2. **Create bucket** on Nebius:
   ```
   nebius storage bucket create \
     --name medisimplifier-adapters-v2 \
     --parent-id ${NEBIUS_PROJECT_ID}
   ```

3. **Commit pending artifacts**:
   ```
   git add nemotron_training_references.json teacher_comparison.json
   git commit -m "feat: 9,999 Nemotron training references + ROUGE-L 0.525 vs Claude"
   git push
   ```

4. **Submit training job**:
   ```
   nebius ai job create --config jobs/job_train_v2.yaml
   ```

5. **After training**:
   - Evaluate v2 vs v1 (ROUGE-L, SARI, BERTScore, FK-Grade)
   - 3-judge safety panel
   - VAGT analysis
   - Safe Endpoint v2
   - Update README PLACEHOLDERs

6. **Demo video** (< 3 min, YouTube)

---

## Working Methodology (NEVER DEVIATE)
1. Never fabricate results — zero tolerance
2. Show script before running — always
3. Estimate cost before large runs — always
4. Commit after each meaningful step
5. Check v1 repo before writing new code
6. Parallel workers (12) for Token Factory
7. Checkpoint every 50 records
8. max_tokens=16000 for Super, 8000+ for Nano

---

## Git Identity
```
user.name  = deepset01-sys
user.email = deepset01@gmail.com
```
