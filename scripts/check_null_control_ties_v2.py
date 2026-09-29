"""
check_null_control_ties_v2.py — ties between the real ΔΦ_V and its τ-blind permutation null.

run_null_control_v2.py reports p = (#{null >= real} + 1) / (N_PERM + 1), comparing floats exactly.
In results/judgebench_v2_null_control.json, nemotron-3-super-120b-a12b has null_max equal to
real_delta_phi_v (0.048): one shuffle gives the same ΔΦ_V as the real column.

Why the ties are exact: a shuffle keeps the candidate's flag count, so σ²_R and σ²_τ are fixed, and
while σ²_B is not clamped at 0, Φ_V = σ²_τ / (σ²_τ + mean b² + σ²_R/R) (the σ²_N terms cancel,
vagt_core.vagt). With c = (l + q + x)/3, mean b² depends on the candidate column x only through the
integer S = Σ x_i (l_i + q_i − 3 τ_i), and Φ_V falls as S rises. A shuffle with the same S as the
real column gives the same ΔΦ_V in exact arithmetic; one with a smaller S gives a larger ΔΦ_V.

Why the committed Super p is 0.001 and a re-run gives 0.002: the σ²_N terms cancel only in exact
arithmetic. judgebench_v2_null_control.json was generated before vagt_core's σ²_N estimator changed
from mean ε² to Σε² / ((N−1)(R−1)) (README A4). With the earlier estimator, the float ΔΦ_V of Super's
tied shuffle comes out just below the real one, so `nulls >= real` leaves it out (p = 0.001); with the
current estimator the two floats are equal, so it is counted (p = 0.002). Both are computed here:
`vagt_mean_eps2` is vagt_core.vagt with the earlier σ²_N line, and the script asserts that its exact
comparison reproduces every committed perm_p_value.

This regenerates run_null_control_v2.py's permutation stream in memory (same functions, same
generator, same candidate order; its main() is not called, so the committed file is not touched),
asserts that it reproduces every committed field, and counts, per candidate, the shuffles above the
real ΔΦ_V and those tied with it — on S, and cross-checked with a 1e-9 tolerance on ΔΦ_V. It then gives
p both ways: ties counted as >= (the rule run_null_control_v2.py states) and ties excluded.
Deterministic (SEED=42 via vagt_core), no API calls.
"""
import io
import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))
from audit_panel import vagt_core as V   # noqa: E402
import run_null_control_v2 as NC          # noqa: E402  (functions only; main() is not run)

COMMITTED = _REPO / "results" / "judgebench_v2_null_control.json"
OUT = _REPO / "results" / "judgebench_v2_null_control_ties.json"
TOL = 1e-9


def vagt_mean_eps2(X, tau, n_r):
    """vagt_core.vagt with the σ²_N estimator it used when judgebench_v2_null_control.json was
    generated (σ²_N = mean ε²); every other line is the same as vagt_core.vagt."""
    R = X.shape[1]
    c = X.mean(axis=1)
    b = c - tau
    sigma_B_naive = float(np.mean(b ** 2))
    grand = X.mean()
    alpha = X.mean(axis=0) - grand
    sigma_R = float(np.mean(alpha ** 2))
    eps = X - (c[:, None] + alpha[None, :])
    sigma_N = float(np.mean(eps ** 2))
    sigma_B = max(0.0, sigma_B_naive - sigma_N / R)
    p = float(tau.mean())
    sigma_tau = p * (1 - p)
    denom = sigma_tau + sigma_B + (sigma_R + sigma_N) / n_r
    phi_v = sigma_tau / denom if denom > 0 else float("nan")
    return dict(sigma_tau=sigma_tau, sigma_B=sigma_B, sigma_R=sigma_R, sigma_N=sigma_N, phi_v=phi_v)


def s_stat(x, llama, qwen, tau):
    return int(np.dot(x.astype(int), (llama + qwen - 3 * tau).astype(int)))


def delta(fn, llama, qwen, x, tau):
    X2, X3 = np.column_stack([llama, qwen]), np.column_stack([llama, qwen, x])
    v3 = fn(X3, tau, 3)
    return v3["phi_v"] - fn(X2, tau, 2)["phi_v"], v3["sigma_B"]


def p_of(k):
    return round((k + 1) / (NC.N_PERM + 1), 4)


def main():
    committed = json.load(io.open(COMMITTED, encoding="utf-8"))
    assert committed["seed"] == V.SEED and committed["n_perm"] == NC.N_PERM
    base = NC.load_base()
    rng = np.random.default_rng(V.SEED)          # same generator, drawn in the same order as run_null_control_v2
    out = {"purpose": ("Ties between each candidate's real ΔΦ_V and its τ-blind permutation null "
                       "(results/judgebench_v2_null_control.json), counted exactly"),
           "source": "results/judgebench_v2_null_control.json (regenerated in memory, not rewritten)",
           "seed": V.SEED, "n_perm": NC.N_PERM,
           "tie_statistic": "S = sum_i x_i (llama_i + qwen_i - 3 tau_i); with the flag count fixed and "
                            "sigma_B unclamped, Delta Phi_V falls as S rises, so equal S = equal Delta Phi_V",
           "p_conventions": {
               "p_ties_counted": "(#{null > real} + #{null = real} + 1) / (N_PERM + 1) — the >= rule of "
                                 "run_null_control_v2.py, with ties decided on S",
               "p_ties_excluded": "(#{null > real} + 1) / (N_PERM + 1)",
               "p_float_ge_current_estimator": "run_null_control_v2.py's float comparison nulls >= real, "
                                               "with vagt_core's current sigma_N = sum eps^2 / ((N-1)(R-1)): "
                                               "what re-running it at this commit writes",
               "p_float_ge_mean_eps2_estimator": "the same comparison with the earlier sigma_N = mean eps^2, "
                                                 "which judgebench_v2_null_control.json was generated with"},
           "candidates": {}}
    for slug, model, source in NC.CANDIDATES:
        cand = NC.cand_lookup(slug, source, base)
        llama, qwen, c, tau = NC.complete_case(base, cand)
        real, sb = delta(V.vagt, llama, qwen, c, tau)
        real_old, _ = delta(vagt_mean_eps2, llama, qwen, c, tau)
        assert sb > 0
        assert real == NC.phi([llama, qwen, c], tau) - NC.phi([llama, qwen], tau)   # same float as the committed script
        s_real = s_stat(c, llama, qwen, tau)
        nulls, nulls_old = np.empty(NC.N_PERM), np.empty(NC.N_PERM)
        s_null = np.empty(NC.N_PERM, dtype=int)
        for i in range(NC.N_PERM):
            x = rng.permutation(c)
            nulls[i], sb = delta(V.vagt, llama, qwen, x, tau)
            nulls_old[i], _ = delta(vagt_mean_eps2, llama, qwen, x, tau)
            assert sb > 0                                         # unclamped: the S argument holds
            s_null[i] = s_stat(x, llama, qwen, tau)
        # S orders ΔΦ_V (larger S, smaller ΔΦ_V) on every shuffle; the two estimators agree to 1e-12
        order = np.argsort(s_null, kind="stable")
        assert np.all(np.diff(nulls[order]) <= TOL)
        assert np.max(np.abs(nulls - nulls_old)) < 1e-12 and abs(real - real_old) < 1e-12
        above, tied = int(np.sum(s_null < s_real)), int(np.sum(s_null == s_real))
        assert above == int(np.sum(nulls > real + TOL)) and tied == int(np.sum(np.abs(nulls - real) <= TOL))
        ge_cur, ge_old = int(np.sum(nulls >= real)), int(np.sum(nulls_old >= real_old))
        # reproduce the committed record
        rec = committed["candidates"][slug]
        lo, hi = np.percentile(nulls, [2.5, 97.5])
        assert rec["model"] == model and rec["n"] == len(tau)
        assert rec["real_delta_phi_v"] == round(float(real), 4)
        assert rec["null_mean"] == round(float(nulls.mean()), 4)
        assert rec["null_95_range"] == [round(float(lo), 4), round(float(hi), 4)]
        assert rec["null_min"] == round(float(nulls.min()), 4) and rec["null_max"] == round(float(nulls.max()), 4)
        p_cnt, p_exc = p_of(above + tied), p_of(above)
        # the committed file (earlier estimator, 0.001 for Super) or a re-run of run_null_control_v2.py (current one)
        assert rec["perm_p_value"] in (p_of(ge_old), p_of(ge_cur))
        matched = [name for name, p in (("mean_eps2_estimator", p_of(ge_old)), ("current_estimator", p_of(ge_cur)))
                   if p == rec["perm_p_value"]]
        assert p_of(ge_cur) == p_cnt                               # the current one counts every tie
        tied_idx = np.flatnonzero(s_null == s_real)
        out["candidates"][slug] = {
            "model": model, "n": int(len(tau)),
            "real_delta_phi_v": rec["real_delta_phi_v"], "null_max": rec["null_max"],
            "real_minus_null_max": round(float(real - nulls.max()), 4) + 0.0,   # + 0.0: no "-0.0" on a tie
            "n_null_above_real": above, "n_null_tied_with_real": tied,
            "real_above_every_null": above + tied == 0,
            "p_ties_counted": p_cnt, "p_ties_excluded": p_exc,
            "committed_perm_p_value": rec["perm_p_value"],
            "committed_perm_p_value_reproduced_by": matched,
            "committed_matches": ("both" if p_cnt == p_exc else
                                  "p_ties_counted" if rec["perm_p_value"] == p_cnt else "p_ties_excluded"),
            "p_float_ge_current_estimator": p_of(ge_cur),
            "p_float_ge_mean_eps2_estimator": p_of(ge_old),
        }
        if 0 < tied <= 3:          # the float gap of each tied shuffle under both estimators
            out["candidates"][slug]["tied_shuffles_float_minus_real"] = {
                "current_estimator": [float(nulls[i] - real) for i in tied_idx],
                "mean_eps2_estimator": [float(nulls_old[i] - real_old) for i in tied_idx]}
    out["checks"] = {"asserted": [
        "the regenerated nulls reproduce real_delta_phi_v, null_mean, null_95_range, null_min, null_max "
        "and n of every committed candidate",
        "sigma_B > 0 for the real column and every shuffle, and S orders Delta Phi_V on every shuffle",
        f"tie and above counts on S equal the counts with a {TOL:g} tolerance on Delta Phi_V",
        "the two sigma_N estimators give Delta Phi_V within 1e-12 of each other on every shuffle",
        "the float comparison nulls >= real reproduces every committed perm_p_value with sigma_N = mean eps^2, "
        "and equals p_ties_counted for every candidate with the current sigma_N"]}
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"τ-blind permutation null — ties (SEED={V.SEED}, N_PERM={NC.N_PERM})\n")
    hdr = (f"{'candidate':32} {'real':>7} {'null max':>8} {'above':>5} {'tied':>4} {'p ties counted':>14} "
           f"{'p excl':>7} {'committed':>9} {'float now':>9}")
    print(hdr); print("-" * len(hdr))
    for slug, r in out["candidates"].items():
        print(f"{slug:32} {r['real_delta_phi_v']:+7.4f} {r['null_max']:+8.4f} {r['n_null_above_real']:5d} "
              f"{r['n_null_tied_with_real']:4d} {r['p_ties_counted']:14.4f} {r['p_ties_excluded']:7.4f} "
              f"{r['committed_perm_p_value']:9.4f} {r['p_float_ge_current_estimator']:9.4f}")
        if "tied_shuffles_float_minus_real" in r:
            print(f"    tied shuffle float - real: {r['tied_shuffles_float_minus_real']}")
    print(f"\nSaved -> {OUT.relative_to(_REPO).as_posix()}")


if __name__ == "__main__":
    main()
