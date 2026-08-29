# MediSimplifier v2 — Claude Code Context
## For Implementation & Code
## Last updated: August 29, 2026

---

## ⚠️ READ FIRST — CRITICAL RULES

1. **Read v1 repo + blog post BEFORE building anything**
   `C:\Users\User\Desktop\assignment_01\medisimplifier-nebius\`
   Blog: `BLOG_POST_MEDIUM.md` in v1 repo

2. **Pin ALL dependencies** — cryptography drift broke train-v28
   Always add: `RUN pip install --no-cache-dir cryptography==48.0.1`

3. **Adapter/bucket path — VERIFIED:**
   Training writes: `/output/adapter/` → bucket root `adapter/`
   Eval reads: `--adapter-path /mnt/adapters/adapter`
   NEVER write `/mnt/adapters/output/adapter`

4. **Never fabricate costs** — get actual billing from Nebius console

5. **Test image BEFORE submitting job:**
   `docker run --rm <image> python -c "from transformers import AutoTokenizer; print('OK')"`

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
  chambul/medisimplifier-nemotron-dataset ✅
  ROUGE-L Claude vs Nemotron: 0.525

PHASE 2 — Fine-tuning (COMPLETE ✅):
  Image: train-v29 (cryptography==48.0.1 pinned)
  Adapter: medisimplifier-adapters-v2/adapter/
  train_loss=0.780, eval_loss=0.861, epochs=3

PHASE 3 — Evaluation (COMPLETE ✅):
  Image: train-v30 (has evaluate.py)
  ROUGE-L=0.5254, SARI=60.36, BERTScore=0.9113, FK-Grade=8.87
  Results: results/eval_v2_results.json

PHASE 4 — Safe Endpoint v2 (IN PROGRESS 🔄):
  Code: ALL FILES UPDATED ✅
  Pending: merge job → HF publish → build image → deploy
```

---

## Safe Endpoint v2 — File Status

| File | Status | Key change |
|------|--------|------------|
| src/safety_gate.py | ✅ 81b8b5c | 3-judge parallel + VAGT rule |
| src/merge_adapter.py | ✅ a004b78 | v2 adapter path + bucket |
| src/safe_endpoint.py | ✅ e41fcfe | v2 model + version 2.0 |
| scripts/start_endpoint.sh | ✅ 82763ee | v2 model |
| docker/Dockerfile.endpoint | ✅ 5bdd795 | copied from v1 |
| src/serve_vllm.py | ✅ 5bdd795 | copied (legacy, not in endpoint path) |

**Target HF model:** `chambul/MediSimplifier-OpenBioLLM-v2-merged` (NOT YET PUBLISHED)

---

## Next Steps for Endpoint v2

1. **Merge job** — run as Nebius Job:
   ```
   Name: medisimplifier-v2-merge
   Image: train-v30 (has merge_adapter.py)
   Command: python merge_adapter.py --model openbio
   Volume: medisimplifier-adapters-v2 → /mnt/adapters rw
   Env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (Nebius S3 keys)
        HF_TOKEN, HF_HOME=/tmp/hf_cache
   ```
   Output: /tmp/merged_openbio_v2 → uploaded to bucket

2. **Publish to HF:**
   Push merged model to `chambul/MediSimplifier-OpenBioLLM-v2-merged`

3. **Build endpoint image:**
   Dockerfile.endpoint → chambul/medisimplifier:endpoint-v2
   (needs VM + Docker)

4. **Deploy Nebius Endpoint**

5. **Smoke test Nemotron judge** at max_tokens=8000

---

## Docker Images

```
train-v28: BROKEN — cryptography 49.0.0 drift
train-v29: ✅ training (cryptography==48.0.1 fixed)
train-v30: ✅ training + evaluate.py
CR: cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:<tag>
DH: chambul/medisimplifier:<tag>
train-v29 digest: sha256:bbbf6df1...
train-v30 digest: sha256:6c3cd4cd...
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

## Infrastructure

```
Project ID: project-e00g1ev2pr00wjxv40r6ga
Subnet ID: vpcsubnet-e00jsdqfjrz04ygxc0
Bucket v2: medisimplifier-adapters-v2
HF Dataset: chambul/medisimplifier-nemotron-dataset
```

## Nebius VM
SSH: `ssh -i C:\Users\User\.ssh\nebius_vm ubuntu@<IP>`
Note: Host key changes on restart — run `ssh-keygen -R <old-ip>` first

---

## v1 LoRA Config (identical for v2)
```python
LoraConfig(r=32, lora_alpha=64,
    target_modules=["q_proj","k_proj","v_proj","o_proj"],
    lora_dropout=0.05, bias="none",
    task_type="CAUSAL_LM", use_rslora=True)
# Epochs: 3, seed=42
# save_safetensors=False (FUSE bucket — training only)
# merge_adapter.py uses safe_serialization=True (writes to /tmp first)
```

---

## Key Commits (v2 repo)

```
82763ee  start_endpoint.sh v2 model
e41fcfe  safe_endpoint.py v2
a004b78  merge_adapter.py v2 defaults
81b8b5c  safety_gate.py 3-judge parallel + VAGT
5bdd795  endpoint files copied from v1
976b87e  README opening (hackathon header, executive summary)
501ebfe  eval results + README updated
85bf26c  job_eval_v2.yaml
de1d6b1  evaluate.py added
8af84fb  Dockerfile cryptography fix
c938001  job_train_v2.yaml → train-v29
fcd44cb  FINDINGS.md
7d2134e  full calibration + VAGT 3-rater
```

---

## Working Methodology (NEVER DEVIATE)
1. Never fabricate results or costs — zero tolerance
2. Read CONTEXT FILES at start of every session
3. Check v1 repo + blog post before building
4. Show script before running — always
5. Verify bucket paths from actual listing
6. Pin ALL dependencies in Docker
7. Test image with import check before submitting job
8. Commit after each meaningful step
