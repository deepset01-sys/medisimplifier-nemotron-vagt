---
license: cc-by-nc-sa-4.0
language:
- en
tags:
- medical
- llm-evaluation
- judge-calibration
- safety
- faithfulness
size_categories:
- n<1K
pretty_name: MedSimp-JudgeBench v2 (diagnosis stratum)
---

# MedSimp-JudgeBench v2 — diagnosis stratum

**Version:** 2.0 · **License:** CC-BY-NC-SA-4.0 · **Supersedes (diagnosis stratum only):**
[`chambul/MedSimp-JudgeBench`](https://huggingface.co/datasets/chambul/MedSimp-JudgeBench) (v1)
· **Code & full provenance:** [deepset01-sys/medisimplifier-nemotron-vagt](https://github.com/deepset01-sys/medisimplifier-nemotron-vagt)

## What this is

A benchmark for testing whether an LLM judge catches a **silently dropped primary diagnosis**
in a plain-language discharge summary. It contains **412 items**:

| Set | Items | Used in the headline figures |
|--|--|--|
| τ=1 drops — a faithful simplification with its primary diagnosis removed | 120 | yes |
| τ=0 paired controls — the *same* simplification before the edit | 120 | yes |
| τ=0 supplementary controls — unpaired faithful simplifications | 172 | no — published for completeness |

The **headline benchmark is the 240 paired items**. Each τ=1 item and its paired control share
a patient (`paired_with`), so each pair isolates one change: the diagnosis is present, or it is
gone. Analyse within pairs.

**τ=1 definition (pre-registered):** a *patient-invisible primary-diagnosis drop* — the diagnosis
name, abbreviation and lay paraphrase are absent; a layperson cannot recover it from the remaining
text; nothing was added; the edit is deletion-only. `patient_recoverable = 0` for all 120 items.

## Why v2 exists

v1's diagnosis-drop labels came from a script that deleted *a sentence mentioning* a diagnosis.
An author-reviewed, item-by-item audit of all 150 v1 diagnosis items found **128/150 still contained the diagnosis**
elsewhere in the summary (9 genuine drops, 13 borderline):
[`results/tau_hand_labels_150.json`](https://github.com/deepset01-sys/medisimplifier-nemotron-vagt/blob/main/results/tau_hand_labels_150.json).
v1's diagnosis labels should not be used. v1's other strata (dose, lateral, negation) are not
replaced by this release.

## Construction provenance

| Role | Model / person | What it did |
|--|--|--|
| Source | `GuyDor007/medisimplifier-dataset`, test split | discharge summaries (`input`) and Claude Opus 4.5 reference simplifications (`clean_ref`) |
| Editor | `deepseek-ai/DeepSeek-V4-Pro` | removed the target diagnosis from `clean_ref` → `edited_summary` |
| Oracle | `openai/gpt-oss-120b` | chose diagnosis targets; answered the τ=1 acceptance gates (name absent, not lay-recoverable, nothing added); ran a non-gating pre-filter |
| Embedding | `Qwen/Qwen3-Embedding-8B` | similarity screen for surviving paraphrases |
| Final arbiter | **the author** | **author-verified, item by item; Claude Opus 4.8 used as a drafting aid** (it proposed an ACCEPT/RETRY verdict for each item; the author confirmed each one) |

Pre-registered protocol (frozen before any judge was run):
[`docs/judgebench_v2_protocol.md`](https://github.com/deepset01-sys/medisimplifier-nemotron-vagt/blob/main/docs/judgebench_v2_protocol.md).
Generator: [`scripts/build_judgebench_v2.py`](https://github.com/deepset01-sys/medisimplifier-nemotron-vagt/blob/main/scripts/build_judgebench_v2.py).

The `input` field is not in the repository's result files; it was joined from the source test
split by row index and checked on every item (`clean_ref` equals the source row's reference
simplification) — **412 / 412 matched**.

## ⚠️ Construction circularity

`gpt-oss-120b` accepted every τ=1 item as the oracle, and `DeepSeek-V4-Pro` wrote every edit.
**Benchmarking gpt-oss-120b or a DeepSeek-family judge on this dataset favours them by
construction**, by an unmeasured amount. The protocol's independence guarantee covers only the
panel judges — Llama-3.3-70B, Qwen3-32B and Nemotron Nano were neither editor nor oracle.

## Fields

**τ=1 drops (120 items)**

| Field | Description |
|--|--|
| `idx` | source row: a number = test-split row index (items from the v1 calibration pool); `hf<N>` = test-split row N |
| `origin` | `calib` (28) or `hf_test` (92) |
| `input` | original discharge summary (joined from the source test split) |
| `target` | the primary diagnosis that was removed |
| `target_type` | `primary` for all items |
| `clean_ref` | reference simplification before the edit |
| `edited_summary` | the same simplification with the diagnosis removed |
| `expert_recoverable` | 1 if a clinician could still infer the diagnosis from what remains |
| `category_retained` | 1 if the broad category survives (e.g. "a cancer") while the specific diagnosis is gone |
| `patient_recoverable` | 0 for all items (a τ=1 requirement) |
| `human_verdict` | the author's final verdict — `ACCEPT` for all 120 |
| `source_batch` | generator batch: `seed42` (28), `seed99_expanded` (33), `seed137_expanded` (18), `seed211_expanded` (41) |

**τ=0 controls (292 items)**

| Field | Description |
|--|--|
| `idx`, `origin`, `input` | as above |
| `clean_ref` | the faithful simplification |
| `tau` | 0 |
| `control_type` | `primary_paired` (120 — the headline controls) or `supplementary_unpaired` (172 — not used in headline figures) |
| `paired_with` | for `primary_paired`: the idx of its τ=1 item (the control's `clean_ref` is identical to that item's pre-edit `clean_ref`); for `supplementary_unpaired`: null |

The 172 supplementary controls all come from the v1 calibration pool (`origin = calib`) and share
no patient with the paired set.

## Covariates (τ=1 items)

| Covariate | = 1 | = 0 |
|--|--|--|
| `category_retained` | 73 | 47 |
| `expert_recoverable` | 90 | 30 |
| `patient_recoverable` | 0 | 120 (by definition) |

The pre-registered **strict subset** is `category_retained = 0` (47 items), reported separately.

## Leaderboard

Headline set only (120 drops / 120 paired controls), deployed gate prompt (`JUDGE_PROMPT` in
`src/safety_gate.py`). Recall on the drops; specificity on the paired controls; ΔΦ_V when the
judge is added to a Llama-3.3-70B + Qwen3-32B panel (panel Φ_V 0.4764; paired item bootstrap,
seed 42, 1,000 resamples).

| Judge | Recall | Specificity | ΔΦ_V added to Llama+Qwen [95% CI] |
|--|--|--|--|
| DeepSeek-V4-Flash-0731 ⚠️ | 118/119 | 75/114 | +0.1238 [+0.1024, +0.1440] (n=233; 7 errors) |
| gpt-oss-120b ⚠️ | 114/120 | 88/120 | +0.1220 [+0.1000, +0.1416] |
| Nemotron-3-Ultra-550B | 107/120 | 70/120 | +0.0781 [+0.0552, +0.1003] |
| Nemotron-3-Nano-30B | 110/120 | 67/120 | +0.0765 [+0.0516, +0.0992] |
| Nemotron-3-Super-120B | 112/120 | 35/120 | +0.0480 [+0.0225, +0.0720] |
| gemma-3-27b-it | 57/120 | 91/120 | +0.0066 [−0.0108, +0.0261] |
| Llama-3.3-70B (panel) | 56/120 | 88/120 | — |
| Qwen3-32B (panel) | 56/120 | 107/120 | — |

⚠️ **Construction circularity:** gpt-oss-120b was the oracle, and DeepSeek-V4-Pro (the same
family as V4-Flash) was the editor, so these two scores are partly by construction. The Nemotron,
Llama, Qwen and gemma scores are not affected by construction roles.

Sources: [`results/judgebench_v2_pool_table.json`](https://github.com/deepset01-sys/medisimplifier-nemotron-vagt/blob/main/results/judgebench_v2_pool_table.json),
[`results/judgebench_v2_panel_gate.json`](https://github.com/deepset01-sys/medisimplifier-nemotron-vagt/blob/main/results/judgebench_v2_panel_gate.json).

## Caveats

- **Author-verified, not clinician-verified:** a single reviewer (the author), with Claude Opus 4.8
  as a drafting aid; no inter-rater κ; no clinician review.
- **Construction circularity** for gpt-oss-120b and DeepSeek-family judges (see above).
- **Synthetic source:** the notes derive from Asclepius synthetic clinical notes — no real patient data.
- **Diagnosis stratum only:** no dose, lateral or negation items.
- **LLM-written references:** `clean_ref` is Claude Opus 4.5 output, not clinician-reviewed.
- **Relationship to v1:** replaces v1's diagnosis stratum; v1's diagnosis labels should not be used.

## Citation

```bibtex
@misc{medsimp_judgebench_v2,
  title  = {MedSimp-JudgeBench v2: a hand-verified diagnosis-drop benchmark for LLM judges},
  author = {Avraham, Shmulik},
  year   = {2026},
  note   = {TODO: final title/venue},
  url    = {https://huggingface.co/datasets/chambul/MedSimp-JudgeBench-v2}
}
```

## License

**CC-BY-NC-SA-4.0**, inherited from the source data (Asclepius-Synthetic-Clinical-Notes →
GuyDor007/medisimplifier-dataset). Non-commercial use only; derivatives must be shared under the
same license.
