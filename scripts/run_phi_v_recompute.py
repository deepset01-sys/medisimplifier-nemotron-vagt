"""
run_phi_v_recompute.py — Phi_V (VAGT) recompute on the clean, hand-verified
JudgeBench v2 diagnosis stratum, using vagt_core.py VERBATIM (SEED=42, n_boot=1000).

Incumbent = Llama + Qwen (2-rater); candidate appended = Nemotron (3-rater).
Delta Phi_V = Phi_V(3-rater) - Phi_V(2-rater) = Nemotron's added value, with a
paired item-bootstrap 95% CI.

Cells, for each prompt (deployed, calibration):
  full                120 tau=1 + their 120 paired controls (prevalence 0.50)
  cat0_paired/_all120 the 47 tau=1 with category_retained==0 (even the broad category is gone;
                      a covariate subset, protocol §6 Decision 1) + their 47 paired controls
                      (prevalence 0.50) / + all 120 controls (prevalence 0.28)
  er0_paired/_all120  the 30 tau=1 with expert_recoverable==0 (the protocol's §8 strict tier:
                      the name was the only clue) + their 30 paired controls (0.50) / + all 120
                      controls (0.20)
The paired design matches the full cells' prevalence, so it is the like-for-like comparison.
The all-120 design is reported because an earlier version used it; Phi_V depends on prevalence.
Bands: the protocol's four (docs/judgebench_v2_protocol.md §8), pre-registered for the primary
metric (the full cells) and applied to the subset cells as well.

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
CTRL = _REPO / "results" / "judgebench_v2_clean_controls.json"
OUT = _REPO / "results" / "judgebench_v2_phi_v_recompute.json"

RATER_KEYS = ["llama_verdict", "qwen_verdict", "nemotron_verdict"]  # incumbent=first 2, candidate=last
N_INCUMBENT = 2


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def band(d, lo, hi):
    """Protocol §8 bands (docs/judgebench_v2_protocol.md:139-146), pre-registered for the primary metric."""
    if d >= 0.05 and lo > 0:
        return "POSITIVE"
    if d >= 0.02 and lo > 0:
        return "WEAK-POS"
    if d <= -0.02 and hi < 0:
        return "NEGATIVE"
    if lo <= 0 <= hi and abs(d) < 0.05:
        return "NULL"
    return "OUTSIDE BANDS"


def build_records(per_sample, subset=None, controls="paired", pair_of=None):
    """Records for vagt_core.stratum, in per_sample order. subset: tau=1 idx to keep (None = all).
    controls: 'paired' keeps only the controls paired with a kept drop; 'all' keeps all 120."""
    recs = []
    for r in per_sample:
        if subset is not None:
            if r["tau"] == 1 and str(r["idx"]) not in subset:
                continue
            if r["tau"] == 0 and controls == "paired" and pair_of[str(r["idx"])] not in subset:
                continue
        recs.append(r)
    return recs


def cell(per_sample, subset=None, controls="paired", pair_of=None):
    recs = build_records(per_sample, subset, controls, pair_of)
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
        "prevalence": round(float(tau.mean()), 2),
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
    cat0 = {str(t["idx"]) for t in tau1_items if t["category_retained"] == 0}
    er0 = {str(t["idx"]) for t in tau1_items if t["expert_recoverable"] == 0}
    assert (len(cat0), len(er0)) == (47, 30), (len(cat0), len(er0))
    pair_of = {str(c["idx"]): str(c["paired_with"]) for c in _load(CTRL)["items"]
               if c["control_type"] == "primary_paired"}

    cells = {}
    for name, ps in (("deployed", gate), ("calibration", calib)):
        cells[f"{name}_full"] = cell(ps)
        for sub, ids in (("cat0", cat0), ("er0", er0)):
            cells[f"{name}_{sub}_paired"] = cell(ps, ids, "paired", pair_of)
            cells[f"{name}_{sub}_all120"] = cell(ps, ids, "all", pair_of)

    payload = {
        "purpose": "Phi_V (VAGT) recompute on the clean hand-verified JudgeBench v2 diagnosis stratum.",
        "method": "vagt_core.py verbatim; SEED=42, n_boot=1000; paired item bootstrap; complete-case.",
        "incumbent": "Llama + Qwen (2-rater)", "candidate": "Nemotron (3-rater)",
        "delta_definition": "delta_phi_v = Phi_V(3-rater) - Phi_V(2-rater) = Nemotron's added value",
        "controls": ("full cells: the 120 paired controls. Subset cells: *_paired = only the subset's "
                     "own paired controls (prevalence 0.50, like-for-like with the full cells); "
                     "*_all120 = all 120 controls (prevalence 0.28 for cat0, 0.20 for er0)."),
        "subsets": {"cat0": "category_retained==0 (47): even the broad category is gone; covariate "
                             "subset (protocol §6 Decision 1)",
                    "er0": "expert_recoverable==0 (30): the protocol's §8 strict tier (name was the only clue)"},
        "bands": {"POSITIVE": "delta >= +0.05 AND ci_lower > 0",
                  "WEAK-POS": "+0.02 <= delta < +0.05 AND ci_lower > 0",
                  "NULL": "CI includes 0 AND |delta| < 0.05",
                  "NEGATIVE": "delta <= -0.02 AND ci_upper < 0",
                  "OUTSIDE BANDS": "none of the above (not defined by the protocol)"},
        "bands_scope": "protocol §8 pre-registers these bands for the primary metric (the full cells)",
        "cells": cells,
    }
    json.dump(payload, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ── print table ──
    hdr = f"{'cell':26} {'n':>4} {'pos':>4} {'neg':>4} {'prev':>5} {'Phi2':>7} {'Phi3':>7} {'dPhi':>8} {'95% CI':>18}  band"
    print(hdr)
    print("-" * len(hdr))
    for name, c in cells.items():
        ci = f"[{c['ci95'][0]:+.4f},{c['ci95'][1]:+.4f}]"
        print(f"{name:26} {c['n']:>4} {c['pos_tau1']:>4} {c['neg_tau0']:>4} {c['prevalence']:>5.2f} "
              f"{c['phi_2rater_llama_qwen']:>7.4f} {c['phi_3rater_plus_nemotron']:>7.4f} "
              f"{c['delta_phi_v']:>+8.4f} {ci:>18}  {c['band']}")
    print(f"\nSaved -> {OUT}")


if __name__ == "__main__":
    main()
