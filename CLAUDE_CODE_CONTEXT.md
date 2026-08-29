# CLAUDE CODE CONTEXT — MediSimplifier v2
# Nebius x NVIDIA Global AI Hackathon
# Last updated: 2026-08-29 (Session: README complete)

## WORKING METHODOLOGY
1. Always slow and methodical
2. Never fabricate results or numbers — zero tolerance
3. Show diff before committing — always
4. Commit after each meaningful step
5. Pin ALL dependencies in Docker images
6. Verify paths from actual file listing
7. Never commit without verification

---

## PROJECT

**Repo:** github.com/deepset01-sys/medisimplifier-nemotron-vagt
**Local:** C:\Users\User\Desktop\medisimplifier-nemotron-vagt\
**Deadline:** October 30, 2026
**Track:** Best Apps and Agents
**Prize:** $20,000

---

## KEY NUMBERS (ALL VERIFIED)

| Metric | Value | Source |
|--------|-------|--------|
| ROUGE-L v2 | 0.5254 | results/eval_v2_results.json |
| SARI v2 | 60.36 | results/eval_v2_results.json |
| BERTScore v2 | 0.9113 | results/eval_v2_results.json |
| FK-Grade v2 | 8.87 | results/eval_v2_results.json |
| Teacher ROUGE-L | 0.525 | teacher_comparison.json |
| n_samples eval | 1,001 | results/eval_v2_results.json |
| Training samples | 7,983 | chambul/medisimplifier-nemotron-dataset |
| Total cost v2 | $110.41 | Nebius Console actual billing |
| H100 hours | 5.55 | Nebius Console |
| Nemotron Super cost | $75.19 | Nebius Console Token Factory |
| Nemotron Nano cost | $0.90 | Nebius Console Token Factory |

---

## VAGT RESULTS (from vagt_nemotron_results.txt)

| Feature | Φ_V (L+Q) | Φ_V (+Nemo) | ΔΦ_V | σ²_B (L+Q) | σ²_B (+Nemo) | Δσ²_B |
|---------|-----------|-------------|------|------------|--------------|-------|
| dose | 0.743 | 0.733 | −0.010 | 0.054 | 0.047 | −0.007 |
| negation | 0.578 | 0.618 | +0.040 | 0.145 | 0.104 | −0.041 |
| lateral | 0.697 | 0.745 | +0.047 | 0.077 | 0.050 | −0.027 |
| diagnosis | 0.404 | 0.476 | +0.072 | 0.347 | 0.229 | −0.118 |

Fleiss κ on diagnosis: 0.076 → −0.088 (Krippendorff α ≈ same)

---

## NEMOTRON CALIBRATION (from nemotron_calibration_full.json, n=708)

| Judge | Recall | FP Rate | Balanced Acc |
|-------|--------|---------|--------------|
| Nemotron Nano | 84.2% | 35.2% | 74.5% |
| Llama-3.3-70B | 31.7% | 1.5% | 65.1% |
| Qwen3-32B | 55.9% | 0.5% | 77.7% |

Nemotron diagnosis recall: 68% vs Llama 14% / Qwen 7%

---

## INFRASTRUCTURE

```
Project ID: project-e00g1ev2pr00wjxv40r6ga
Subnet ID: vpcsubnet-e00jsdqfjrz04ygxc0
Bucket v2: medisimplifier-adapters-v2
  adapter/              → v2 LoRA adapter
  merged_openbio_v2/    → merged model
  eval_v2/              → evaluation results
CR path: cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:<tag>
```

---

## DOCKER IMAGES

| Tag | Digest | Purpose |
|-----|--------|---------|
| train-v31 | sha256:9d832391... | training + eval + merge |
| endpoint-v3 | sha256:9d950d83... | Safe Endpoint v2 |

**Critical:** cryptography==48.0.1 pinned via post-install step in Dockerfile.train

---

## MODELS

| Model | String | Purpose |
|-------|--------|---------|
| Nemotron Super | nvidia/nemotron-3-super-120b-a12b | Teacher |
| Nemotron Nano | nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B | Safety judge |
| Llama | meta-llama/Llama-3.3-70B-Instruct | Safety judge |
| Qwen | Qwen/Qwen3-32B | Safety judge |
| Base model | aaditya/Llama3-OpenBioLLM-8B | Student (gated — requires HF access) |
| Token Factory base URL | https://api.studio.nebius.ai/v1/ | |

---

## SAFE ENDPOINT v2 DECISION RULE (safety_gate.py)

```python
if nemotron=="SAFE" and qwen=="SAFE": → SAFE
if nemotron=="UNSAFE" and qwen=="UNSAFE": → UNSAFE
if qwen=="UNSAFE": → UNSAFE  # trust 0.5% FP specificity
if nemotron=="UNSAFE" and qwen=="SAFE": → DISAGREE + "diagnosis-drop risk"
elif "ERROR" in (nemotron, qwen): → ERROR  # fail-safe
# Parallel: ThreadPoolExecutor(max_workers=3), ~73s total
```

---

## HUGGINGFACE

| Resource | Identifier |
|----------|-----------|
| Training dataset | chambul/medisimplifier-nemotron-dataset |
| Merged model v2 | chambul/MediSimplifier-OpenBioLLM-v2-merged |
| JudgeBench | chambul/MedSimp-JudgeBench |
| Source dataset | GuyDor007/medisimplifier-dataset |
| v1 merged model | chambul/MediSimplifier-OpenBioLLM-merged |
| v1 adapter | chambul/MediSimplifier-LoRA-Adapter-Nebius |

---

## NEBIUS BILLING (ACTUAL)

| Resource | Usage | Cost |
|----------|-------|------|
| Nemotron Super teacher | 81.23M output tokens | $75.19 |
| Nemotron Nano calibration | 3.48M output tokens | $0.90 |
| Llama + Qwen endpoint tests | — | $0.43 |
| H100 NVLink | 5.55 GPU hours | $21.36 |
| CPU + RAM | 211.95 vCPU / 847.80 GiB hours | $5.25 |
| Disk + Object Storage | 75,000 GiB hours | $7.29 |
| **Total v2** | | **$110.41** |

---

## README STATUS — COMPLETE ✅

All sections committed. Key commits this session:
```
898c5df  key findings v2, what nebius added v2, LoRA config
ed54a6b  evaluation results complete
2194131  pipeline → eval + merge + endpoint
5c1e7e3  safety gate decision rule + live demo
280ed5a  VAGT precision fix
d547b51  Merge & Deploy v2
7a181a0  Adapter Storage Flow
3478f07  hardware and cost ($110.41)
5fd96aa  reproduce → Nebius Jobs table
12a8c3d  fix eval results path
6a1f932  project structure (29 files)
ab08bdb  4 missing files
2515f8e  endpoint-v3 rebuild recipe
882fea9  Container Images
fe17b98  Dataset and models
d21d586  dataset split counts
86d87e1  Public Artifacts
9f440eb  Future Work & Limitations
```

---

## PENDING TASKS

### SECURITY — URGENT:
- [ ] Rotate Nebius API key (exposed in transcript)
- [ ] Rotate HuggingFace token (exposed in transcript)

### Next Priority:
- [ ] First review with Claude Opus 4.7
- [ ] VAGT files integration from v1 repo:
      vagt_section.md, vagt_estimand.md, vagt_medsimplifier_demo.py,
      calculate_kappa_ci.py, calibration_judge_cot.py,
      power_simulation_v7.py, power_simulation_v7.txt,
      kappa_robustness_check.txt, judge_accuracy_cot_vs_nocot.txt
      NOTE: These were developed POST-v1 submission, NOT part of v1 submission
- [ ] Novel Finding section — VAGT Inversion placement in README
- [ ] Blog post v2 (Medium)
- [ ] Demo video (< 3 min, YouTube)
- [ ] Devpost submission fields
- [ ] Update CLAUDE_CODE_CONTEXT.md in repo (uncommitted local edits)
- [ ] License already exists ✅

### IRL Event:
- Tel Aviv, September 15 (City Winner Award $500 possible)

---

## ACCURACY CATCHES THIS SESSION

1. PABAK/Gwet AC1 overclaim → corrected to Fleiss κ + Krippendorff α
2. "ERROR in any judge" → corrected to "ERROR in Nemotron or Qwen"
3. Fleiss κ vs Krippendorff α attribution → precision fix
4. eval path eval_v2/results.json → results/eval_v2_results.json
5. Total cost $110.42 → $110.41

---

## IMPORTANT NOTES

- v1 repo: github.com/deepset01-sys/medisimplifier-nebius (🥇 First Place)
- VAGT post-v1 files are in v1 repo but NOT part of v1 submission
- "From Finding to Framework" narrative belongs in blog post / Devpost, NOT README
- Nemotron Nano threshold: "ERROR" in (nemotron, qwen) → Llama NOT in consensus logic
- Test set for eval: GuyDor007 test (1,001) → NOT Nemotron dataset test (998)
- 9,999 source records → 9,976 valid Nemotron references (23 errored)
