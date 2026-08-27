# MediSimplifier v2 — Claude Code Context
## For Implementation & Code

---

## Active Repo (v2)
`C:\Users\User\Desktop\medisimplifier-nemotron-vagt`
`github.com/deepset01-sys/medisimplifier-nemotron-vagt`

## Reference Repo (v1 — PRIMARY REFERENCE)
`C:\Users\User\Desktop\assignment_01\medisimplifier-nebius`
`github.com/deepset01-sys/medisimplifier-nebius`

**Always check v1 repo first before writing new code.**
**The v1 repo is production-quality and fully reproducible.**

---

## Key Data Files (v1 repo)

```
results/nebius_evidence/
  calibration_verdicts.json      # 708 samples, Llama+Qwen verdicts (no-CoT)
  calibration_verdicts_cot.json  # 708 samples, CoT condition
  safety_results_v2.json         # 1001 samples, dual-judge
  safety_results_v3.json         # 1001 samples, CoT condition

# Root level (v1):
judge_accuracy_cot_vs_nocot.txt  # CoT vs no-CoT accuracy table
kappa_robustness_check.txt       # PABAK, Gwet AC1, Krippendorff α
vagt_section.md                  # VAGT framework
vagt_estimand.md                 # Formal generative model
vagt_medsimplifier_demo.py       # Empirical validation
calculate_kappa_ci.py            # Bootstrap CI
calibration_judge_cot.py         # CoT accuracy run
power_simulation_v7.py           # RQ4 power simulation
```

## Key Data Files (v2 repo)

```
nemotron_calibration_full.json   # 708 samples, Nemotron Nano verdicts
vagt_nemotron_results.txt        # VAGT 3-rater analysis
FINDINGS.md                      # All key findings documented
```

---

## Nebius Token Factory — Model Strings

```python
NEMOTRON_NANO  = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
NEMOTRON_SUPER = "nvidia/nemotron-3-super-120b-a12b"
NEMOTRON_ULTRA = "nvidia/Nemotron-3-Ultra-550b-a55b"
LLAMA          = "meta-llama/Meta-Llama-3.1-70B-Instruct"
QWEN           = "Qwen/Qwen2.5-32B-Instruct"

# Token Factory endpoint
BASE_URL = "https://api.studio.nebius.com/v1/"

# CRITICAL: Nemotron is a reasoning model
# max_tokens=8000 REQUIRED (uses ~3.7k thinking tokens)
# enable_thinking: False does NOT work — use token budget instead
```

---

## Git Identity (v2 repo)
```
user.name  = deepset01-sys
user.email = deepset01@gmail.com
```

---

## Working Methodology (NEVER DEVIATE)

1. **Never fabricate results** — zero tolerance
2. **Show script before running** — always
3. **Estimate cost before large runs** — always
4. **Commit after each meaningful step**
5. **Check v1 repo before writing new code**
6. **Parallel workers for Token Factory** — 12 workers default
7. **Checkpoint every 50 samples** — for long runs
8. **max_tokens=8000 for Nemotron** — reasoning model

---

## Key Findings (for context)

### v1 Findings
- CoT: κ=0.1114→0.0431, Δκ=0.0682, p<0.0001
- Llama d′: 1.694→1.178 (CoT), Qwen d′: 2.717→1.339
- VAGT: PABAK=0.827 vs Φ_V=0.404 on diagnosis (inversion)
- σ²_B=0.347 diagnosis no-CoT → 0.229 with Nemotron (3-rater)

### v2 Findings (so far)
- Nemotron Nano: recall=84.2%, FP=35.2%, balanced_acc=74.5%
- Diagnosis: Nemotron 68% vs Llama 14% vs Qwen 7%
- VAGT 3-rater: Φ_V diagnosis +0.072, Fleiss κ goes negative
- "Adding Nemotron makes consensus metrics worse, VAGT better"

---

## Next Tasks (v2)

1. **Nemotron Super as teacher**
   - Generate reference simplifications for JudgeBench items
   - Compare ROUGE-L vs Claude Opus references
   - Script: `nemotron_teacher.py`

2. **Fine-tune on Nemotron references**
   - Same LoRA config as v1 (r=32, all attention, 8K samples)
   - Replace Claude Opus references with Nemotron Super
   - Nebius Job on H100

3. **VAGT on all conditions**
   - no-CoT, CoT, Nemotron judge
   - Full 4×3 table

4. **README for hackathon**
   - Rubric: Technological Implementation, Design, Impact, Idea Quality
   - Must highlight: Nemotron across full pipeline

---

## Hackathon Requirements
- Track: Best Apps and Agents
- Must use: NVIDIA Nemotron + Token Factory or AI Cloud
- Deadline: October 30, 2026
- License: Apache 2.0 ✅ (already set)
- Public repo ✅
- Demo video: 3 min max
- Working demo URL required
