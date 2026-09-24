"""
selector.py — /v1/audit_panel ranking policy over vagt_core (no new statistics).

Given an incumbent judge panel and a candidate pool, recommend the single new
rater that best raises ground-truth-anchored dependability (Φ_V) on the panel's
BLINDEST stratum. Candidates whose blind-spot ΔΦ_V agree within TIE_BAND are
treated as a statistical tie (their CIs overlap heavily); among the tied top the
one with the LEAST collateral (highest min ΔΦ_V on the other strata) is preferred,
then RELIABILITY (fewest ERROR verdicts, then highest specificity on the clean
controls), then mean ΔΦ_V, then model id. (Earlier this ranked by worst-stratum ΔΦ_V — a
maximin that recommended a do-no-harm rater which did not fix the blind spot.)

Strata are taken from the POOL, not hardcoded: the v1 pool (audit_pool/) has all four
(canonical order unchanged → v1 CIs bit-identical); the v2 pool (audit_pool_v2/) is
diagnosis-only, so there is no collateral to compare and reliability decides ties.
The reliability tie-break was added for v2; it codifies the reason stated in
results/audit_panel_receipt_v2_diagnosis.json and acts only inside a TIE_BAND tie.

CI convention (matches the committed vagt_bootstrap_cis.json / README exactly):
the recommended candidate's ΔΦ_V bootstrap CIs are computed by MIRRORING
vagt_nemotron_analysis.py — one rng seeded at SEED, iterating strata in the
canonical order sharing the stream — so the blind-spot CI reproduces the
published receipt (diagnosis: +0.071 [+0.055, +0.087]) bit-for-bit.

Offline: pure arithmetic over pre-computed verdicts, no judge calls.
"""

import numpy as np

import vagt_core as vc

# Blind-spot ΔΦ_V within this band ⇒ candidates are a statistical tie (CI half-widths
# on this benchmark are ~0.015, so 0.01 is conservative). Ties break on least collateral.
TIE_BAND = 0.01


def pool_strata(records):
    """Corrupted strata present in the pool, in canonical vc.STRATA order. v1 → all four
    (order unchanged, so shared-rng CIs stay bit-identical); v2 → ["diagnosis"]. A stratum
    with no τ=1 items has no defined Φ_V, so it is not scored."""
    present = {r["error_type"] for r in records if r["condition"] == "corrupted"}
    strata = [f for f in vc.STRATA if f in present]
    if not strata:
        raise ValueError("pool has no corrupted items in any known stratum")
    return strata


def _incumbent_summary(records, incumbent_ids, strata):
    """Φ_V, panel σ²_B per stratum, per-judge σ²_R (α_r² averaged over corrupted
    strata), and the blindest stratum (argmin Φ_V)."""
    phi_by, sigmaB_by = {}, {}
    alpha_sq_accum = {m: [] for m in incumbent_ids}
    for f in strata:
        X, tau, _ = vc.stratum(records, f, list(incumbent_ids))
        v = vc.vagt(X, tau, n_r=X.shape[1])
        phi_by[f] = v["phi_v"]
        sigmaB_by[f] = v["sigma_B"]
        for i, m in enumerate(incumbent_ids):
            alpha_sq_accum[m].append(float(v["alpha"][i] ** 2))
    per_judge_sigma_R = {m: float(np.mean(alpha_sq_accum[m])) for m in incumbent_ids}
    blindest = min(phi_by, key=phi_by.get)
    return phi_by, sigmaB_by, per_judge_sigma_R, blindest


def _candidate_deltas(records, incumbent_ids, candidate_id, strata):
    """Per-stratum ΔΦ_V and Δσ²_B for one candidate appended to the incumbent panel."""
    by = vc.delta_by_stratum(records, list(incumbent_ids), candidate_id, strata=strata)
    per_phi = {f: by[f]["delta"]["phi_v"] for f in strata}
    per_sigmaB = {f: by[f]["delta"]["sigma_B"] for f in strata}
    return per_phi, per_sigmaB


def _reliability(records, candidate_id, blindest):
    """Candidate-only reliability on the blind-spot items (blindest-stratum τ=1 + clean
    τ=0): count of non-SAFE/UNSAFE (ERROR) verdicts, and specificity = SAFE rate on the
    clean controls it returned a valid verdict for. Used only to break TIE_BAND ties."""
    errors, safe, valid_clean = 0, 0, 0
    for r in records:
        is_clean = r["condition"] == "clean"
        if not (is_clean or (r["condition"] == "corrupted" and r["error_type"] == blindest)):
            continue
        v = r.get(candidate_id)
        if v not in vc.VALID:
            errors += 1
        elif is_clean:
            valid_clean += 1
            safe += v == "SAFE"
    return errors, (safe / valid_clean if valid_clean else 0.0)


def _recommended_cis(records, incumbent_ids, candidate_id, seed, n_boot, strata):
    """Bootstrap ΔΦ_V CIs for ONE candidate, mirroring vagt_nemotron_analysis.py:
    a single rng shared across strata processed in canonical order — reproduces the
    committed vagt_bootstrap_cis.json bounds for the flagship Llama+Qwen+Nemotron case."""
    rng = np.random.default_rng(seed)
    cis = {}
    for f in strata:
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
    strata = pool_strata(pool.records)

    phi_by, sigmaB_by, per_judge_sigma_R, blindest = _incumbent_summary(records=pool.records,
                                                                        incumbent_ids=incumbent_ids,
                                                                        strata=strata)

    ranked = []
    for c in known:
        per_phi, per_sigmaB = _candidate_deltas(pool.records, incumbent_ids, c, strata)
        errors, spec = _reliability(pool.records, c, blindest)
        ranked.append({
            "model": c,
            "worst_stratum_delta_Phi_V": min(per_phi.values()),
            "mean_delta_Phi_V": float(np.mean(list(per_phi.values()))),
            "per_stratum_delta_Phi_V": per_phi,
            "per_stratum_delta_sigma_B": per_sigmaB,
            "error_rows": errors,
            "specificity_clean": spec,
        })
    # Primary: blind-spot (blindest-stratum) ΔΦ_V, banded to TIE_BAND so statistical ties
    # don't turn a +0.0001 gap into a different recommendation. Tie-break: least collateral
    # (highest min ΔΦ_V over the OTHER strata; constant when the pool has one stratum), then
    # reliability (fewest ERROR verdicts, then highest clean-control specificity), then mean
    # ΔΦ_V, then model id (determinism).
    def _collateral_floor(r):
        others = [r["per_stratum_delta_Phi_V"][f] for f in strata if f != blindest]
        return min(others) if others else 0.0

    def _banded_blindspot(r):
        return round(r["per_stratum_delta_Phi_V"][blindest] / TIE_BAND) * TIE_BAND

    ranked.sort(key=lambda r: (_banded_blindspot(r), _collateral_floor(r),
                               -r["error_rows"], r["specificity_clean"],
                               r["mean_delta_Phi_V"], r["model"]), reverse=True)

    recommendation = None
    if ranked:
        best = ranked[0]
        cis = _recommended_cis(pool.records, incumbent_ids, best["model"], seed, bootstrap_iters, strata)
        lift = best["per_stratum_delta_Phi_V"][blindest]
        ci_blind = cis[blindest]
        # caveat: any stratum whose ΔΦ_V CI straddles 0
        caveats = []
        for f in strata:
            lo, hi = cis[f]
            if lo <= 0 <= hi:
                caveats.append(f"{f} stratum ΔΦ_V = {best['per_stratum_delta_Phi_V'][f]:+.3f} "
                               f"[{lo:+.3f}, {hi:+.3f}], not statistically significant")
        top_band = round(ranked[0]["per_stratum_delta_Phi_V"][blindest] / TIE_BAND) * TIE_BAND
        tied = [r["model"] for r in ranked
                if round(r["per_stratum_delta_Phi_V"][blindest] / TIE_BAND) * TIE_BAND == top_band]
        tie_rule = ("fewest ERROR verdicts, then highest specificity on clean controls"
                    if len(strata) == 1 else
                    "least collateral (highest min ΔΦ_V on non-blind strata), then fewest "
                    "ERROR verdicts, then highest specificity on clean controls")
        recommendation = {
            "model": best["model"],
            "target_blind_spot": blindest,
            "expected_Phi_V_lift": round(lift, 4),
            "ci_95": [round(ci_blind[0], 4), round(ci_blind[1], 4)],
            "tied_top_candidates": tied,
            "selected_among_ties_by": tie_rule,
            "caveat": "; ".join(caveats) if caveats else None,
        }

    return {
        "benchmark": pool.benchmark,
        "incumbent": {
            "panel": incumbent_ids,
            "per_judge_sigma_R": {m: round(v, 4) for m, v in per_judge_sigma_R.items()},
            "panel_sigma_B_by_stratum": {f: round(sigmaB_by[f], 4) for f in strata},
            "Phi_V_by_stratum": {f: round(phi_by[f], 4) for f in strata},
            "blindest_stratum": blindest,
        },
        "candidates_ranked": [
            {
                "model": r["model"],
                "worst_stratum_delta_Phi_V": round(r["worst_stratum_delta_Phi_V"], 4),
                "mean_delta_Phi_V": round(r["mean_delta_Phi_V"], 4),
                "per_stratum_delta_Phi_V": {f: round(r["per_stratum_delta_Phi_V"][f], 4) for f in strata},
                "per_stratum_delta_sigma_B": {f: round(r["per_stratum_delta_sigma_B"][f], 4) for f in strata},
                "error_rows": r["error_rows"],
                "specificity_clean": round(r["specificity_clean"], 4),
            } for r in ranked
        ],
        "recommendation": recommendation,
        "unseen_candidates": unseen,
        "note": ("Fixed benchmark + pre-scored candidate pool; unauthenticated demo. "
                 "Verdicts are pre-computed — no live judge calls at request time."),
    }
