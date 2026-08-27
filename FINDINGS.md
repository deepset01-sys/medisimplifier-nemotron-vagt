# Findings — MediSimplifier v2 (Nemotron × VAGT)

## 1. Nemotron Nano as a safety judge — full calibration (n=708)

Nemotron-3 Nano (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`) run as a faithfulness
judge on MedSimp-JudgeBench (no-CoT / v2 condition), using the **same** judge
prompt as the original project (`src/safety_eval_v2.py`). It judged the same
`(input, perturbed)` pairs as the stored Llama + Qwen verdicts, so all three
raters are directly comparable. 699/708 valid (9 transient ERRORs, 1.3%).

Source data: [`nemotron_calibration_full.json`](nemotron_calibration_full.json).
Reproduce: `python nemotron_judge_test.py --n 708 --workers 12 --output nemotron_calibration_full.json`.

### Verdict distribution
| Judge | SAFE | UNSAFE | ERROR | UNSAFE rate |
|---|---|---|---|---|
| Nemotron | 208 | 491 | 9 | **~70%** |
| Llama-3.3-70B | 544 | 164 | 0 | 23% |
| Qwen3-32B | 405 | 267 | 36 | ~40% |

### Accuracy vs ground truth (200 clean → SAFE; 508 corrupted → UNSAFE)
| Metric | **Nemotron** | Llama | Qwen |
|---|---|---|---|
| False-positive on clean (over-flagging) | **35.2%** ⚠️ | 1.5% | 0.5% |
| Recall on corrupted (catches real errors) | **84.2%** ✅ | 31.7% | 55.9% |
| Specificity (clean) | 64.8% | 98.5% | 99.5% |
| **Balanced accuracy** | 74.5% | 65.1% | **77.7%** |

### Recall by error type (corrupted only)
| Error type | Nemotron | Llama | Qwen |
|---|---|---|---|
| **diagnosis** (known blind spot) | **68%** | 14% | 7% |
| dose | 92% | 44% | 86% |
| lateral | 97% | 43% | 85% |
| negation | 82% | 30% | 55% |

**Summary:** Nemotron Nano is a **high-sensitivity, low-specificity** judge. It
catches errors Llama and Qwen miss — most dramatically diagnosis omissions
(68% vs 7–14%) — but over-flags ~1 in 3 faithful simplifications. It is **not a
drop-in calibrated judge as-is**; it needs threshold/prompt calibration to pull
the false-positive rate down without losing its recall edge. On *balanced*
accuracy Qwen still wins (77.7%) purely on near-perfect specificity.

---

## 2. VAGT 3-rater decomposition — the headline result

Adding Nemotron as a **third rater** alongside Llama + Qwen, per error type.
`Φ_V` = veridicality-anchored dependability (agreement with ground truth, higher
is better). `σ²_B` = shared blind-spot bias (all raters wrong the same way,
lower is better). SAFE=0/UNSAFE=1; point estimates from a 1000-item bootstrap,
seed=42; complete-case (rows with any ERROR verdict dropped).

Reproduce: `python vagt_nemotron_analysis.py` →
[`vagt_nemotron_results.txt`](vagt_nemotron_results.txt).

| feature | Φ_V (L+Q) | Φ_V (+Nemo) | ΔΦ_V | σ²_B (L+Q) | σ²_B (+Nemo) | Δσ²_B |
|---|---|---|---|---|---|---|
| dose | 0.743 | 0.733 | **−0.010** | 0.054 | 0.047 | −0.007 |
| negation | 0.578 | 0.618 | +0.040 | 0.145 | 0.104 | −0.041 |
| lateral | 0.697 | 0.745 | +0.047 | 0.077 | 0.050 | −0.027 |
| **diagnosis** | **0.404** | **0.476** | **+0.072** | **0.347** | **0.229** | **−0.118** |

Full per-feature decomposition (σ²_τ, σ²_B, σ²_R, σ²_N, Φ_V, Fleiss κ,
Krippendorff α, pairwise Cohen κ, and per-rater bias α_r) with 95% bootstrap CIs
is in [`vagt_nemotron_results.txt`](vagt_nemotron_results.txt).

### The diagnosis inversion (the whole point of VAGT)

On `diagnosis`, Llama + Qwen share a massive blind spot — σ²_B = 0.347, Φ_V =
0.404 (worst of all features); both almost never flag diagnosis omissions
(UNSAFE rates 7% / 3%). Adding Nemotron (47% UNSAFE on diagnosis):

- **cuts shared bias by a third** — σ²_B 0.347 → 0.229 (largest reduction of any feature),
- **raises dependability most** — Φ_V 0.404 → 0.476 (+0.072),
- **yet Fleiss κ and Krippendorff α go *negative*** — 0.076 → **−0.088**.

That is a **consensus-vs-veridicality inversion**: by every rater-agreement
metric the three-judge panel looks *worse*, while Φ_V correctly shows it moved
*closer to ground truth*. Agreement statistics only measure judge-to-judge
consensus — never agreement with truth — so they reward a shared blind spot and
penalize the one rater that breaks it. This is exactly the failure mode VAGT was
built to expose, and the data confirms it.

Per-rater bias on diagnosis (α_r, positive = flags UNSAFE more than panel mean):
Llama −0.13, Qwen −0.16, **Nemotron +0.28** — Nemotron is the lone rater pulling
the consensus toward the truth.

---

## 3. Honest caveats

- **Nemotron is not a free win everywhere.** On `dose`, ΔΦ_V = **−0.010**
  (slight *loss*): Llama+Qwen weren't badly blind there (σ²_B only 0.054), so
  Nemotron's added rater noise outweighs the small bias gain. The panel benefits
  most exactly where the two incumbents share a blind spot (diagnosis, negation,
  lateral) and least where they don't (dose).
- **Adding a diverging rater raises σ²_R and σ²_N across the board.** σ²_R goes
  from ~0 (the two-rater case, where Llama+Qwen fail together) to 0.024–0.040;
  σ²_N roughly doubles. Φ_V nets the veridicality gain against this added noise —
  a positive ΔΦ_V means the gain wins. This cost side is printed explicitly per
  feature, not hidden.
- **35.2% false-positive rate on clean controls** is the elephant in the room:
  Nemotron's veridicality gains come partly from being *trigger-happy*. Its high
  recall and its over-flagging are two sides of the same low threshold. Any
  production use needs calibration to separate the two.
- **68 items (9–18 per feature) dropped** for ERROR verdicts (complete-case
  analysis). 9 of those are Nemotron transient nulls (recoverable with higher
  `max_tokens`/retries); the rest are Qwen's 36 ERRORs from the original run.
- **Single condition.** This is the no-CoT (v2) prompt only. No Nemotron CoT
  (v3) data yet, so the CoT condition from the original demo is not reproduced
  here with three raters.
- **σ²_R is now genuinely informative** (unlike the original 2-rater demo, where
  it was illustrative because both judges failed identically). With a third,
  diverging rater the rater facet finally has signal.

---

## 4. Operational notes

- **Model strings on Nebius Token Factory** (verified via `--list-models`):
  Nemotron Nano = `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (a 30B-A3B MoE, ~3B
  active — **not** an 8B dense model); Nemotron Super = `nvidia/nemotron-3-super-120b-a12b`.
- **Nemotron-3 Nano is a reasoning model:** it thinks internally first, then
  emits the JSON answer in `content`. Too small a `max_tokens` returns
  `content=None` / `finish_reason=length`. Fix: `max_tokens=8000` (observed ~3.7k
  reasoning tokens/call). Neither `enable_thinking:False` nor a "detailed
  thinking off" system directive disables its reasoning — token budget is the
  only lever.
- Full 708-sample run: ~32 min at 12 concurrent workers.
