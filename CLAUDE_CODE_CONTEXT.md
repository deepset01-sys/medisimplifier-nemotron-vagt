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
  ROUGE-L Claude vs Nemotron: 0.525 (teacher_comparison.json)

PHASE 2 — Fine-tuning (RUNNING 🔄):
  Job: jobs/job_train_v2.yaml
  Image: cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:train-v29
  Digest: sha256:bbbf6df1b1649c6dbd3828de8156a55970b541e0e0549cf3839df7dc6dd457f5
  Dataset: chambul/medisimplifier-nemotron-dataset
  Bucket: medisimplifier-adapters-v2 ✅ (exists)
  Status: ~1.5/3 epochs complete

PHASE 3 — Evaluation (PENDING):
  Will run after Phase 2 completes
  Compare ROUGE-L/SARI/BERTScore/FK-Grade: v1 vs v2

PHASE 4 — Safe Endpoint v2 (PENDING)
```

---

## CRITICAL — Docker Image Lessons Learned

**train-v28 failed** — cryptography 49.0.0 broke pyOpenSSL 23.2.0
**train-v29 fix** — Dockerfile post-install step:
```dockerfile
RUN pip install --no-cache-dir cryptography==48.0.1
```
**ALWAYS** verify SSL stack after build:
```bash
docker run --rm <image> python -c "from transformers import AutoTokenizer; print('OK')"
```

---

## Nebius Token Factory — Model Strings (VERIFIED)

```python
NEMOTRON_NANO  = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
NEMOTRON_SUPER = "nvidia/nemotron-3-super-120b-a12b"
LLAMA          = "meta-llama/Llama-3.3-70B-Instruct"
QWEN           = "Qwen/Qwen3-32B"
BASE_URL       = "https://api.studio.nebius.ai/v1/"

# Nemotron Nano:  max_tokens=8000 minimum
# Nemotron Super: max_tokens=16000 required
# finish_reason=="length" = ERROR even if content non-empty
```

---

## Infrastructure Status

```
Docker image: chambul/medisimplifier:train-v29
CR path: cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:train-v29
Digest: sha256:bbbf6df1b1649c6dbd3828de8156a55970b541e0e0549cf3839df7dc6dd457f5
HF Dataset: chambul/medisimplifier-nemotron-dataset
  train=7,983 / val=995 / test=998
Bucket: medisimplifier-adapters-v2 ✅ (exists)
Project ID: project-e00g1ev2pr00wjxv40r6ga
Subnet ID: vpcsubnet-e00jsdqfjrz04ygxc0
```

---

## Nebius VM
IP: 89.169.109.22 (current session)
SSH: `ssh -i C:\Users\User\.ssh\nebius_vm ubuntu@89.169.109.22`
Note: Host key changes on restart — run `ssh-keygen -R <old-ip>` first

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

## Key Commits (v2 repo)

```
4900aa8  CLAUDE_CODE_CONTEXT.md update
09b7068  teacher_comparison.json (ROUGE-L 0.525)
c938001  job_train_v2.yaml → train-v29 digest
8af84fb  Dockerfile cryptography fix
4571a12  requirements_train.txt (reverted)
4b436ea  job_train_v2.yaml → Nebius CR path
4856464  digest-pin train-v28 (superseded by v29)
d08d669  Docker build context + job_train_v2.yaml
02af114  src/train.py --dataset arg
10cf1b6  prepare_hf_dataset.py
d603c45  compare_teachers.py
31f146a  nemotron_training_data.py
fa20d87  708 JudgeBench references
fc4e8c2  nemotron_teacher.py
fcd44cb  FINDINGS.md
7d2134e  full calibration + VAGT 3-rater
```

---

## Next Tasks (after Phase 2 completes)

1. **Get adapter from bucket:**
   Check medisimplifier-adapters-v2/output/adapter/

2. **Run evaluation job** (same pattern as v1):
   ```
   Name: medisimplifier-v2-evaluate
   Image: cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:train-v29
   Command: python evaluate.py --model openbio 
     --adapter-path /mnt/adapters/output/adapter
     --split test --output-dir /mnt/adapters/eval_v2
   Volume: medisimplifier-adapters-v2 → /mnt/adapters (rw)
   Timeout: 2h
   ```

3. **Compare results:**
   v1: ROUGE-L=0.6638, SARI=73.49, BERTScore=0.9460, FK-Grade=7.33
   v2: [TBD]

4. **Update README PLACEHOLDERs** with real numbers

5. **Safe Endpoint v2** — OpenBioLLM v2 + Nemotron Nano

---

## Working Methodology (NEVER DEVIATE)
1. Never fabricate results — zero tolerance
2. Show script before running — always
3. Estimate cost before large runs — always
4. Commit after each meaningful step
5. Check v1 repo before writing new code
6. READ CONTEXT FILES before every session
7. Pin ALL dependencies — learned from train-v28 failure
8. Verify image with import test before submitting job
