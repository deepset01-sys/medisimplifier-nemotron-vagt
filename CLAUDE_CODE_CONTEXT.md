# MediSimplifier v2 — Claude Code Context
## For Implementation & Code
## Last updated: August 29, 2026

---

## ⚠️ READ FIRST — CRITICAL RULES

1. **Read v1 repo + blog post BEFORE building anything**
   `C:\Users\User\Desktop\assignment_01\medisimplifier-nebius\`
   Blog: `BLOG_POST_MEDIUM.md` in v1 repo

2. **Pin ALL dependencies** — cryptography drift broke train-v28
   Always: `RUN pip install --no-cache-dir cryptography==48.0.1`

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

## v2 Pipeline — ALL PHASES COMPLETE ✅

```
PHASE 1 — Teacher (COMPLETE ✅)
PHASE 2 — Fine-tuning (COMPLETE ✅)
PHASE 3 — Evaluation (COMPLETE ✅)
PHASE 4 — Safe Endpoint v2 (COMPLETE ✅ LIVE)
```

---

## Live Endpoint

```
URL: https://port8000-qzv93v671z09ej5.tunnel.applications.eu-north1.nebius.cloud
Health: GET /health → {"vllm": true, "token_factory": true, "ready": true}
Simplify: POST /v1/simplify
  body: {"text": "...", "safety_mode": "flag"|"block"}
  response: {simplified_text, llama_verdict, qwen_verdict, 
             nemotron_verdict, consensus, warning, blocked, latency_ms}
```

---

## Docker Images

```
train-v28: BROKEN — cryptography 49.0.0 drift
train-v29: ✅ training (cryptography==48.0.1 fixed)
train-v30: ✅ training + evaluate.py
train-v31: ✅ training + evaluate.py + endpoint files
endpoint-v3: ✅ Safe Endpoint v2 (vLLM + 3-judge gate)

CR: cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:<tag>
DH: chambul/medisimplifier:<tag>

train-v29 digest: sha256:bbbf6df1...
train-v30 digest: sha256:6c3cd4cd...
train-v31 digest: sha256:9d832391...
endpoint-v3 digest: sha256:9d950d83...
```

---

## HuggingFace Assets

```
Dataset: chambul/medisimplifier-nemotron-dataset (public)
  train=7,983 / val=995 / test=998
  columns: instruction, input, output

Model (v1): chambul/MediSimplifier-OpenBioLLM-merged
Model (v2): chambul/MediSimplifier-OpenBioLLM-v2-merged (public)
JudgeBench: chambul/MedSimp-JudgeBench (708 samples)
```

---

## Infrastructure

```
Project ID: project-e00g1ev2pr00wjxv40r6ga
Subnet ID: vpcsubnet-e00jsdqfjrz04ygxc0
Bucket v2: medisimplifier-adapters-v2
  adapter/          ← v2 LoRA adapter
  merged_openbio_v2/ ← merged model (also on HF)
  eval_v2/          ← evaluation results
```

## Nebius VM
SSH: `ssh -i C:\Users\User\.ssh\nebius_vm ubuntu@<IP>`
Note: Host key changes on restart — run `ssh-keygen -R <old-ip>` first

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

## Safe Endpoint v2 — Decision Rule (VAGT-informed)

```python
# Nemotron: recall=84.2%, FP=35.2%
# Qwen: recall=55.9%, FP=0.5%
# Llama: recall=31.7%, FP=1.5% (informational only)

if nemotron=="SAFE" and qwen=="SAFE": → SAFE
if nemotron=="UNSAFE" and qwen=="UNSAFE": → UNSAFE
if qwen=="UNSAFE": → UNSAFE
if nemotron=="UNSAFE" and qwen=="SAFE":
    → DISAGREE + "diagnosis-drop risk"
elif "ERROR" in (nemotron, qwen): → ERROR
else: → DISAGREE

# Parallel calls: ThreadPoolExecutor(max_workers=3)
# Latency: ~73s (dominated by Nemotron reasoning)
```

---

## Key Commits (v2 repo)

```
1fb8381  README — endpoint live, four services
462c89f  safe_endpoint_v2.yaml
bd57c3e  job_merge_v2.yaml
82763ee  start_endpoint.sh v2
e41fcfe  safe_endpoint.py v2
a004b78  merge_adapter.py v2
81b8b5c  safety_gate.py 3-judge parallel + VAGT
5bdd795  endpoint files from v1
976b87e  README opening
501ebfe  eval results + README
85bf26c  job_eval_v2.yaml
de1d6b1  evaluate.py
8af84fb  Dockerfile cryptography fix
c938001  job_train_v2.yaml → train-v29
fcd44cb  FINDINGS.md
7d2134e  full calibration + VAGT 3-rater
```

---

## Next Tasks

1. **VAGT integration** — bring from v1:
   vagt_section.md, vagt_estimand.md,
   vagt_medsimplifier_demo.py, calculate_kappa_ci.py,
   calibration_judge_cot.py, power_simulation_v7.py

2. **README remaining sections:**
   - How it runs (pipeline diagram)
   - Hardware and cost (real numbers)
   - Reproduce step by step
   - Project structure

3. **Demo video** (< 3 min, YouTube)

4. **Devpost submission** — complete all fields

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
