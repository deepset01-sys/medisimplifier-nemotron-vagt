"""
selector.py — /v1/audit_panel ranking policy over vagt_core (no new statistics).

Given an incumbent judge panel and a candidate pool, recommend the single new
rater that best raises ground-truth-anchored dependability (Φ_V) on the panel's
BLINDEST stratum, scored by worst-stratum ΔΦ_V (spec §1).

CI convention (matches the committed vagt_bootstrap_cis.json / README exactly):
the recommended candidate's ΔΦ_V bootstrap CIs are computed by MIRRORING
vagt_nemotron_analysis.py — one rng seeded at SEED, iterating strata in the
canonical order sharing the stream — so the blind-spot CI reproduces the
published receipt (diagnosis: +0.071 [+0.055, +0.087]) bit-for-bit.

Offline: pure arithmetic over pre-computed verdicts, no judge calls.
"""

import numpy as np

import vagt_core as vc


def _incumbent_summary(records, incumbent_ids):
    """Φ_V, panel σ²_B per stratum, per-judge σ²_R (α_r² averaged over corrupted
    strata), and the blindest stratum (argmin Φ_V)."""
    phi_by, sigmaB_by = {}, {}
    alpha_sq_accum = {m: [] for m in incumbent_ids}
    for f in vc.STRATA:
        X, tau, _ = vc.stratum(records, f, list(incumbent_ids))
        v = vc.vagt(X, tau, n_r=X.shape[1])
        phi_by[f] = v["phi_v"]
        sigmaB_by[f] = v["sigma_B"]
        for i, m in enumerate(incumbent_ids):
            alpha_sq_accum[m].append(float(v["alpha"][i] ** 2))
    per_judge_sigma_R = {m: float(np.mean(alpha_sq_accum[m])) for m in incumbent_ids}
    blindest = min(phi_by, key=phi_by.get)
    return phi_by, sigmaB_by, per_judge_sigma_R, blindest


def _candidate_deltas(records, incumbent_ids, candidate_id):
    """Per-stratum ΔΦ_V and Δσ²_B for one candidate appended to the incumbent panel."""
    by = vc.delta_by_stratum(records, list(incumbent_ids), candidate_id)
    per_phi = {f: by[f]["delta"]["phi_v"] for f in vc.STRATA}
    per_sigmaB = {f: by[f]["delta"]["sigma_B"] for f in vc.STRATA}
    return per_phi, per_sigmaB


def _recommended_cis(records, incumbent_ids, candidate_id, seed, n_boot):
    """Bootstrap ΔΦ_V CIs for ONE candidate, mirroring vagt_nemotron_analysis.py:
    a single rng shared across strata processed in canonical order — reproduces the
    committed vagt_bootstrap_cis.json bounds for the flagship Llama+Qwen+Nemotron case."""
    rng = np.random.default_rng(seed)
    cis = {}
    for f in vc.STRATA:
        X, tau, _ = vc.stratum(records, f, list(incumbent_ids) + [candidate_id])
        _point, ci = vc.paired_delta_cis(X, tau, n_incumbent=len(incumbent_ids),
                                         rng=rng, n_boot=n_boot)
        cis[f] = ci["phi_v"]
    return cis


def audit_panel(pool, incumbent_panel, candidate_pool, bootstrap_iters=vc.N_BOOT,
                seed=vc.SEED):
    """Rank the candidate pool for the incumbent panel and recommend a third rater.

    Returns a plain dict matching the /v1/audit_panel response contract. Pure CPU;
    no Token Factory calls (all verdicts are pre-computed in `pool`)."""
    incumbent_ids = pool.known(incumbent_panel)
    missing_incumbents = pool.unseen(incumbent_panel)
    if missing_incumbents:
        raise ValueError(f"incumbent judges not in pool: {missing_incumbents}")
    if len(incumbent_ids) < 2:
        raise ValueError("incumbent_panel must have >= 2 pooled judges")

    known = [c for c in pool.known(candidate_pool) if c not in incumbent_ids]
    unseen = pool.unseen(candidate_pool)

    phi_by, sigmaB_by, per_judge_sigma_R, blindest = _incumbent_summary(records=pool.records,
                                                                        incumbent_ids=incumbent_ids)

    ranked = []
    for c in known:
        per_phi, per_sigmaB = _candidate_deltas(pool.records, incumbent_ids, c)
        ranked.append({
            "model": c,
            "worst_stratum_delta_Phi_V": min(per_phi.values()),
            "mean_delta_Phi_V": float(np.mean(list(per_phi.values()))),
            "per_stratum_delta_Phi_V": per_phi,
            "per_stratum_delta_sigma_B": per_sigmaB,
        })
    # worst-stratum ΔΦ_V; tiebreak mean ΔΦ_V, then -Δσ²_B on the blindest incumbent stratum
    ranked.sort(key=lambda r: (r["worst_stratum_delta_Phi_V"], r["mean_delta_Phi_V"],
                               -r["per_stratum_delta_sigma_B"][blindest]), reverse=True)

    recommendation = None
    if ranked:
        best = ranked[0]
        cis = _recommended_cis(pool.records, incumbent_ids, best["model"], seed, bootstrap_iters)
        lift = best["per_stratum_delta_Phi_V"][blindest]
        ci_blind = cis[blindest]
        # caveat: any stratum whose ΔΦ_V CI straddles 0
        caveats = []
        for f in vc.STRATA:
            lo, hi = cis[f]
            if lo <= 0 <= hi:
                caveats.append(f"{f} stratum ΔΦ_V = {best['per_stratum_delta_Phi_V'][f]:+.3f} "
                               f"[{lo:+.3f}, {hi:+.3f}], not statistically significant")
        recommendation = {
            "model": best["model"],
            "target_blind_spot": blindest,
            "expected_Phi_V_lift": round(lift, 4),
            "ci_95": [round(ci_blind[0], 4), round(ci_blind[1], 4)],
            "caveat": "; ".join(caveats) if caveats else None,
        }

    return {
        "benchmark": pool.benchmark,
        "incumbent": {
            "panel": incumbent_ids,
            "per_judge_sigma_R": {m: round(v, 4) for m, v in per_judge_sigma_R.items()},
            "panel_sigma_B_by_stratum": {f: round(sigmaB_by[f], 4) for f in vc.STRATA},
            "Phi_V_by_stratum": {f: round(phi_by[f], 4) for f in vc.STRATA},
            "blindest_stratum": blindest,
        },
        "candidates_ranked": [
            {
                "model": r["model"],
                "worst_stratum_delta_Phi_V": round(r["worst_stratum_delta_Phi_V"], 4),
                "mean_delta_Phi_V": round(r["mean_delta_Phi_V"], 4),
                "per_stratum_delta_Phi_V": {f: round(r["per_stratum_delta_Phi_V"][f], 4) for f in vc.STRATA},
                "per_stratum_delta_sigma_B": {f: round(r["per_stratum_delta_sigma_B"][f], 4) for f in vc.STRATA},
            } for r in ranked
        ],
        "recommendation": recommendation,
        "unseen_candidates": unseen,
        "note": ("Fixed benchmark + pre-scored candidate pool; unauthenticated demo. "
                 "Verdicts are pre-computed — no live judge calls at request time."),
    }
