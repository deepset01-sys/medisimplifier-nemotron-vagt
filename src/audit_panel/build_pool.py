"""
build_pool.py — Reshape the committed 3-judge calibration into the audit_pool layout.

Reads nemotron_calibration_full.json (708 rows, canonical order) and writes:
  audit_pool/ground_truth.json                              {row_id, idx, stratum, tau}
  audit_pool/verdicts/<slug>.json  (one per model)          {row_id, idx, verdict}

Join key is the POSITIONAL row_id (0..707), NOT idx — idx is not unique (519/708:
160 source docs appear as both a clean control and a corrupted perturbation), so
keying by idx would collapse rows and corrupt the VAGT numbers.

Raw verdicts (SAFE/UNSAFE/ERROR) are preserved verbatim; complete-case dropping
happens later at analysis time in vagt_core.stratum(). Each verdict file records
its prompt_provenance so the (mixed) generating prompts are transparent.

Self-validation: after writing, the files are reloaded, merged by row_id, and run
through vagt_core — diagnosis ΔΦ_V must land within ±1e-3 of the published 0.071,
proving the reshape is lossless end-to-end. Offline; no NEBIUS_API_KEY, no cost.

Run:  python src/audit_panel/build_pool.py
"""

import json
import os
import sys
from pathlib import Path

# src/audit_panel on path so `vagt_core` imports whether run from repo root or here.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import vagt_core as vc  # noqa: E402

REPO = _HERE.parents[1]
SOURCE = REPO / "nemotron_calibration_full.json"
POOL_DIR = REPO / "audit_pool"
VERDICTS_DIR = POOL_DIR / "verdicts"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# model id -> (source rater key in per_sample, prompt provenance)
MODELS = {
    "meta-llama/Llama-3.3-70B-Instruct": ("llama_verdict", "v1 v2/no-CoT safety run (safety_eval_v2.py)"),
    "Qwen/Qwen3-32B": ("qwen_verdict", "v1 v2/no-CoT safety run (safety_eval_v2.py)"),
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": ("nemotron_verdict", "nemotron_judge_test.py JSON-CoT prompt (max_tokens=8000)"),
}


def _stratum_of(rec):
    """clean control -> 'clean' (tau=0); corrupted-feature -> error_type (tau=1)."""
    if rec["condition"] == "clean":
        return "clean", 0
    return rec["error_type"], 1


def _stratum_to_ce(stratum):
    """Inverse of _stratum_of: reconstruct (condition, error_type) for vagt_core.stratum()."""
    if stratum == "clean":
        return "clean", "none"
    return "corrupted", stratum


def build():
    per_sample = json.loads(SOURCE.read_text(encoding="utf-8"))
    per_sample = per_sample["per_sample"] if isinstance(per_sample, dict) else per_sample
    n = len(per_sample)

    # ground truth (canonical order == source order; row_id is the join key)
    gt_rows = []
    for row_id, rec in enumerate(per_sample):
        stratum, tau = _stratum_of(rec)
        gt_rows.append({"row_id": row_id, "idx": rec["idx"], "stratum": stratum, "tau": tau})

    POOL_DIR.mkdir(parents=True, exist_ok=True)
    VERDICTS_DIR.mkdir(parents=True, exist_ok=True)

    gt = {
        "benchmark": "MedSimp-JudgeBench",
        "n": n,
        "strata": ["diagnosis", "dose", "lateral", "negation", "clean"],
        "note": ("join key is row_id (idx is NOT unique: 519/708 — 160 docs appear as both a "
                 "clean control and a corrupted perturbation). stratum='clean' => tau=0 control "
                 "shared across all corrupted strata."),
        "rows": gt_rows,
    }
    (POOL_DIR / "ground_truth.json").write_text(
        json.dumps(gt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    written = []
    for model, (key, provenance) in MODELS.items():
        slug = model.split("/")[-1]
        verdicts = [{"row_id": row_id, "idx": rec["idx"], "verdict": rec[key]}
                    for row_id, rec in enumerate(per_sample)]
        errors = sum(1 for v in verdicts if v["verdict"] not in vc.VALID)
        payload = {
            "model": model,
            "slug": slug,
            "benchmark": "MedSimp-JudgeBench",
            "n": n,
            "prompt_provenance": provenance,
            "verdicts": verdicts,
        }
        out = VERDICTS_DIR / f"{slug}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append((slug, key, errors, out))

    return gt_rows, written


def validate(gt_rows, written):
    """Reload the WRITTEN files, merge by row_id, and reproduce the README receipt."""
    gt = json.loads((POOL_DIR / "ground_truth.json").read_text(encoding="utf-8"))["rows"]
    # merged records keyed by row_id -> {condition, error_type, "<slug>_verdict": v, ...}
    merged = {}
    for row in gt:
        cond, etype = _stratum_to_ce(row["stratum"])
        merged[row["row_id"]] = {"idx": row["idx"], "condition": cond, "error_type": etype}
    for slug, _key, _err, path in written:
        vf = json.loads(path.read_text(encoding="utf-8"))
        for v in vf["verdicts"]:
            merged[v["row_id"]][f"{slug}_verdict"] = v["verdict"]
    records = [merged[i] for i in sorted(merged)]

    llama = "Llama-3.3-70B-Instruct_verdict"
    qwen = "Qwen3-32B_verdict"
    nemo = "NVIDIA-Nemotron-3-Nano-30B-A3B_verdict"
    by = vc.delta_by_stratum(records, [llama, qwen], nemo)

    print("Validation — ΔΦ_V per stratum from the WRITTEN audit_pool files:")
    for f in vc.STRATA:
        d = by[f]["delta"]["phi_v"]
        print(f"  {f:10} n={by[f]['n']:>3}  ΔΦ_V={d:+.4f}  "
              f"(Φ_V incumbent {by[f]['phi_incumbent']:.3f} -> full {by[f]['phi_full']:.3f})")

    diag = by["diagnosis"]["delta"]["phi_v"]
    ok = abs(diag - 0.071) <= 1e-3
    print(f"\n  diagnosis ΔΦ_V = {diag:.4f}  |  target 0.071 ± 1e-3  ->  "
          f"{'PASS ✅' if ok else 'FAIL ❌'}")
    return ok


def main():
    if not SOURCE.exists():
        sys.exit(f"source not found: {SOURCE}")
    gt_rows, written = build()
    print(f"Wrote {POOL_DIR / 'ground_truth.json'}  ({len(gt_rows)} rows)")
    for slug, key, errors, path in written:
        print(f"Wrote {path}  (from {key}; {errors} ERROR verdicts preserved)")
    print()
    ok = validate(gt_rows, written)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
