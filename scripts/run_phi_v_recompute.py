"""
run_phi_v_recompute.py — Phi_V (VAGT) recompute on the clean, hand-verified
JudgeBench v2 diagnosis stratum, using vagt_core.py VERBATIM (SEED=42, n_boot=1000).

Incumbent = Llama + Qwen (2-rater); candidate appended = Nemotron (3-rater).
Delta Phi_V = Phi_V(3-rater) - Phi_V(2-rater) = Nemotron's added value, with a
paired item-bootstrap 95% CI.

4 cells (all use the 120 tau=0 clean controls):
  1. deployed    / full   (120 tau=1)
  2. deployed    / strict (47 tau=1, category_retained==0)
  3. calibration / full   (120 tau=1)
  4. calibration / strict (47 tau=1, category_retained==0)

Deterministic, no API calls.
"""
import json
import io
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
from audit_panel import vagt_core as V  # noqa: E402

GATE = _REPO / "results" / "judgebench_v2_panel_gate.json"
CALIB = _REPO / "results" / "judgebench_v2_panel_calib.json"
TAU1 = _REPO / "results" / "judgebench_v2_tau1_final.json"
OUT = _REPO / "results" / "judgebench_v2_phi_v_recompute.json"

RATER_KEYS = ["llama_verdict", "qwen_verdict", "nemotron_verdict"]  # incumbent=first 2, candidate=last
N_INCUMBENT = 2


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def band(delta, lo, hi):
    if delta >= 0.05 and lo > 0:
        return "POSITIVE"
    if delta <= -0.02 and hi < 0:
        return "NEGATIVE"
    return "NULL"


def build_records(per_sample, cat0_idx=None):
    """Return records for vagt_core.stratum. If cat0_idx given, restrict tau=1 rows
    to those idx (strict subset); keep ALL tau=0 clean controls."""
    recs = []
    for r in per_sample:
        if r["tau"] == 1:
            if cat0_idx is not None and str(r["idx"]) not in cat0_idx:
                continue
        recs.append(r)
    return recs


def cell(per_sample, cat0_idx=None):
    recs = build_records(per_sample, cat0_idx)
    X, tau, dropped = V.stratum(recs, "diagnosis", RATER_KEYS)
    phi2 = V.all_stats(X[:, :N_INCUMBENT], tau)["phi_v"]
    phi3 = V.all_stats(X, tau)["phi_v"]
    point, cis = V.paired_delta_cis(X, tau, N_INCUMBENT,
                                    np.random.default_rng(V.SEED), n_boot=V.N_BOOT)
    delta = point["phi_v"]
    lo, hi = cis["phi_v"]
    return {
        "n": int(X.shape[0]),
        "pos_tau1": int(tau.sum()),
        "neg_tau0": int((tau == 0).sum()),
        "dropped_incomplete": int(dropped),
        "phi_2rater_llama_qwen": round(float(phi2), 4),
        "phi_3rater_plus_nemotron": round(float(phi3), 4),
        "delta_phi_v": round(float(delta), 4),
        "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "band": band(delta, lo, hi),
    }


def main():
    gate = _load(GATE)["per_sample"]
    calib = _load(CALIB)["per_sample"]
    tau1_items = _load(TAU1)["items"]
    cat0_idx = {str(t["idx"]) for t in tau1_items if t["category_retained"] == 0}
    assert len(cat0_idx) == 47, f"expected 47 cat=0 idx, got {len(cat0_idx)}"

    cells = {
        "deployed_full":     cell(gate),
        "deployed_strict":   cell(gate, cat0_idx),
        "calibration_full":  cell(calib),
        "calibration_strict": cell(calib, cat0_idx),
    }

    payload = {
        "purpose": "Phi_V (VAGT) recompute on the clean hand-verified JudgeBench v2 diagnosis stratum.",
        "method": "vagt_core.py verbatim; SEED=42, n_boot=1000; paired item bootstrap; complete-case.",
        "incumbent": "Llama + Qwen (2-rater)", "candidate": "Nemotron (3-rater)",
        "delta_definition": "delta_phi_v = Phi_V(3-rater) - Phi_V(2-rater) = Nemotron's added value",
        "controls": "all 120 tau=0 clean controls in every cell (option a)",
        "bands": {"POSITIVE": "delta >= +0.05 AND ci_lower > 0",
                  "NEGATIVE": "delta <= -0.02 AND ci_upper < 0",
                  "NULL": "CI includes 0 (otherwise)"},
        "cells": cells,
    }
    json.dump(payload, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ── print table ──
    hdr = f"{'cell':22} {'n':>4} {'pos':>4} {'neg':>4} {'Phi2':>7} {'Phi3':>7} {'dPhi':>8} {'95% CI':>18}  band"
    print(hdr)
    print("-" * len(hdr))
    for name, c in cells.items():
        ci = f"[{c['ci95'][0]:+.4f},{c['ci95'][1]:+.4f}]"
        print(f"{name:22} {c['n']:>4} {c['pos_tau1']:>4} {c['neg_tau0']:>4} "
              f"{c['phi_2rater_llama_qwen']:>7.4f} {c['phi_3rater_plus_nemotron']:>7.4f} "
              f"{c['delta_phi_v']:>+8.4f} {ci:>18}  {c['band']}")
    print(f"\nSaved -> {OUT}")


if __name__ == "__main__":
    main()
