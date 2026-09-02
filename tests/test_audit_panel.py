"""
test_audit_panel.py — Step-1 regression lock.

Confirms the GENERALIZED vagt_core reproduces the README's published receipt
BEFORE any selector/endpoint code is built on it:

  Incumbent panel = Llama + Qwen; sole candidate = Nemotron Nano.
    * recommendation == Nemotron Nano
    * diagnosis-stratum ΔΦ_V within ±1e-3 of the published +0.071
    * incumbent blind spot == diagnosis (the README's whole thesis)
    * diagnosis ΔΦ_V 95% CI excludes 0

The `_rank` helper below is a REFERENCE implementation of the spec's worst-stratum
selection; src/audit_panel/selector.py (step 3) will formalize it and this test
will switch to importing it.

Run:  pytest tests/test_audit_panel.py -q      (offline; no NEBIUS_API_KEY)
"""

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src" / "audit_panel"))
import vagt_core as vc  # noqa: E402

DATA = REPO / "nemotron_calibration_full.json"
INCUMBENT = ["llama_verdict", "qwen_verdict"]
NEMOTRON_ID = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
CANDIDATES = {NEMOTRON_ID: "nemotron_verdict"}


def _load():
    recs = json.loads(DATA.read_text(encoding="utf-8"))
    return recs["per_sample"] if isinstance(recs, dict) else recs


def _rank(records, incumbent_keys, candidate_map):
    """Reference: worst-stratum ΔΦ_V; tiebreak on mean ΔΦ_V (spec §1)."""
    inc_phi = vc.incumbent_phi_by_stratum(records, incumbent_keys)
    blindest = min(inc_phi, key=inc_phi.get)
    ranked = []
    for model, key in candidate_map.items():
        by = vc.delta_by_stratum(records, incumbent_keys, key)
        per = {f: by[f]["delta"]["phi_v"] for f in by}
        ranked.append({
            "model": model,
            "worst_stratum_delta_phi_v": min(per.values()),
            "mean_delta_phi_v": float(np.mean(list(per.values()))),
            "per_stratum_delta_phi_v": per,
        })
    ranked.sort(key=lambda r: (r["worst_stratum_delta_phi_v"], r["mean_delta_phi_v"]),
                reverse=True)
    best = ranked[0]
    return {
        "blindest_stratum": blindest,
        "recommendation": {
            "model": best["model"],
            "target_blind_spot": blindest,
            "expected_phi_v_lift": best["per_stratum_delta_phi_v"][blindest],
        },
        "ranked": ranked,
    }


def test_recommendation_is_nemotron():
    result = _rank(_load(), INCUMBENT, CANDIDATES)
    assert result["recommendation"]["model"] == NEMOTRON_ID


def test_diagnosis_delta_phi_v_matches_readme():
    by = vc.delta_by_stratum(_load(), INCUMBENT, "nemotron_verdict")
    d = by["diagnosis"]["delta"]["phi_v"]
    assert abs(d - 0.071) <= 1e-3, f"diagnosis dPhi_V={d:.4f}, expected ~0.071"


def test_blindest_stratum_is_diagnosis():
    result = _rank(_load(), INCUMBENT, CANDIDATES)
    assert result["blindest_stratum"] == "diagnosis"


def test_diagnosis_delta_ci_excludes_zero():
    recs = _load()
    keys = INCUMBENT + ["nemotron_verdict"]
    X, tau, _ = vc.stratum(recs, "diagnosis", keys)
    rng = np.random.default_rng(vc.SEED)
    _point, cis = vc.paired_delta_cis(X, tau, n_incumbent=len(INCUMBENT), rng=rng)
    lo, hi = cis["phi_v"]
    assert lo > 0, f"diagnosis dPhi_V 95% CI [{lo:.4f}, {hi:.4f}] should exclude 0"
