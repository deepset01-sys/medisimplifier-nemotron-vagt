# CLAUDE CODE CONTEXT — MediSimplifier v2
# Nebius x NVIDIA Global AI Hackathon
# Last updated: 2026-08-31 (Session: Fix #3 executed + v4 Opus review 34/40 — all review fixes landed)

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

## SESSION August 30–31, 2026 — review fixes + Fix #3 executed (HEAD = c2cc0a4)

```
591428a - Training log committed + .gitignore whitelist
6313d2a - Per-stage image tags corrected (v29/v30/v31) + excerpt
61ee5bf - Endpoint reframe (~27s) + smoke-test + models_verified
29c745d - VAGT origin framing reconciled
18cf994 - README polish (blog removed, FK-Grade, σ²_B trim, safety_mode)
c239d3c - Fix #3 scaffolding (job + scripts + evaluate.py --save-predictions)
70318dc - Pin eval-nemotron job to train-v32
fd36ae2 - Nemotron-reference eval companion table + results artifact
a76f426 - Model-recommendation callout [v4 fix #2]
cbd32ad - max_tokens=16000 engineering-finding callout [v4 fix #3]
c2cc0a4 - Real live-endpoint SAFE curl + gate-level UNSAFE trace [v4 fix #1]
```

### FIX #3 STATUS — COMPLETE ✅
- train-v32 built + pushed: sha256:2c95dfef0a29... (includes evaluate.py --save-predictions)
- Eval job ran → predictions.json written to bucket eval_v2_nemotron/
- Scored vs Nemotron refs with train-v32 libraries (version-consistent):
  ROUGE-L 0.601 / BERTScore 0.9321 / SARI 64.18 (n=998; 3 errored Nemotron refs skipped)
- results/eval_v2_nemotron_results.json + README companion table committed (fd36ae2)

### ENDPOINT
- URL: https://port8000-qzv93v671z09ej5.tunnel.applications.eu-north1.nebius.cloud
- Latency: ~27s (3-judge Token Factory gate; corrected from ~73s)
- Live Nebius serverless endpoint — permanent URL, scales to zero, wakes on request (~27s cold start)
- Real SAFE call + response in README (Reproduce) and results/endpoint_smoke_test.json

### SECURITY — URGENT
Rotate Nebius API key + HF token (both exposed in transcripts). Endpoint uses NEBIUS_API_KEY →
rotate, then redeploy endpoint with the new key so the live URL keeps working.

---

## KEY NUMBERS (ALL VERIFIED)

| Metric | Value | Source |
|--------|-------|--------|
| ROUGE-L v2 | 0.5254 | results/eval_v2_results.json |
| SARI v2 | 60.36 | results/eval_v2_results.json |
| BERTScore v2 | 0.9113 | results/eval_v2_results.json |
| FK-Grade v2 | 8.87 | results/eval_v2_results.json |
| FK-Grade v1 | 7.33 | v1 repo |
| ROUGE-L v2 vs Nemotron refs | 0.6010 | results/eval_v2_nemotron_results.json |
| BERTScore v2 vs Nemotron refs | 0.9321 | results/eval_v2_nemotron_results.json |
| SARI v2 vs Nemotron refs | 64.18 | results/eval_v2_nemotron_results.json |
| Teacher ROUGE-L | 0.525 | teacher_comparison.json |
| n_samples eval | 1,001 | results/eval_v2_results.json |
| Training samples | 7,983 | chambul/medisimplifier-nemotron-dataset |
| Training time | 8,523s (~2.4h) | logs/train_v2.json.gz (train_runtime) |
| Total cost v2 | $110.42 | Nebius Console actual billing |
| H100 hours | 5.55 | Nebius Console |
| Nemotron Super cost | $75.19 | Nebius Console Token Factory |
| Nemotron Nano cost | $0.90 | Nebius Console Token Factory |

---

## DIAGNOSIS RECALL NUMBERS — RECONCILIATION

Three numbers appear in README — all correct, different denominators (see README footnote in Medical Safety Evaluation):
- **84.2%** = Nemotron overall recall across all 4 error types (421 of 500 non-ERROR corrupted; 508 corrupted total)
- **68%** = Nemotron recall on the diagnosis-corrupted subset (100 of 147 non-ERROR; 150 diagnosis-corrupted total)
- **47%** = Nemotron UNSAFE rate on the VAGT diagnosis stratum (complete-case n=333, ~41% corrupted) — NOT the all-708 rate (which is 69.4%)

Sources: nemotron_calibration_full.json (recall) + vagt_nemotron_results.txt (47% stratum rate)

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
  eval_v2/              → evaluation results (Claude refs)
  eval_v2_nemotron/     → predictions.json + results.json (Fix #3 run)
CR path: cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:<tag>
Build host: VM ubuntu@195.242.30.65 (nebius_vm key); has nebius CLI + boto3 + ~/.aws/credentials
```

---

## DOCKER IMAGES

| Tag | Digest | Purpose |
|-----|--------|---------|
| train-v29 | sha256:bbbf6df1... | training only |
| train-v30 | sha256:6c3cd4cd... | evaluation (OLD, pre --save-predictions) |
| train-v31 | sha256:9d832391... | merge only |
| train-v32 | sha256:2c95dfef0a298ce258f094fa5d5647b0d7c84e297850bff8b7daba5a719694dc | evaluation with --save-predictions |
| endpoint-v3 | sha256:9d950d83... | Safe Endpoint v2 |

**Critical:** cryptography==48.0.1 pinned via post-install step in Dockerfile.train
**Build method:** manual `docker build` dual-tagged to Docker Hub + Nebius CR, tag bumped per version (build_and_push.sh is STALE — hardcodes v28, Docker-Hub only). CR login: `nebius iam get-access-token | docker login cr.eu-north1.nebius.cloud --username iam --password-stdin`.

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

Model strings verified live via /v1/models → results/models_verified.json (31 models; both nvidia strings present).

---

## SAFE ENDPOINT v2 DECISION RULE (safety_gate.py)

```python
if nemotron=="SAFE" and qwen=="SAFE": → SAFE
if nemotron=="UNSAFE" and qwen=="UNSAFE": → UNSAFE
if qwen=="UNSAFE": → UNSAFE  # trust 0.5% FP specificity
if nemotron=="UNSAFE" and qwen=="SAFE": → DISAGREE + "diagnosis-drop risk"
elif "ERROR" in (nemotron, qwen): → ERROR  # fail-safe
# Parallel: ThreadPoolExecutor(max_workers=3), ~27s total
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

## README STATUS — COMPLETE ✅ (HEAD = c2cc0a4)

All sections committed. All v4 review fixes landed:
- v4 Fix #1: real live-endpoint SAFE curl + response + gate-level UNSAFE trace (c2cc0a4)
- v4 Fix #2: "Which model to deploy" callout — v1 for readability, v2 for research/safety (a76f426)
- v4 Fix #3: max_tokens=16000 engineering-finding callout in exec block (cbd32ad)

Earlier fixes landed: VAGT origin framing, recall-denominator footnote, per-stage image tags,
cost $110.42, training-log evidence, blog placeholder removed, σ²_B trimmed to 2×, safety_mode
contract documented, Nemotron-reference eval (companion table).

---

## OPUS 4.7 REVIEW HISTORY

| Review | Score | Verdict |
|--------|-------|---------|
| v2 (review_output_v2_opus47.txt) | 33/40 | "Submission-ready and competitive for a top-tier finish" (Impact 7) |
| v3 (post first fixes) | 33/40 | "Submission-ready and competitive for a top placement" |
| v4 (all fixes landed) | 34/40 | "Submission-ready and competitive for a top prize" (Impact 8) |

v4 per-criterion: Technological 9 / Design 8 / Impact 8 / Idea 9.
Review outputs: review_output_v2/v3/v4_opus47.txt + run_review.py + review_prompt.txt
— **UNTRACKED (not committed to repo)**; decide before final submission.
v4 top-3 (all done): real live-URL curl, model-recommendation callout, max_tokens elevation.

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

### 🔴 SECURITY — URGENT
- [ ] Rotate Nebius API key (exposed in transcript) → then redeploy endpoint with new key so live URL survives
- [ ] Rotate HuggingFace token (exposed in transcript)

### 🟢 Deliverables (remaining)
- [ ] Blog post v2 (Medium) — "From Finding to Framework"
- [ ] Demo video (< 3 min, YouTube)
- [ ] Devpost submission fields

### IRL Event
- Tel Aviv, September 15 (City Winner Award $500 possible)

---

## SCHEDULE

```
September (remaining):
  - Rotate keys + redeploy endpoint
  - Blog post v2 (Medium)
  - IRL Event Tel Aviv (September 15)

Late September – October:
  - Demo video (< 3 min, YouTube)
  - Devpost submission fields
  - Final Opus review iterations → final submission (deadline Oct 30)
```

---

## ACCURACY CATCHES (ALL SESSIONS)

1. PABAK/Gwet AC1 overclaim → corrected to Fleiss κ + Krippendorff α
2. "ERROR in any judge" → corrected to "ERROR in Nemotron or Qwen"
3. Fleiss κ vs Krippendorff α attribution → precision fix
4. eval path eval_v2/results.json → results/eval_v2_results.json
5. Total cost $110.42 confirmed correct (matches line-item sum); earlier "$110.42 → $110.41" catch was itself wrong and reverted
6. Recall denominators: 68% = diagnosis-corrupted n=150 (not n≈127); 47% = VAGT stratum n=333 (not all-708) — README footnote committed
7. Endpoint latency: ~73s → ~27s (measured live, 26,975–28,719 ms)
8. Per-stage image tags: train=v29 / eval=v30 / merge=v31 (README had said v31 for all three)
9. Abandoned the un-reproducible DISAGREE endpoint claim (total_ms ~73,392) — could not reproduce across 5 tests; committed honest SAFE smoke test (26,975 ms) instead

---

## IMPORTANT NOTES

- v1 repo: github.com/deepset01-sys/medisimplifier-nebius (🥇 First Place, $320.20)
- VAGT post-v1 files are in v1 repo but NOT part of v1 submission
- "From Finding to Framework" narrative → blog post / Devpost, NOT README
- Nemotron Nano: "ERROR" in (nemotron, qwen) → Llama NOT in consensus logic
- Test set for eval: GuyDor007 test (1,001) → NOT Nemotron dataset test (998)
- 9,999 source records → 9,976 valid Nemotron references (23 errored)
- FK-Grade 8.87 > v1 7.33 → v2 LESS readable for patients; v2's value = VAGT research + safety gate
- σ²_B 0.347→0.229 now appears 2× in README (VAGT table + one narrative) — trim complete
- Endpoint is PUBLIC + unauthenticated in README (live curl advertised) — each call spends Token Factory tokens; consider rate-limit / take-down after judging
- FK-Grade version note: local textstat (newer) gives 9.91; train-v32 image textstat gives 8.87 (comparable to baseline) — always score in-image for comparable numbers
