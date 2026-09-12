#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix 1 - per-candidate paired bootstrap CIs on Delta-Phi_V.

For each audit-pool candidate, compute the paired Delta-Phi_V(candidate | Llama+Qwen)
with a 1000-iteration PAIRED item bootstrap 95% CI, per stratum, reusing the committed
audit_pool/ and the EXACT vagt_core estimators (SEED=42, no new math).

This answers the reviewer critique that "scale is irrelevant / saturated at 30B" was
asserted from point estimates with no per-candidate CIs: now every candidate carries
a CI, so the claim can be supported or retired on evidence.

Output:
  - prints a table (candidate x stratum): Delta-Phi_V, 95% CI, CI width
  - writes results/pool_candidate_cis.json
"""
import os
import sys
import json

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Greek/Delta print on legacy Windows codepages
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src", "audit_panel"))

from pool_loader import Pool          # noqa: E402
import vagt_core as vc                # noqa: E402

SEED = 42
N_BOOT = 1000
INCUMBENT = ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen3-32B"]

# (display label, full model id).  The 5 requested candidates, plus the Nano
# reference (recomputed here purely to validate the pipeline against the committed
# receipt CI [0.0552, 0.0866] and to enable the 30B-vs-550B scale comparison).
CANDIDATES = [
    ("gemma-3-27b-it",             "google/gemma-3-27b-it"),
    ("gpt-oss-120b",               "openai/gpt-oss-120b"),
    ("nemotron-3-super-120b-a12b", "nvidia/nemotron-3-super-120b-a12b"),
    ("DeepSeek-V4-Flash-0731",     "deepseek-ai/DeepSeek-V4-Flash-0731"),
    ("Nemotron-3-Ultra-550b-a55b", "nvidia/Nemotron-3-Ultra-550b-a55b"),
]
NANO_REF = ("Nemotron-3-Nano-30B (ref)", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")


def candidate_cis(pool, cand_id):
    per_stratum = {}
    for feature in vc.STRATA:
        keys = INCUMBENT + [cand_id]
        X, tau, dropped = vc.stratum(pool.records, feature, keys)
        rng = np.random.default_rng(SEED)   # fresh, per-candidate reproducible bootstrap
        point, cis = vc.paired_delta_cis(X, tau, n_incumbent=len(INCUMBENT), rng=rng, n_boot=N_BOOT)
        lo, hi = cis["phi_v"]
        per_stratum[feature] = {
            "n": int(X.shape[0]),
            "dropped": int(dropped),
            "delta_phi_v": round(float(point["phi_v"]), 4),
            "ci_95": [round(float(lo), 4), round(float(hi), 4)],
            "ci_width": round(float(hi - lo), 4),
        }
    return per_stratum


def main():
    pool = Pool.load()
    for key in INCUMBENT + [c[1] for c in CANDIDATES] + [NANO_REF[1]]:
        if key not in pool.models:
            raise SystemExit(f"model id not in pool: {key}\navailable: {sorted(pool.models)}")

    results = {}
    for label, cand in CANDIDATES + [NANO_REF]:
        results[label] = {"model": cand, "per_stratum": candidate_cis(pool, cand)}

    out = os.path.join(REPO, "results", "pool_candidate_cis.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"seed": SEED, "n_bootstrap": N_BOOT, "incumbent_panel": INCUMBENT,
                   "metric": "delta_phi_v (paired, candidate vs Llama+Qwen)",
                   "candidates": results}, f, indent=2)

    # ---- print table ----
    print(f"Per-candidate paired ΔΦ_V 95% CI  (incumbent = Llama+Qwen, seed={SEED}, boot={N_BOOT})")
    print("=" * 94)
    print(f"{'candidate':<30}{'stratum':<11}{'n':>5}   {'ΔΦ_V':>8}   {'95% CI':>20}   {'width':>7}  sig")
    print("-" * 94)
    for label, cand in CANDIDATES + [NANO_REF]:
        ps = results[label]["per_stratum"]
        for i, feat in enumerate(vc.STRATA):
            s = ps[feat]
            lo, hi = s["ci_95"]
            excl = lo > 0 or hi < 0
            sig = "  *" if excl else "  ."
            name = label if i == 0 else ""
            ci = f"[{lo:+.4f}, {hi:+.4f}]"
            print(f"{name:<30}{feat:<11}{s['n']:>5}   {s['delta_phi_v']:>+8.4f}   {ci:>20}   {s['ci_width']:>7.4f}{sig}")
        print("-" * 94)
    print("*  = 95% CI excludes 0    .  = CI straddles 0")

    # ---- validation vs committed receipt ----
    nano_diag = results[NANO_REF[0]]["per_stratum"]["diagnosis"]
    print(f"\nValidation: Nano (ref) diagnosis ΔΦ_V = {nano_diag['delta_phi_v']:+.4f} "
          f"CI {nano_diag['ci_95']}  vs committed receipt +0.0706 [0.0552, 0.0866]")

    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
