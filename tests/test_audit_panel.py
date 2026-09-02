"""
test_audit_panel.py — regression lock for the /v1/audit_panel core.

Steps 1-3 all validate against the README's published receipt, now through the
REAL pool_loader + selector (not an inline reference):

  Pool = the 3 committed models; incumbent = Llama + Qwen; candidate = Nemotron Nano.
    * recommendation == Nemotron Nano
    * target blind spot == diagnosis (the README's whole thesis)
    * expected Φ_V lift within ±1e-3 of the published +0.071
    * ci_95 == the committed [0.0552, 0.0866] (chained-rng, bit-for-bit)
    * an unseen model id is returned in unseen_candidates, never ranked
  Plus a direct vagt_core check that diagnosis ΔΦ_V ≈ 0.071.

Run:  pytest tests/test_audit_panel.py -q      (offline; no NEBIUS_API_KEY)
"""

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src" / "audit_panel"))
import vagt_core as vc          # noqa: E402
from pool_loader import Pool    # noqa: E402
import selector                 # noqa: E402

LLAMA = "meta-llama/Llama-3.3-70B-Instruct"
QWEN = "Qwen/Qwen3-32B"
NEMOTRON = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
INCUMBENT = [LLAMA, QWEN]


def _pool():
    return Pool.load(REPO / "audit_pool")


def _audit(candidates):
    return selector.audit_panel(_pool(), INCUMBENT, candidates)


# ── vagt_core-level receipt (offline, from the committed pool) ────────────────
def test_diagnosis_delta_phi_v_matches_readme():
    pool = _pool()
    by = vc.delta_by_stratum(pool.records, INCUMBENT, NEMOTRON)
    d = by["diagnosis"]["delta"]["phi_v"]
    assert abs(d - 0.071) <= 1e-3, f"diagnosis dPhi_V={d:.4f}, expected ~0.071"


# ── pool loader ──────────────────────────────────────────────────────────────
def test_pool_loads_three_models():
    pool = _pool()
    assert pool.models == {LLAMA, QWEN, NEMOTRON}
    assert len(pool.records) == 708


# ── selector: recommendation + receipt through the real service path ──────────
def test_recommendation_is_nemotron():
    res = _audit([NEMOTRON])
    assert res["recommendation"]["model"] == NEMOTRON


def test_blindest_stratum_is_diagnosis():
    res = _audit([NEMOTRON])
    assert res["incumbent"]["blindest_stratum"] == "diagnosis"
    assert res["recommendation"]["target_blind_spot"] == "diagnosis"


def test_expected_lift_matches_readme():
    res = _audit([NEMOTRON])
    lift = res["recommendation"]["expected_Phi_V_lift"]
    assert abs(lift - 0.071) <= 1e-3, f"expected_Phi_V_lift={lift}, expected ~0.071"


def test_recommended_ci_matches_committed():
    # chained-rng convention reproduces vagt_bootstrap_cis.json / README exactly
    res = _audit([NEMOTRON])
    lo, hi = res["recommendation"]["ci_95"]
    assert (lo, hi) == (0.0552, 0.0866), f"ci_95={[lo, hi]}, expected [0.0552, 0.0866]"


def test_dose_flagged_not_significant():
    res = _audit([NEMOTRON])
    caveat = res["recommendation"]["caveat"] or ""
    assert "dose" in caveat and "not statistically significant" in caveat


def test_unseen_candidate_not_ranked():
    unseen_id = "some-org/Not-In-Pool-7B"
    res = _audit([NEMOTRON, unseen_id])
    assert unseen_id in res["unseen_candidates"]
    ranked_models = [c["model"] for c in res["candidates_ranked"]]
    assert unseen_id not in ranked_models
    assert res["recommendation"]["model"] == NEMOTRON


def test_diagnosis_delta_ci_excludes_zero():
    pool = _pool()
    keys = INCUMBENT + [NEMOTRON]
    X, tau, _ = vc.stratum(pool.records, "diagnosis", keys)
    rng = np.random.default_rng(vc.SEED)
    _point, cis = vc.paired_delta_cis(X, tau, n_incumbent=len(INCUMBENT), rng=rng)
    lo, hi = cis["phi_v"]
    assert lo > 0, f"diagnosis dPhi_V 95% CI [{lo:.4f}, {hi:.4f}] should exclude 0"
