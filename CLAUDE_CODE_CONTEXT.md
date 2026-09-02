# CLAUDE CODE CONTEXT — MediSimplifier v2
# Nebius x NVIDIA Global AI Hackathon
# Last updated: 2026-09-02 (Session: audit_panel Steps 1-5 + DISAGREE example; Fable 5 review 28/40 — 7 fixes landed)

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

## SESSION August 30 – September 2, 2026 — review fixes, VAGT CIs, reframe, 4.8 reviews, DISAGREE capture, audit_panel Steps 1-5, Fable 5 review (HEAD = fec2193)

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
23c1afe - CLAUDE_CODE_CONTEXT refresh (Fix #3 complete, v4 review, corrected denominators)
88085fe - paired bootstrap CIs on VAGT deltas (ΔΦ_V +0.071 [+0.055,+0.087] on diagnosis)
1a4f52c - "The finding" lead paragraph (VAGT inversion first) [v5 fix]
bfa7240 - CLAUDE_CODE_CONTEXT refresh (prior — recorded HEAD 1a4f52c, v5 review + /v1/audit_panel decision)
957fcdf - README line 11: VAGT framed as direct response to v1 κ=0.11 finding [4.8 fix]
f20cd2e - Nemotron-refs eval trail documented (job + train-v32 + run id + full digest) [4.8 fix]
6debd43 - Project Structure: all committed results/ artifacts + vagt_bootstrap_cis.json [4.8 fix]
87d719c - Endpoint cold-start wake note + digest table '(full list below)' pointer [4.8 fix]
76710f9 - CLAUDE_CODE_CONTEXT refresh (prior — recorded HEAD 87d719c, 4.8 reviews + DISAGREE spec)
9fe9fa3 - DISAGREE gate-level worked example — idx 146 (Parkinson+depression) splits panel live + capture JSON + script
4f8688a - audit_panel Step 1: vagt_core.py (generalized, bit-identical to README) + regression tests (4/4)
72b9dd7 - audit_panel Step 2: audit_pool data (ground_truth + 3 verdicts); lossless reshape (diag ΔΦ_V=0.0706 ✓)
fa1000d - audit_panel Step 3: pool_loader + selector (reproduces receipt) — 9/9 tests
8c20382 - audit_panel Step 4: schemas + router + mount; /v1/audit_panel live — 13/13 tests
cd97aa1 - audit_pool/candidates.yaml (Step 5) + CCC refresh (recorded HEAD 8c20382)
a6c04c4 - README line 143: disambiguate JudgeBench-ref run (~$1.7) vs full training run ($75.19) [4.8 v4]
f423b99 - README: +0.072→+0.071 consistency (A) + "hallucinated"→"omitted" (B) [Fable 5]
ca0bfba - billing → $134.81 total / 10.22 GPU hrs (README + CCC sweep) [Fable 5 Fix C]
a72cfc8 - README Project Structure: + logs/train_v2.json.gz + results/disagree_case_gate.json [Fable 5]
d707bc4 - README: judge-params table + 4-bit NF4 QLoRA + epoch-2 best-checkpoint disclosure [Fable 5]
b2d37e3 - README: DISAGREE rate 203/708 (28.7%) + calibration caveat [Fable 5]
9afd50b - README: "proving"→"demonstrating on MedSimp-JudgeBench" (lines 17+47) [Fable 5]
fec2193 - README: patient-facing value prop before "The finding" [Fable 5]
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
| Total cost v2 | $134.81 | Nebius Console actual billing |
| H100 hours | 10.22 | Nebius Console |
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

## VAGT RESULTS (from vagt_nemotron_results.txt; paired-Δ 95% CIs committed in vagt_bootstrap_cis.json, 88085fe)

| Feature | Φ_V (L+Q) | Φ_V (+Nemo) | ΔΦ_V | σ²_B (L+Q) | σ²_B (+Nemo) | Δσ²_B |
|---------|-----------|-------------|------|------------|--------------|-------|
| dose | 0.743 | 0.733 | −0.013 [−0.055, +0.021] (n.s.) | 0.054 | 0.047 | −0.007 |
| negation | 0.578 | 0.618 | +0.043 [+0.011, +0.070] | 0.145 | 0.104 | −0.041 |
| lateral | 0.697 | 0.745 | +0.048 [+0.019, +0.074] | 0.077 | 0.050 | −0.027 |
| diagnosis | 0.404 | 0.476 | +0.071 [+0.055, +0.087] | 0.347 | 0.229 | −0.115 [−0.141, −0.090] |

ΔΦ_V column = paired bootstrap (3-rater − 2-rater on same complete-case items, 1000 iters, seed=42), 95% CI.
Fleiss κ on diagnosis: 0.076 → −0.088 (Krippendorff α ≈ same); paired ΔFleiss κ = −0.163 [−0.305, −0.045] (CI excludes 0).
Diagnosis inversion is significant on both axes (Φ_V up, κ down, CIs exclude 0); dose is the lone dip and is n.s.

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
| H100 NVLink | 10.22 GPU hours | $39.34 |
| CPU + RAM | 452.60 vCPU / 1,810.39 GiB hours | $11.22 |
| Disk + Object Storage | 76,053.72 GiB hours | $7.73 |
| **Total v2** | | **$134.81** |

---

## README STATUS — COMPLETE ✅ (HEAD = fec2193)

All sections committed. All v4 review fixes landed:
- v4 Fix #1: real live-endpoint SAFE curl + response + gate-level UNSAFE trace (c2cc0a4)
- v4 Fix #2: "Which model to deploy" callout — v1 for readability, v2 for research/safety (a76f426)
- v4 Fix #3: max_tokens=16000 engineering-finding callout in exec block (cbd32ad)

Plus v5-driven rigor + framing:
- Paired bootstrap CIs on VAGT deltas + surfaced in the README VAGT table (88085fe)
- "The finding" — README now leads with the VAGT inversion before the exec summary (1a4f52c)

Plus 4.8-review doc fixes (all landed): VAGT-as-response-to-κ framing (957fcdf), Nemotron-refs eval trail
(f20cd2e), all results/ artifacts listed in Project Structure (6debd43), endpoint cold-start note + digest
pointer (87d719c).

Earlier fixes landed: VAGT origin framing, recall-denominator footnote, per-stage image tags,
cost $134.81, training-log evidence, blog placeholder removed, σ²_B trimmed to 2×, safety_mode
contract documented, Nemotron-reference eval (companion table).

---

## OPUS 4.7 REVIEW HISTORY

| Review | Score | Verdict |
|--------|-------|---------|
| v2 (review_output_v2_opus47.txt) | 33/40 | "Submission-ready and competitive for a top-tier finish" (Impact 7) |
| v3 (post first fixes) | 33/40 | "Submission-ready and competitive for a top placement" |
| v4 (all fixes landed) | 34/40 | "Submission-ready and competitive for a top prize" (Impact 8) |
| v5 (with bonus prompt) | 32/40 | scores non-deterministic across runs (range 31–34) |

v4 per-criterion: Technological 9 / Design 8 / Impact 8 / Idea 9.
v5 bonus answers: "borderline top-5, not top-3 as submitted"; single biggest lever from competitive → first place =
the **/v1/audit_panel** "win move" — turn VAGT into a reusable Nebius-native judge-panel calibration tool.
v5 top-3: (1) lead with the finding ✅ done (1a4f52c), (2) demonstrate DISAGREE end-to-end via curl — OPEN
(student doesn't self-drop reliably; needs a crafted case), (3) commit bootstrap CIs ✅ done (88085fe).

Review outputs (all UNTRACKED — decide before final submission):
- review_output_v2_opus47.txt, review_output_v3_opus47.txt, review_output_v4_opus47.txt, review_output_v5_opus47.txt
- run_review.py (now supports --model / --prompt), review_prompt.txt, review_prompt_with_bonus.txt
- audit_panel_clarification_prompt.txt, audit_panel_clarification_response.txt
- review_output_v1_opus48.txt, review_output_v2_opus48.txt, review_output_v3_opus48.txt (bonus)
- disagree_capture_clarification_prompt.txt, disagree_capture_clarification_response.txt

---

## OPUS 4.8 REVIEW HISTORY

| Review | Score | Verdict |
|--------|-------|---------|
| v1 (review_output_v1_opus48.txt)        | 34/40 | "Submission-ready and competitive" |
| v2 (review_output_v2_opus48.txt)        | 34/40 | stable — no new substantive findings vs v1 |
| v3 (review_output_v3_opus48.txt, bonus) | 34/40 | "credibly top-3 capable … not yet a locked first place" |

Per-criterion (stable across all three runs): Technological 9 / Design 8 / Impact 8 / Idea 9.

**Bonus ("the one thing to win"):** make the DISAGREE branch witnessable + reframe around the safety layer.
Shared diagnosis of both bonus runs: the killer finding (only Nemotron catches a silent diagnosis drop) is
never shown live — "proven on paper but never witnessed."

**Self-correction (disagree_capture_clarification_response.txt):** Opus 4.8 REVERSED its own hero-slot advice.
A crafted DISAGREE is a *synthetic gate test*, not live product output (our model preserves diagnoses), so it
must NOT sit at the top as "The finding" (that would overclaim). Correct placement = an honestly-labeled
gate-level worked example inside Medical Safety Evaluation; real evaluate_safety gate; no curl/hero framing;
committed only if the panel actually splits. Top-of-README finding stays the VAGT inversion.

False positive to ignore (both 4.8 runs): "future-dated 2026-08-28 training log" — 2026-08-28 is a real PAST
date; the flag is a model knowledge-cutoff artifact. Timestamp is correct — do NOT change it.

---

## FABLE 5 REVIEW HISTORY

| Review | Score | Verdict |
|--------|-------|---------|
| v1 (review_output_v1_fable5.txt, no bonus) | 28/40 | "Strong, honest, technically real … submit after the fixes, not before" |

Per-criterion: Technological 8 / Design 7 / Impact 6 / Idea 7. Harsher + more forensic than Opus 4.8 (33-34) —
grader temperament, not a regression. Run: run_review.py --model claude-fable-5-1, MAX_TOKENS=16000 (needed —
used 14,514 output tokens; truncates at 8000).

7 fixes landed (all committed this session):
1. A+B (f423b99): Key-findings +0.072→+0.071; "hallucinated"→"omitted" (all demonstrated catches are omissions)
2. C (ca0bfba): billing → $134.81 / 10.22 GPU hrs (README table + CCC swept; six line items sum EXACTLY)
3. Tree (a72cfc8): + logs/train_v2.json.gz + results/disagree_case_gate.json (safety_eval_v2.py left out — v1 ref)
4. Disclosures (d707bc4): judge-params table (temp 0 / thinking off / mt 2000·2000·8000); 4-bit NF4 QLoRA base
   (merge loads fp16); epoch-2 best-checkpoint (load_best_model_at_end, NOT epoch-3 overfit 0.8610)
5. DISAGREE rate (b2d37e3): 203/708 (28.7%) = 136 catches + 67 clean false alarms (~1-in-3 spurious)
6. Overclaim (9afd50b): "proving … blind" → "demonstrating on MedSimp-JudgeBench … moves the wrong way"
7. Value prop (fec2193): patient-facing sentence before "The finding"

REMAINING (needs key): calibration≠gate re-run — the 68%/14%/7% and 203/708 numbers come from the CALIBRATION
prompt (Nemotron JSON-CoT + Llama/Qwen v1 no-CoT), NOT safety_gate.py's one-word gate prompt. A full 708-item
re-run through the gate prompt would let the README describe the DEPLOYED gate directly. (Subjective/deferred:
larger "lead with patient value prop" restructure — partially addressed by fec2193.)
Note: Fable did NOT flag the 2026-date false positive that Opus keeps raising.

---

## VAGT FRAMING — CRITICAL NOTE

VAGT did NOT originate in v1 submission. Correct narrative:
- v1 submitted July 15 — found κ=0.11
- Post-v1: developed VAGT (calculate_kappa_ci.py, vagt_estimand.md,
  calibration_judge_cot.py, power_simulation_v7.py, vagt_section.md etc.)
  — commit-verified: VAGT files created Aug 16, 2026 (after v1 submission July 15, before v2 window opens Aug 26)
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

README line 11 reframed (commit 957fcdf): VAGT = "a direct response to v1's κ=0.11 finding, first applied
empirically in v2." The deeper-history mention later in the README was left untouched.

---

## AUDIT_PANEL BUILD (/v1/audit_panel — the "win move")

Spec: audit_panel_clarification_response.txt (Opus 4.7). Turns VAGT into a reusable Nebius-native
judge-panel calibration tool: given an incumbent panel + candidate pool, recommend the third rater that
best raises Φ_V on the panel's blindest stratum, with a paired-bootstrap CI receipt.

### Steps 1-4 — COMPLETE ✅ (offline, no key, no cost; 13/13 tests green)
- Step 1 (4f8688a): src/audit_panel/vagt_core.py — generalized VAGT (arbitrary panel size); estimators
  copied VERBATIM from vagt_nemotron_analysis.py (same SEED=42, same bias correction). + tests.
- Step 2 (72b9dd7): audit_pool/ground_truth.json + verdicts/{Llama-3.3-70B, Qwen3-32B, Nemotron-Nano}.json.
  Reshape validated LOSSLESS via build_pool.py (join key = row_id, NOT idx — idx is only 519/708 unique).
- Step 3 (fa1000d): pool_loader.py + selector.py (worst-stratum ΔΦ_V; bootstrap CI on recommended only).
- Step 4 (8c20382): schemas.py + router.py + mount in safe_endpoint.py (graceful try/except; health field).
- RECEIPT REPRODUCED OFFLINE — POST /v1/audit_panel (Llama+Qwen incumbent, Nemotron candidate) returns:
  recommendation=Nemotron Nano, target_blind_spot=diagnosis, expected_Phi_V_lift=0.0706 (+0.071),
  ci_95=[0.0552, 0.0866] (= README [+0.055,+0.087], bit-for-bit), caveat="dose ΔΦ_V=-0.013 n.s.".
  Pure CPU — no live judge calls.
- CI convention: selector mirrors vagt_nemotron_analysis.py (one rng, canonical stratum order) so the
  endpoint can never drift from the committed vagt_bootstrap_cis.json / README numbers.

### Step 5 — COMPLETE ✅ (offline); Steps 6-8 — PENDING (need key rotation + a deploy)
- Step 5 (cd97aa1): audit_pool/candidates.yaml committed — 3 pooled + 3 pending, all verified-live
  (gemma-3-27b-it, nemotron-super, DeepSeek-V4-Flash).
- Step 6 🔴: generate 708-row verdicts for ~3 more pool models (Token Factory, ~$1/~1h) — NEEDS key
  rotation first. NOTE: Llama-3.1-8B / Qwen2.5-72B are NOT in results/models_verified.json; use verified-live
  models (DeepSeek-V4-Flash, gemma-3-27b-it, nemotron-super).
- Step 7: rebuild endpoint image (endpoint-v4; COPY audit_pool/ + src/audit_panel/) + redeploy; live smoke test.
- Step 8: README /v1/audit_panel section + public artifacts + CCC refresh.

Prompt-consistency rule: verdict files carry prompt_provenance. The 3 committed models preserve the EXACT
verdicts behind the published +0.071 receipt (Llama/Qwen = v1 no-CoT; Nemotron = JSON-CoT); new models must
document their generating prompt.

---

## PENDING TASKS (PRIORITY ORDER)

### 🔴 SECURITY — URGENT
- [ ] Rotate Nebius API key (exposed in transcript) → then redeploy endpoint with new key so live URL survives
- [ ] Rotate HuggingFace token (exposed in transcript)

### ✅ DONE — DISAGREE gate-level worked example (9fe9fa3)
- idx 146 (Parkinson + depression drop) splits the panel LIVE (Llama SAFE + Qwen SAFE + Nemotron UNSAFE →
  DISAGREE). Committed results/disagree_case_gate.json + README worked example (honest gate-level scope, no
  hero slot). idx 21 (primary) did NOT reproduce → disclosed (calibration verdicts ≠ live-gate verbatim).

### ✅ DONE — /v1/audit_panel Steps 1-5 (offline, 13/13 green) — see AUDIT_PANEL BUILD above

### ✅ DONE — Fable 5 review v1 (no-bonus, 28/40) — 7 fixes landed; see FABLE 5 REVIEW HISTORY

### 🟡 NEXT (all gated on 🔴 key rotation above)
- Fable 5 BONUS review: run_review.py --prompt review_prompt_with_bonus.txt --model claude-fable-5-1.
- /v1/audit_panel Steps 6-8: generate ~3 more models' verdicts (Token Factory, needs key) →
  endpoint-v4 rebuild + redeploy → README /v1/audit_panel section + public artifacts.
- calibration≠gate re-run: 708 items through safety_gate.py's exact prompt → recompute recall/VAGT/DISAGREE
  on the DEPLOYED gate (closes the last Fable finding). Needs key.

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
5. Total cost $110.42 confirmed correct (matches line-item sum); earlier "$110.42 → $110.41" catch was itself wrong and reverted — SUPERSEDED 2026-09-02: billing updated to $134.81 as endpoint/eval GPU+CPU+disk usage grew (10.22 GPU hrs; line items re-verified to sum exactly; see NEBIUS BILLING)
6. Recall denominators: 68% = diagnosis-corrupted n=150 (not n≈127); 47% = VAGT stratum n=333 (not all-708) — README footnote committed
7. Endpoint latency: ~73s → ~27s (measured live, 26,975–28,719 ms)
8. Per-stage image tags: train=v29 / eval=v30 / merge=v31 (README had said v31 for all three)
9. Abandoned the un-reproducible DISAGREE endpoint claim (total_ms ~73,392) — could not reproduce across 5 tests; committed honest SAFE smoke test (26,975 ms) instead
10. VAGT Δ was unpaired (2- and 3-rater bootstrapped on different item sets); added paired bootstrap → diagnosis ΔΦ_V +0.071 [+0.055,+0.087] (matches unpaired +0.072 within rounding), CI excludes 0

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
- VAGT deltas are CI-backed (paired bootstrap, seed=42, vagt_bootstrap_cis.json): diagnosis ΔΦ_V +0.071 [+0.055,+0.087] & ΔFleiss κ −0.163 [−0.305,−0.045] both exclude 0; dose ΔΦ_V −0.013 [−0.055,+0.021] not significant
- CLI reproduction: `nebius ai job create --volume` does NOT work for the bucket mounts these jobs use — bare
  bucket → "unsupported volume source type"; `s3://BUCKET:/path:rw` → "s3_config.endpoint: value is required"
  (needs an S3 endpoint + creds profile the native YAML `bucket:` mount supplies automatically). Verified twice
  on VM 195.242.10.164; no job created either time (zero GPU spend). VERIFIED reproduction path = Nebius
  Console + committed YAMLs. Decision (Option 1): do NOT put unverified CLI commands in the README.
- Reviews done: Opus 4.8 v1/v2/v4 33-34 + v3 bonus; Fable 5 v1 28/40 (no-bonus, 7 fixes landed). Next: Fable 5 bonus (after key rotation).
