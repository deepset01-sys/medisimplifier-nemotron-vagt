"""
test_audit_panel.py — regression lock for the /v1/audit_panel core.

TWO layers:
  • test_v1_historical_* — lock the v1 CONTAMINATED pool (audit_pool/, 708 rows) + the
    originally-published receipt for REPRODUCIBILITY. These numbers (+0.071, Nemotron-Nano,
    CI [0.0552, 0.0866]) are a KNOWN label-contamination artifact — kept only so the v1
    code path stays bit-for-bit reproducible, NOT as the current recommendation.
  • test_v2_* — the CURRENT truth, on the clean hand-verified JudgeBench v2 diagnosis
    stratum (120 τ=1 + 120 paired τ=0). CURRENT RECOMMENDATION: openai/gpt-oss-120b
    (ΔΦ_V ≈ +0.1220). See results/audit_panel_receipt_v2_diagnosis.json. These read the
    committed v2 result files (SKIP if absent).
  • test_v2_pool_* — the SELECTOR on audit_pool_v2/ (what the redeployed endpoint serves).

Unchanged: blindest-stratum, CI-excludes-zero, pool-loader, unseen-candidate, endpoint,
and health tests (not refuted by v2).

Run:  pytest tests/test_audit_panel.py -q      (offline; no NEBIUS_API_KEY)
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src" / "audit_panel"))
import vagt_core as vc          # noqa: E402
from pool_loader import Pool    # noqa: E402
import selector                 # noqa: E402

LLAMA = "meta-llama/Llama-3.3-70B-Instruct"
QWEN = "Qwen/Qwen3-32B"
NEMOTRON = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
GEMMA = "google/gemma-3-27b-it"
GPT_OSS = "openai/gpt-oss-120b"
SUPER = "nvidia/nemotron-3-super-120b-a12b"
DEEPSEEK = "deepseek-ai/DeepSeek-V4-Flash-0731"
ULTRA = "nvidia/Nemotron-3-Ultra-550b-a55b"
INCUMBENT = [LLAMA, QWEN]
ALL_EIGHT = {LLAMA, QWEN, NEMOTRON, GEMMA, GPT_OSS, SUPER, DEEPSEEK, ULTRA}
CANDIDATES = [NEMOTRON, GEMMA, GPT_OSS, SUPER, DEEPSEEK, ULTRA]  # non-incumbent pool

V2_POOL_TABLE = REPO / "results" / "judgebench_v2_pool_table.json"
V2_POOL = REPO / "audit_pool_v2"


def _pool():
    return Pool.load(REPO / "audit_pool")


def _v2_pool():
    return Pool.load(V2_POOL)


def _audit_v2(candidates, incumbent=INCUMBENT):
    return selector.audit_panel(_v2_pool(), incumbent, candidates)


def _audit(candidates):
    return selector.audit_panel(_pool(), INCUMBENT, candidates)


def _client():
    sys.path.insert(0, str(REPO / "src"))
    from fastapi.testclient import TestClient
    import safe_endpoint
    return TestClient(safe_endpoint.app)


def _v2_rows():
    """{model -> pool-table row} from the v2 recompute; skip if the untracked file is absent."""
    if not V2_POOL_TABLE.is_file():
        pytest.skip("v2 pool table not present (untracked results file) — run scripts/run_pool_judgebench_v2.py")
    data = json.loads(V2_POOL_TABLE.read_text(encoding="utf-8"))
    return {r["model"]: r for r in data["candidates_ranked"]}


# ══════════════════════════════════════════════════════════════════════════════
# v1 HISTORICAL — locks the CONTAMINATED pool + published receipt (reproducibility only).
# These are a known label-contamination artifact, SUPERSEDED by the v2 group below.
# ══════════════════════════════════════════════════════════════════════════════
def test_v1_historical_diagnosis_delta_phi_v():
    # v1 contaminated pool result (superseded by v2 +0.1220): diagnosis ΔΦ_V ≈ +0.071.
    pool = _pool()
    by = vc.delta_by_stratum(pool.records, INCUMBENT, NEMOTRON)
    d = by["diagnosis"]["delta"]["phi_v"]
    assert abs(d - 0.071) <= 1e-3, f"v1 diagnosis dPhi_V={d:.4f}, expected ~0.071"


def test_v1_historical_recommendation_is_nemotron():
    # v1 pool recommends Nemotron Nano (contaminated labels); single candidate → trivially picked.
    res = _audit([NEMOTRON])
    assert res["recommendation"]["model"] == NEMOTRON


def test_v1_historical_full_pool_recommends_nemotron():
    # v1 pool recommends Nemotron Nano (contaminated labels) — NOT gemma. On CLEAN v2 labels this
    # recommendation changes to gpt-oss/DeepSeek (see test_v2_* + audit_panel_receipt_v2_diagnosis.json);
    # this assertion is retained only to lock the v1 maximin code path.
    res = _audit(CANDIDATES)
    assert res["recommendation"]["model"] == NEMOTRON
    assert res["recommendation"]["model"] != GEMMA
    assert abs(res["recommendation"]["expected_Phi_V_lift"] - 0.071) <= 1e-3
    assert res["recommendation"]["ci_95"] == [0.0552, 0.0866]
    assert set(res["recommendation"]["tied_top_candidates"]) >= {NEMOTRON, GPT_OSS, ULTRA}
    assert [c["model"] for c in res["candidates_ranked"]][-1] == GEMMA


def test_v1_historical_expected_lift():
    # v1 contaminated-pool receipt lift ≈ +0.071 (superseded by v2 +0.1220).
    res = _audit([NEMOTRON])
    lift = res["recommendation"]["expected_Phi_V_lift"]
    assert abs(lift - 0.071) <= 1e-3, f"v1 expected_Phi_V_lift={lift}, expected ~0.071"


def test_v1_historical_recommended_ci():
    # chained-rng convention reproduces vagt_bootstrap_cis.json / v1 receipt exactly.
    res = _audit([NEMOTRON])
    lo, hi = res["recommendation"]["ci_95"]
    assert (lo, hi) == (0.0552, 0.0866), f"v1 ci_95={[lo, hi]}, expected [0.0552, 0.0866]"


def test_v1_historical_dose_not_significant():
    # v1 multi-stratum caveat (v2 receipt is diagnosis-only).
    res = _audit([NEMOTRON])
    caveat = res["recommendation"]["caveat"] or ""
    assert "dose" in caveat and "not statistically significant" in caveat


def test_v1_historical_endpoint_receipt():
    # Runs in-process on the DEFAULT pool (AUDIT_POOL_DIR unset → v1 audit_pool/), so it locks
    # the historical v1 receipt (Nano/+0.071/CI). The deployed always-on service sets
    # AUDIT_POOL_DIR=audit_pool_v2; its v2 answer is locked by test_v2_pool_* and captured in
    # results/audit_panel_live_receipt_v2.json. (Run the suite with AUDIT_POOL_DIR unset.)
    body = {"incumbent_panel": INCUMBENT, "candidate_pool": [NEMOTRON]}
    r = _client().post("/v1/audit_panel", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["recommendation"]["model"] == NEMOTRON
    assert data["recommendation"]["target_blind_spot"] == "diagnosis"
    assert abs(data["recommendation"]["expected_Phi_V_lift"] - 0.071) <= 1e-3
    assert data["recommendation"]["ci_95"] == [0.0552, 0.0866]


# ══════════════════════════════════════════════════════════════════════════════
# v2 CURRENT — clean hand-verified diagnosis stratum (results/judgebench_v2_pool_table.json).
# CURRENT RECOMMENDATION: openai/gpt-oss-120b (ΔΦ_V ≈ +0.1220).
# ══════════════════════════════════════════════════════════════════════════════
def test_v2_gpt_oss_delta_phi_v():
    d = _v2_rows()[GPT_OSS]["delta_phi_v"]
    assert abs(d - 0.122) <= 0.002, f"v2 gpt-oss ΔΦ_V={d:.4f}, expected ~0.122"


def test_v2_gpt_oss_ci_lower_above_0_10():
    lo = _v2_rows()[GPT_OSS]["ci95"][0]
    # v2 gpt-oss CI is [+0.1000, +0.1416]; lower bound sits AT 0.10 (rounded) → assert >= 0.10.
    assert lo >= 0.10, f"v2 gpt-oss CI lower={lo:.4f}, expected >= 0.10"


def test_v2_top_tier_outranks_nano():
    rows = _v2_rows()
    nano = rows[NEMOTRON]["delta_phi_v"]
    assert rows[GPT_OSS]["delta_phi_v"] > nano, "gpt-oss should out-rank Nano on clean v2 labels"
    assert rows[DEEPSEEK]["delta_phi_v"] > nano, "DeepSeek should out-rank Nano on clean v2 labels"


def test_v2_gemma_is_null():
    lo, hi = _v2_rows()[GEMMA]["ci95"]
    assert lo <= 0.0 <= hi, f"v2 gemma CI [{lo:.4f}, {hi:.4f}] should include 0 (null)"


def test_v2_recommended_ci_excludes_zero():
    lo = _v2_rows()[GPT_OSS]["ci95"][0]
    assert lo > 0.0, f"v2 gpt-oss diagnosis ΔΦ_V CI lower={lo:.4f} should exclude 0"


# ══════════════════════════════════════════════════════════════════════════════
# v2 POOL — selector over audit_pool_v2/ (diagnosis-only, reliability tie-break).
# ══════════════════════════════════════════════════════════════════════════════
def test_v2_pool_loads_240_rows_eight_models():
    pool = _v2_pool()
    assert pool.benchmark == "MedSimp-JudgeBench-v2"
    assert pool.models == ALL_EIGHT
    assert len(pool.records) == 240


def test_v2_pool_strata_diagnosis_only_v1_unchanged():
    assert selector.pool_strata(_v2_pool().records) == ["diagnosis"]
    assert selector.pool_strata(_pool().records) == vc.STRATA


def test_v2_pool_recommends_gpt_oss():
    rec = _audit_v2(CANDIDATES)["recommendation"]
    assert rec["model"] == GPT_OSS
    assert rec["target_blind_spot"] == "diagnosis"
    assert rec["expected_Phi_V_lift"] == 0.122
    assert rec["ci_95"] == [0.1, 0.1416]
    assert set(rec["tied_top_candidates"]) >= {GPT_OSS, DEEPSEEK}
    assert rec["caveat"] is None


def test_v2_pool_tiebreak_is_reliability():
    ranked = {c["model"]: c for c in _audit_v2(CANDIDATES)["candidates_ranked"]}
    assert ranked[DEEPSEEK]["error_rows"] == 7 and ranked[GPT_OSS]["error_rows"] == 0
    assert ranked[GPT_OSS]["specificity_clean"] > ranked[DEEPSEEK]["specificity_clean"]


def test_v2_pool_ranked_deltas_match_pool_table():
    rows = _v2_rows()
    ranked = {c["model"]: c for c in _audit_v2(CANDIDATES)["candidates_ranked"]}
    for model, row in rows.items():
        assert ranked[model]["per_stratum_delta_Phi_V"]["diagnosis"] == row["delta_phi_v"], model


def test_pool_dir_env_resolution(monkeypatch):
    import router
    monkeypatch.setenv("AUDIT_POOL_DIR", "audit_pool_v2")
    assert router.resolve_pool_dir() == REPO / "audit_pool_v2"
    monkeypatch.delenv("AUDIT_POOL_DIR")
    assert router.resolve_pool_dir() is None


# ══════════════════════════════════════════════════════════════════════════════
# UNCHANGED — not refuted by v2 (hold on both v1 and v2).
# ══════════════════════════════════════════════════════════════════════════════
def test_pool_loads_all_eight_models():
    pool = _pool()
    assert pool.models == ALL_EIGHT
    assert len(pool.records) == 708


def test_blindest_stratum_is_diagnosis():
    res = _audit([NEMOTRON])
    assert res["incumbent"]["blindest_stratum"] == "diagnosis"
    assert res["recommendation"]["target_blind_spot"] == "diagnosis"


def test_diagnosis_delta_ci_excludes_zero():
    pool = _pool()
    keys = INCUMBENT + [NEMOTRON]
    X, tau, _ = vc.stratum(pool.records, "diagnosis", keys)
    rng = np.random.default_rng(vc.SEED)
    _point, cis = vc.paired_delta_cis(X, tau, n_incumbent=len(INCUMBENT), rng=rng)
    lo, hi = cis["phi_v"]
    assert lo > 0, f"diagnosis dPhi_V 95% CI [{lo:.4f}, {hi:.4f}] should exclude 0"


def test_unseen_candidate_not_ranked():
    unseen_id = "some-org/Not-In-Pool-7B"
    res = _audit([NEMOTRON, unseen_id])
    assert unseen_id in res["unseen_candidates"]
    ranked_models = [c["model"] for c in res["candidates_ranked"]]
    assert unseen_id not in ranked_models
    assert res["recommendation"]["model"] == NEMOTRON


def test_endpoint_rejects_unknown_benchmark():
    body = {"incumbent_panel": INCUMBENT, "candidate_pool": [NEMOTRON], "benchmark": "Other"}
    r = _client().post("/v1/audit_panel", json=body)
    assert r.status_code == 422


def test_endpoint_unseen_candidate():
    body = {"incumbent_panel": INCUMBENT, "candidate_pool": [NEMOTRON, "x/Not-Pooled-7B"]}
    r = _client().post("/v1/audit_panel", json=body)
    assert r.status_code == 200, r.text
    assert "x/Not-Pooled-7B" in r.json()["unseen_candidates"]


def test_health_has_audit_panel_field():
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json().get("audit_panel") is True
