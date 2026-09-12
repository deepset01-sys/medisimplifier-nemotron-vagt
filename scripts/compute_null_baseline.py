#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix 2 - null-rater baseline.

Adversarial control for the VAGT finding: does adding *any* high-flagging rater to
the Llama+Qwen panel raise Delta-Phi_V on diagnosis, or does the gain require a rater
whose flags actually TRACK the ground truth (i.e. detection ability)?

Two synthetic null raters are injected as candidate columns, then scored with the
exact same paired 1000-iteration bootstrap CI as the real candidates:
  a. null_unsafe  - constant UNSAFE on every item (flags everything, tracks nothing)
  b. null_random  - UNSAFE with p=0.47 (Nemotron's approx UNSAFE rate on diagnosis),
                    drawn once per item with seed=42, independent of tau

Compared head-to-head with the real Nemotron Nano on the diagnosis stratum.

Output: prints a comparison table + writes results/null_baseline_cis.json.
"""
import os
import sys
import json

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src", "audit_panel"))

from pool_loader import Pool      # noqa: E402
import vagt_core as vc            # noqa: E402

SEED = 42
N_BOOT = 1000
P_UNSAFE = 0.47   # Nemotron's approx UNSAFE rate on the diagnosis stratum
INCUMBENT = ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen3-32B"]
NANO = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"


def inject_nulls(records):
    """Add two synthetic rater columns to every record (in place)."""
    rng = np.random.default_rng(SEED)
    for r in records:
        r["null_unsafe"] = "UNSAFE"
        r["null_random"] = "UNSAFE" if rng.random() < P_UNSAFE else "SAFE"


def cis_for(records, cand):
    per = {}
    for feat in vc.STRATA:
        X, tau, dropped = vc.stratum(records, feat, INCUMBENT + [cand])
        rng = np.random.default_rng(SEED)
        point, cis = vc.paired_delta_cis(X, tau, n_incumbent=len(INCUMBENT), rng=rng, n_boot=N_BOOT)
        lo, hi = cis["phi_v"]
        per[feat] = {
            "n": int(X.shape[0]),
            "delta_phi_v": round(float(point["phi_v"]), 4),
            "ci_95": [round(float(lo), 4), round(float(hi), 4)],
            "ci_width": round(float(hi - lo), 4),
        }
    return per


def main():
    pool = Pool.load()
    inject_nulls(pool.records)
    realized = sum(1 for r in pool.records if r["null_random"] == "UNSAFE") / len(pool.records)

    raters = [
        ("null_unsafe (constant UNSAFE)", "null_unsafe"),
        ("null_random (p=0.47)", "null_random"),
        ("Nemotron Nano (real)", NANO),
    ]
    results = {}
    for label, cand in raters:
        results[label] = {"model": cand, "per_stratum": cis_for(pool.records, cand)}

    out = os.path.join(REPO, "results", "null_baseline_cis.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"seed": SEED, "n_bootstrap": N_BOOT, "p_unsafe_target": P_UNSAFE,
                   "null_random_realized_prevalence": round(realized, 4),
                   "incumbent_panel": INCUMBENT, "raters": results}, f, indent=2)

    # ---- full table ----
    print(f"Null-rater baseline vs Nemotron  (incumbent = Llama+Qwen, seed={SEED}, boot={N_BOOT})")
    print(f"null_random realized prevalence: {realized:.3f}  (target {P_UNSAFE})")
    print("=" * 88)
    print(f"{'rater':<32}{'stratum':<11}{'n':>5}   {'ΔΦ_V':>8}   {'95% CI':>20}  sig")
    print("-" * 88)
    for label, _cand in raters:
        ps = results[label]["per_stratum"]
        for i, feat in enumerate(vc.STRATA):
            s = ps[feat]
            lo, hi = s["ci_95"]
            sig = "  *" if (lo > 0 or hi < 0) else "  ."
            name = label if i == 0 else ""
            print(f"{name:<32}{feat:<11}{s['n']:>5}   {s['delta_phi_v']:>+8.4f}   "
                  f"[{lo:+.4f}, {hi:+.4f}]{sig}")
        print("-" * 88)
    print("*  = 95% CI excludes 0    .  = CI straddles 0")

    # ---- headline: diagnosis comparison ----
    print("\n" + "=" * 88)
    print("DIAGNOSIS STRATUM — the finding's blind spot (head-to-head):")
    for label, _cand in raters:
        d = results[label]["per_stratum"]["diagnosis"]
        print(f"  {label:<32} ΔΦ_V {d['delta_phi_v']:>+.4f}  CI [{d['ci_95'][0]:+.4f}, {d['ci_95'][1]:+.4f}]")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
