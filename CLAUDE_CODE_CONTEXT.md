# CLAUDE CODE CONTEXT — MediSimplifier v2
# Nebius x NVIDIA Global AI Hackathon
# Last updated: 2026-08-30 (Session: README complete + First Opus 4.7 Review)

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
| FK-Grade v1 | 7.33 | v1 repo |
| Teacher ROUGE-L | 0.525 | teacher_comparison.json |
| n_samples eval | 1,001 | results/eval_v2_results.json |
| Training samples | 7,983 | chambul/medisimplifier-nemotron-dataset |
| Training time | 8,523s (~2.4h) | Nebius job logs |
| Total cost v2 | $110.42 | Nebius Console actual billing |
| H100 hours | 5.55 | Nebius Console |
| Nemotron Super cost | $75.19 | Nebius Console Token Factory |
| Nemotron Nano cost | $0.90 | Nebius Console Token Factory |

---

## DIAGNOSIS RECALL NUMBERS — RECONCILIATION (CRITICAL)

Three numbers that appear in README — all correct but need clear denominators:
- **84.2%** = Nemotron overall recall across ALL 4 error types (508 corrupted samples)
- **68%** = Nemotron recall on diagnosis-corrupted SUBSET ONLY (n≈127)
- **47%** = Nemotron UNSAFE rate across ALL 708 (including 200 clean controls)

Source: nemotron_calibration_full.json
TODO: Add footnote in README reconciling these three numbers explicitly.

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
Verdict distribution (n=708): 208 SAFE / 491 UNSAFE / 9 ERROR = 69.4% UNSAFE rate

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
| **Total v2** | | **$110.42** |

---

## README STATUS — COMPLETE ✅

All sections committed. Last commit: 86d87e1 (Public Artifacts)

---

## FIRST OPUS 4.7 REVIEW — COMPLETE ✅

**Score: 33/40 — "Submission-ready and competitive for a top-tier finish"**

| Criterion | Score |
|-----------|-------|
| Technological Implementation | 9/10 |
| Design | 8/10 |
| Potential Impact | 7/10 |
| Quality of the Idea | 9/10 |

**What reviewer praised:**
- VAGT inversion — "strongest intellectual contribution"
- max_tokens finding — "real engineering, generalizes beyond this project"
- Cost transparency — "unusually honest"
- Limitation table — rare in hackathon submissions
- Honest ROUGE-L reframing cross-validated by teacher↔teacher 0.525

**Review file:** review_output_v2_opus47.txt (in repo)

---

## TOP 3 FIXES FROM REVIEW

### Fix #1 — Reconcile diagnosis numbers (EASY)
Add footnote in Medical Safety Evaluation:
- 84.2% = overall recall across all 4 error types (n=508 corrupted)
- 68% = recall on diagnosis-corrupted subset only (n≈127)
- 47% = UNSAFE rate across ALL 708 (including 200 clean controls)
Cite: nemotron_calibration_full.json

### Fix #2 — Commit live demo JSON (EASY)
We have the live endpoint response. Commit as docs/live_demo.json:
- Llama: SAFE, Qwen: SAFE, Nemotron: UNSAFE
- consensus: DISAGREE + "diagnosis-drop risk"
- latency: total_ms ~73,392
OR reframe as "reproducible via safe_endpoint_v2.yaml" and drop "tested live"

### Fix #3 — Inline job YAML + training log (MEDIUM)
Show job_train_v2.yaml inline (image train-v31, sha256:9d832..., H100)
Add 10 lines of training log proving 8,523s / 3 epochs / seed=42
This could push Technological Implementation from 9 → 10

---

## ADDITIONAL README FIXES IDENTIFIED

- [ ] VAGT framing: change "originates in v1" → "developed between submissions, directly from κ=0.11 finding"
- [ ] FK-Grade 8.87 tension: add sentence → "v2's primary contribution is the judge-panel research (VAGT); for patient-facing deployment v1 remains more readable"
- [ ] Remove "Blog Post: [coming soon]" placeholder
- [ ] Trim σ²_B repetition — appears 4 times → reduce to 2
- [ ] Document safety_mode request/response contract inline

---

## VAGT FRAMING — CRITICAL NOTE

VAGT did NOT originate in v1 submission. Correct narrative:
- v1 submitted July 15 — found κ=0.11
- Six weeks post-v1: developed VAGT (calculate_kappa_ci.py, vagt_estimand.md,
  calibration_judge_cot.py, power_simulation_v7.py, vagt_section.md etc.)
- These files are in v1 REPO but NOT part of v1 SUBMISSION
- v2 submission period opens August 26
- v2 is VAGT's first empirical application

Files developed between submissions (in v1 repo, NOT v1 submission):
- calculate_kappa_ci.py
- calibration_judge_cot.py
- judge_accuracy_cot_vs_nocot.txt
- kappa_robustness_check.txt
- power_simulation_v7.py / power_simulation_v7.txt
- vagt_estimand.md
- vagt_medsimplifier_demo.py
- vagt_section.md

---

## PENDING TASKS (PRIORITY ORDER)

### 🔴 SECURITY — URGENT:
- [ ] Rotate Nebius API key (exposed in transcript)
- [ ] Rotate HuggingFace token (exposed in transcript)

### 🔴 Top 3 Review Fixes (next session):
- [ ] Fix #1: Reconcile 47%/68%/84.2% — footnote
- [ ] Fix #2: Commit docs/live_demo.json OR reframe endpoint claim
- [ ] Fix #3: Inline job_train_v2.yaml + training log excerpt
- [ ] Run second Opus 4.7 review — target 36+/40

### 🟡 README Polish:
- [ ] VAGT framing fix ("developed between submissions")
- [ ] FK-Grade 8.87 tension — add clarifying sentence
- [ ] Remove "Blog Post: coming soon"
- [ ] Trim σ²_B repetition
- [ ] Document safety_mode contract
- [ ] Update CLAUDE_CODE_CONTEXT.md in repo

### 🟡 VAGT Integration:
- [ ] Discuss narrative integration of v1 post-submission VAGT files into v2
- [ ] Novel Finding section placement

### 🟢 Deliverables:
- [ ] Blog post v2 (Medium) — "From Finding to Framework"
- [ ] Demo video (< 3 min, YouTube)
- [ ] Devpost submission fields

### IRL Event:
- Tel Aviv, September 15 (City Winner Award $500 possible)

---

## SCHEDULE

```
September 1-7:
  - Top 3 fixes (1 hour)
  - VAGT framing + FK-Grade tension (1 hour)
  - Second Opus review — target 36+/40

September 8-15:
  - Blog post v2 (Medium)
  - IRL Event Tel Aviv (September 15)
  - VAGT files integration from v1

September 16-30:
  - Demo video
  - Devpost submission fields
  - Security — rotate keys

October 1-29:
  - Final Opus review iterations
  - Polish to maximum score
  - Final submission
```

---

## ACCURACY CATCHES (ALL SESSIONS)

1. PABAK/Gwet AC1 overclaim → corrected to Fleiss κ + Krippendorff α
2. "ERROR in any judge" → corrected to "ERROR in Nemotron or Qwen"
3. Fleiss κ vs Krippendorff α attribution → precision fix
4. eval path eval_v2/results.json → results/eval_v2_results.json
5. Total cost $110.42 confirmed correct (matches line-item sum); earlier "$110.42 → $110.41" catch was itself wrong and has been reverted

---

## IMPORTANT NOTES

- v1 repo: github.com/deepset01-sys/medisimplifier-nebius (🥇 First Place, $320.20)
- VAGT post-v1 files are in v1 repo but NOT part of v1 submission
- "From Finding to Framework" narrative → blog post / Devpost, NOT README
- Nemotron Nano: "ERROR" in (nemotron, qwen) → Llama NOT in consensus logic
- Test set for eval: GuyDor007 test (1,001) → NOT Nemotron dataset test (998)
- 9,999 source records → 9,976 valid Nemotron references (23 errored)
- FK-Grade 8.87 > v1 7.33 → v2 LESS readable for patients; v2's value = VAGT research
- σ²_B 0.347→0.229 appears 4x in README — needs trimming to 2x
