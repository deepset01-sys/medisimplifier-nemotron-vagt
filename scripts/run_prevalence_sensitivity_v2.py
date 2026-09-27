"""
run_prevalence_sensitivity_v2.py — how the v2 diagnosis-stratum figures depend on the drop share.

The v2 stratum is balanced by design (120 drops + their 120 paired controls, prevalence 0.50),
and Phi_V depends on prevalence: sigma^2_tau = p(1-p), and mean b^2 averages the drop side
(weight p) with the control side (weight 1-p). This reweights the SAME verdicts to other
prevalences (no new judge calls, no new labels) and reports:
  1. Delta Phi_V (candidate appended to Llama+Qwen) at each p in PREVALENCES, with a paired CI and
     band, for the six pool candidates (deployed gate prompt), and for the Llama+Qwen+Nano panel with
     all three judges under the calibration prompt.
  2. On a 0.01 grid: sign, CI and band runs, the ranking, the selector's pick, and the terms behind
     the gpt-oss-120b / DeepSeek-V4-Flash order.
  3. The deployed gate's operating characteristics: recall and false-positive rate (independent of
     p) and the share of flags that are real (depends on p).
  4. Controls flagged per judge under both prompts, the full stratum reweighted to the shares of the
     all-120-control subset cells, and the 708-set DISAGREE reference (72% corrupted by automated
     label, all four error types).

Reweighting: each drop gets weight p/n1, each control (1-p)/n0; every mean over rows in
vagt_core.vagt becomes a weighted mean (means over raters stay unweighted). Rows and pairs are all
kept. Equal weights reproduce vagt_core.vagt, and at p = 0.50 the weights are equal for the five
240-row candidates, so their Delta and CI reproduce results/judgebench_v2_pool_table.json (asserted).
CI: paired item bootstrap on the index stream of vagt_core.paired_delta_cis (SEED=42, n_boot=1000),
each resampled row keeping its weight, so a replicate's prevalence varies around p as it does around
0.50 in the published CIs. The grid CI runs are also given with the weights recomputed inside each
replicate (prevalence fixed at p); the two conventions can move a threshold by one or two grid points.
This script reports no permutation null. The published one (results/judgebench_v2_null_control.json)
is for the benchmark's own composition and is not reweighted: permuting a verdict column within the
benchmark sample keeps its flag rate there, not the candidate's flag rate at p (flag_rate_by_prevalence),
so real minus null would mix detection with a flag-rate mismatch.
As a cross-check, drops are also subsampled against all controls (a range over draws, not a CI).
Assumes drops and controls behave at other prevalences as they do here; it does not address harder
real-world drops (README A8 threat 4). Post hoc: not part of the pre-registered protocol.

Deterministic, no API calls.
"""
import io
import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "src" / "audit_panel"))
from audit_panel import vagt_core as V  # noqa: E402
import selector  # noqa: E402  (TIE_BAND and the ranking key are mirrored from it)

RES = _REPO / "results"
GATE = RES / "judgebench_v2_panel_gate.json"
CALIB = RES / "judgebench_v2_panel_calib.json"
POOL_TABLE = RES / "judgebench_v2_pool_table.json"
GATE708 = RES / "gate_calibration_full.json"
PHIR = RES / "judgebench_v2_phi_v_recompute.json"
OUT = RES / "judgebench_v2_prevalence_sensitivity.json"

PREVALENCES = [0.50, 0.33, 0.20, 0.10, 0.05]
GRID = [round(0.01 * i, 2) for i in range(1, 100)]
N_DRAW = 1000   # subsample cross-check
N_INCUMBENT = 2
OSS, DS = "gpt-oss-120b", "DeepSeek-V4-Flash-0731"

CANDIDATES = [
    ("NVIDIA-Nemotron-3-Nano-30B-A3B", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "panel"),
    ("Nemotron-3-Ultra-550b-a55b",     "nvidia/Nemotron-3-Ultra-550b-a55b",     "pool"),
    ("nemotron-3-super-120b-a12b",     "nvidia/nemotron-3-super-120b-a12b",     "pool"),
    ("gpt-oss-120b",                   "openai/gpt-oss-120b",                   "pool"),
    ("DeepSeek-V4-Flash-0731",         "deepseek-ai/DeepSeek-V4-Flash-0731",    "pool"),
    ("gemma-3-27b-it",                 "google/gemma-3-27b-it",                 "pool"),
]
CLAMP = [0]     # times sigma_B would go negative (then sigma_N would matter); asserted 0


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


# ── weighted VAGT ─────────────────────────────────────────────────────────────
def vagt_w(X, tau, w):
    """vagt_core.vagt (n_r = R = X.shape[1]) with every mean over rows replaced by a w-weighted
    mean; means over raters stay unweighted. sigma_N keeps vagt_core's (N-1)(R-1) degrees of
    freedom, so equal weights reproduce it exactly; with sigma_B unclamped (asserted) Phi_V does
    not depend on sigma_N."""
    w = np.asarray(w, dtype=float)
    w = w / w.sum()
    N, R = X.shape
    c = X.mean(axis=1)
    b = c - tau
    mean_b2 = float(np.sum(w * b ** 2))
    colmean = w @ X
    alpha = colmean - colmean.mean()
    sigma_R = float(np.mean(alpha ** 2))
    eps = X - (c[:, None] + alpha[None, :])
    dof = (N - 1) * (R - 1)
    sigma_N = float(N * np.sum(w * np.sum(eps ** 2, axis=1))) / dof if dof > 0 else 0.0
    sigma_B = mean_b2 - sigma_N / R
    if sigma_B < 0:
        CLAMP[0] += 1
        sigma_B = 0.0
    p = float(np.sum(w * tau))
    sigma_tau = p * (1 - p)
    denom = sigma_tau + sigma_B + (sigma_R + sigma_N) / R
    return dict(sigma_tau=sigma_tau, sigma_B=sigma_B, sigma_R=sigma_R, sigma_N=sigma_N,
                mean_b2=mean_b2, phi_v=sigma_tau / denom if denom > 0 else float("nan"))


def weights(tau, p):
    n1 = tau.sum()
    n0 = len(tau) - n1
    return np.where(tau == 1, p / n1, (1 - p) / n0)


def dphi(X, tau, w):
    return vagt_w(X, tau, w)["phi_v"] - vagt_w(X[:, :N_INCUMBENT], tau, w)["phi_v"]


def delta_ci(X, tau, w, p_fixed=None):
    """Point Delta Phi_V and its paired item-bootstrap 95% CI: the index stream of
    vagt_core.paired_delta_cis (SEED, N_BOOT). Each resampled row keeps its weight w; with
    p_fixed, the weights are instead recomputed inside each replicate (prevalence exactly p_fixed)."""
    rng = np.random.default_rng(V.SEED)
    n = len(tau)
    acc = np.empty(V.N_BOOT)
    for i in range(V.N_BOOT):
        ii = rng.integers(0, n, n)
        t = tau[ii]
        if p_fixed is None:
            acc[i] = dphi(X[ii], t, w[ii])
        else:
            acc[i] = dphi(X[ii], t, weights(t, p_fixed)) if 0 < t.sum() < len(t) else np.nan
    acc = acc[np.isfinite(acc)]
    return dphi(X, tau, w), float(np.percentile(acc, 2.5)), float(np.percentile(acc, 97.5))


def at_p_raw(X, tau, p, alt=False):
    w = weights(tau, p)
    d, lo, hi = delta_ci(X, tau, w)
    r = dict(phi2=vagt_w(X[:, :N_INCUMBENT], tau, w)["phi_v"], phi3=vagt_w(X, tau, w)["phi_v"], d=d, lo=lo, hi=hi)
    if alt:
        _, r["lo_fixed_p"], r["hi_fixed_p"] = delta_ci(X, tau, w, p_fixed=p)
    return r


def fmt(r):
    return {"phi_incumbent": r4(r["phi2"]), "phi_with_candidate": r4(r["phi3"]),
            "delta_phi_v": r4(r["d"]), "ci95": [r4(r["lo"]), r4(r["hi"])], "band": band(r["d"], r["lo"], r["hi"])}


def at_p(X, tau, p):
    return fmt(at_p_raw(X, tau, p))


def r4(x):
    return round(float(x), 4)


def runs(pairs):
    """[(p, label), ...] on the grid -> [{'from', 'to', 'value'}] for consecutive equal labels."""
    out = []
    for p, v in pairs:
        if out and out[-1]["value"] == v:
            out[-1]["to"] = p
        else:
            out.append({"from": p, "to": p, "value": v})
    return out


def wilson(k, n, z=1.96):
    ph = k / n
    den = 1 + z * z / n
    mid = (ph + z * z / (2 * n)) / den
    half = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return [round(100 * (mid - half), 1), round(100 * (mid + half), 1)]


# ── data ──────────────────────────────────────────────────────────────────────
def load_rows(per_sample, cand):
    """Complete-case (idx, tau, [llama, qwen, candidate]) in per_sample order; also the
    candidate's ERROR count and SAFE / valid-clean specificity, as selector._reliability counts them."""
    X, tau, keys, errors, safe, valid_clean = [], [], [], 0, 0, 0
    for r in per_sample:
        k = (str(r["idx"]), int(r["tau"]))
        cv = cand.get(k, "ERROR")
        if cv not in V.VALID:
            errors += 1
        elif k[1] == 0:
            valid_clean += 1
            safe += cv == "SAFE"
        vals = [r["llama_verdict"], r["qwen_verdict"], cv]
        if all(v in V.VALID for v in vals):
            X.append([V.LABEL_TO_INT[v] for v in vals])
            tau.append(k[1])
            keys.append(k)
    return (np.array(X, dtype=float), np.array(tau, dtype=float), keys, errors,
            safe / valid_clean if valid_clean else 0.0)


def candidate_verdicts(slug, source, gate):
    if source == "panel":
        return {(str(r["idx"]), int(r["tau"])): r["nemotron_verdict"] for r in gate}
    return {(str(r["idx"]), int(r["tau"])): r["verdict"]
            for r in _load(RES / f"judgebench_v2_pool_{slug}.json")["verdicts"]}


def side_means(X, tau):
    """Within-side mean b^2 (independent of p) for [Llama+Qwen, with candidate], and the p below which
    the candidate's control-side change outweighs its drop-side change in the weighted mean b^2."""
    c1, c2 = X[:, :N_INCUMBENT].mean(axis=1), X.mean(axis=1)
    drop = [float(np.mean((c1[tau == 1] - 1) ** 2)), float(np.mean((c2[tau == 1] - 1) ** 2))]
    ctrl = [float(np.mean(c1[tau == 0] ** 2)), float(np.mean(c2[tau == 0] ** 2))]
    dd1, dd0 = drop[1] - drop[0], ctrl[1] - ctrl[0]
    if dd1 < 0 < dd0:
        be = {"p": round(dd0 / (dd0 - dd1), 3),
              "reason": "adding the candidate lowers drop-side and raises control-side mean b^2; below p it raises the weighted total"}
    elif dd0 < 0 < dd1:
        be = {"p": round(dd0 / (dd0 - dd1), 3),
              "reason": "adding the candidate raises drop-side and lowers control-side mean b^2; above p it raises the weighted total"}
    elif dd1 <= 0 and dd0 <= 0:
        be = {"p": None, "reason": "adding the candidate does not raise mean b^2 on either side, so at no p"}
    else:
        be = {"p": None, "reason": "adding the candidate does not lower mean b^2 on either side, so at every p it raises it"}
    return {"drop_side_mean_b2": [r4(v) for v in drop], "control_side_mean_b2": [r4(v) for v in ctrl],
            "pairs_are": "[Llama+Qwen, with candidate]; within-side means, independent of p",
            "mean_b2_breakeven": be,
            "note": "sigma_R/R also enters Phi_V, so the Delta Phi_V zero crossing differs from this break-even"}


def gate_rule(r):
    """src/safety_gate.py consensus rule (Nemotron + Qwen; Llama advisory)."""
    n, q = r["nemotron_verdict"], r["qwen_verdict"]
    if n == "SAFE" and q == "SAFE":
        return "SAFE"
    if q == "UNSAFE":
        return "UNSAFE"
    if n == "UNSAFE" and q == "SAFE":
        return "DISAGREE"
    return "ERROR" if "ERROR" in (n, q) else "DISAGREE"


def operating(tp, n1, fp, n0, component=False):
    """component=True (the DISAGREE branch): drops it does not flag may still be flagged UNSAFE,
    so no missed-drop count is given."""
    rec, fpr = tp / n1, fp / n0
    by_p = {}
    for p in PREVALENCES:
        flag = rec * p + fpr * (1 - p)
        by_p[f"{p:.2f}"] = {"share_of_flags_real_pct": round(100 * rec * p / flag, 1),
                            "share_of_flags_false_alarm_pct": round(100 * fpr * (1 - p) / flag, 1),
                            "per_1000_false_alarms": round(1000 * fpr * (1 - p))}
        if not component:
            by_p[f"{p:.2f}"]["per_1000_missed_drops"] = round(1000 * (1 - rec) * p)
    return {"drops_flagged": f"{tp}/{n1}", "recall_pct": round(100 * rec, 1), "recall_wilson95": wilson(tp, n1),
            "controls_flagged": f"{fp}/{n0}", "false_positive_rate_pct": round(100 * fpr, 1),
            "fpr_wilson95": wilson(fp, n0), "by_prevalence": by_p}


def main():
    gate = _load(GATE)["per_sample"]
    calib = _load(CALIB)["per_sample"]
    table = {r["slug"]: r for r in _load(POOL_TABLE)["candidates_ranked"]}

    data = {}
    for slug, model, source in CANDIDATES:
        X, tau, keys, errors, spec = load_rows(gate, candidate_verdicts(slug, source, gate))
        data[slug] = dict(model=model, X=X, tau=tau, keys=keys, errors=errors, spec=spec)

    # ── checks: equal weights reproduce vagt_core and every published pool-table row ──
    for slug, d in data.items():
        X, tau = d["X"], d["tau"]
        eq = np.ones(len(tau))
        for Xk in (X, X[:, :N_INCUMBENT]):
            ref, got = V.vagt(Xk, tau, Xk.shape[1]), vagt_w(Xk, tau, eq)
            assert all(abs(ref[m] - got[m]) < 1e-12 for m in V.VAGT_METRICS), slug
        pt, lo, hi = delta_ci(X, tau, eq)
        row = table[slug]
        assert (r4(pt), [r4(lo), r4(hi)], len(tau)) == (row["delta_phi_v"], row["ci95"], row["n"]), slug
        if len(tau) == 240:  # balanced: p = 0.50 weights are equal weights
            assert at_p(X, tau, 0.50)["ci95"] == row["ci95"], slug

    out = {
        "purpose": ("How the v2 diagnosis-stratum Phi_V figures depend on the drop share (prevalence). "
                    "The stratum is 50% drops by design; the same verdicts are reweighted to other shares."),
        "status": "post hoc sensitivity analysis; not part of the pre-registered protocol (docs/judgebench_v2_protocol.md)",
        "method": {
            "reweighting": ("each drop weighted p/n1, each control (1-p)/n0; every mean over rows in "
                            "vagt_core.vagt is weighted (means over raters are not); all rows and pairs kept"),
            "ci": ("paired item bootstrap, index stream of vagt_core.paired_delta_cis (SEED=42, n_boot=1000); "
                   "each resampled row keeps its weight, so a replicate's prevalence varies around p as it varies "
                   "around 0.50 in the published CIs. The *_fixed_p_runs repeat the grid CI runs with the weights "
                   "recomputed inside each replicate (prevalence exactly p); the conventions can move a threshold by "
                   "one or two grid points"),
            "no_reweighted_null": ("no permutation null is reported: permuting a verdict column within the benchmark "
                                   "sample keeps the benchmark's flag rate, not the candidate's flag "
                                   "rate at p (flag_rate_by_prevalence), so real minus null would mix detection with a "
                                   "flag-rate mismatch. The published null (results/judgebench_v2_null_control.json) "
                                   "is for the benchmark's own composition"),
            "reproduces_published": ("equal weights reproduce vagt_core.vagt and all six rows of "
                                     "results/judgebench_v2_pool_table.json; at p=0.50 the five 240-row "
                                     "candidates reproduce it exactly (asserted)"),
            "deepseek_rows": ("DeepSeek-V4-Flash-0731 is on its 233 complete-case rows (119 drops, 114 controls), "
                              "as in the pool table, so its published +0.1238 is at p = 0.511, not 0.50"),
            "assumption": ("drops and controls behave at other prevalences as they do here; this does not "
                           "address harder real-world drops (README A8 threat 4)"),
        },
        "bands": {"POSITIVE": "delta >= +0.05 AND ci_lower > 0",
                  "WEAK-POS": "+0.02 <= delta < +0.05 AND ci_lower > 0",
                  "NULL": "CI includes 0 AND |delta| < 0.05",
                  "NEGATIVE": "delta <= -0.02 AND ci_upper < 0",
                  "OUTSIDE BANDS": "none of the above (not defined by the protocol)"},
        "bands_scope": ("protocol §8 pre-registers these bands for the primary metric at the benchmark's own "
                        "composition (p = 0.50); here they are applied descriptively"),
        "prevalences": PREVALENCES,
        "grid": "0.01 to 0.99 in steps of 0.01",
        "candidates": {},
    }

    # ── 1-2: Delta Phi_V by prevalence, grid runs ──
    grid_delta = {}
    for slug, d in data.items():
        X, tau = d["X"], d["tau"]
        n1, n0 = int(tau.sum()), int(len(tau) - tau.sum())
        rec = int(X[tau == 1, 2].sum())
        spec_n = int((X[tau == 0, 2] == 0).sum())
        raw = {p: at_p_raw(X, tau, p, alt=True) for p in GRID}   # runs use unrounded values
        grid = {p: fmt(raw[p]) for p in GRID}
        grid_delta[slug] = {p: raw[p]["d"] for p in GRID}
        sign = [(p, "positive" if raw[p]["d"] > 0 else ("negative" if raw[p]["d"] < 0 else "zero")) for p in GRID]
        w5 = weights(tau, 0.5)
        phi2_max = max(GRID, key=lambda p: raw[p]["phi2"])
        out["candidates"][slug] = {
            "model": d["model"], "n": int(len(tau)), "drops": n1, "controls": n0,
            "benchmark_prevalence": round(n1 / len(tau), 3),
            "recall": f"{rec}/{n1}", "specificity": f"{spec_n}/{n0}",
            "flag_rate_by_prevalence": {f"{p:.2f}": round(float(np.sum(weights(tau, p) * X[:, 2])), 3)
                                        for p in PREVALENCES},
            "by_prevalence": {f"{p:.2f}": grid[p] for p in PREVALENCES},
            "band_runs": runs([(p, grid[p]["band"]) for p in GRID]),
            "delta_sign_runs": runs(sign),
            "ci_lower_above_0_runs": runs([(p, raw[p]["lo"] > 0) for p in GRID]),
            "ci_upper_below_0_runs": runs([(p, raw[p]["hi"] < 0) for p in GRID]),
            "ci_lower_above_0_fixed_p_runs": runs([(p, raw[p]["lo_fixed_p"] > 0) for p in GRID]),
            "ci_upper_below_0_fixed_p_runs": runs([(p, raw[p]["hi_fixed_p"] < 0) for p in GRID]),
            "delta_ge_0_05_runs": runs([(p, raw[p]["d"] >= 0.05) for p in GRID]),
            "phi_incumbent_ge_0_5_runs": runs([(p, raw[p]["phi2"] >= 0.5) for p in GRID]),
            "phi_with_candidate_ge_0_5_runs": runs([(p, raw[p]["phi3"] >= 0.5) for p in GRID]),
            "phi_incumbent_max_on_grid": {"p": phi2_max, "phi_v": r4(raw[phi2_max]["phi2"])},
            "phi_runs_note": "the Phi_V >= 0.5 runs and the maximum are point estimates",
            "mechanism": {**side_means(X, tau),
                          "sigma_R_at_0_50": [r4(vagt_w(X[:, :N_INCUMBENT], tau, w5)["sigma_R"]),
                                              r4(vagt_w(X, tau, w5)["sigma_R"])]},
        }

    # Llama + Qwen + Nano with all three judges under the calibration prompt (same 240 items)
    Xc, tc, _, _, _ = load_rows(calib, {(str(r["idx"]), int(r["tau"])): r["nemotron_verdict"] for r in calib})
    out["panel_calibration_prompt"] = {
        "panel": ("Llama + Qwen + Nano, all three under the calibration prompt "
                  "(results/judgebench_v2_panel_calib.json); incumbent and candidate both differ from the deployed panel"),
        "n": int(len(tc)), "recall": f"{int(Xc[tc == 1, 2].sum())}/{int(tc.sum())}",
        "specificity": f"{int((Xc[tc == 0, 2] == 0).sum())}/{int((tc == 0).sum())}",
        "by_prevalence": {f"{p:.2f}": at_p(Xc, tc, p) for p in PREVALENCES},
        "mechanism": side_means(Xc, tc)}
    # The full deployed-prompt stratum (Llama+Qwen+Nano) reweighted to each all-120-control subset cell's share,
    # so a subset's lower Delta can be split into prevalence and subset.
    cells = _load(PHIR)["cells"]
    Xn, tn = data["NVIDIA-Nemotron-3-Nano-30B-A3B"]["X"], data["NVIDIA-Nemotron-3-Nano-30B-A3B"]["tau"]
    at_share = {}
    for name in ("deployed_cat0_all120", "deployed_er0_all120"):
        c = cells[name]
        p = c["pos_tau1"] / (c["pos_tau1"] + c["neg_tau0"])
        rw = at_p_raw(Xn, tn, p, alt=True)
        at_share[name] = {"share": round(p, 4), "subset_cell": {"delta_phi_v": c["delta_phi_v"], "ci95": c["ci95"],
                                                                "band": c["band"]},
                          "full_stratum": {**fmt(rw), "ci95_fixed_p": [r4(rw["lo_fixed_p"]), r4(rw["hi_fixed_p"])],
                                           "band_fixed_p": band(rw["d"], rw["lo_fixed_p"], rw["hi_fixed_p"])}}
    out["full_stratum_at_subset_shares"] = {
        "source": "subset cells from results/judgebench_v2_phi_v_recompute.json (deployed prompt, all 120 controls)",
        "cells": at_share}
    out["controls_flagged_by_judge"] = {
        name: {j.replace("_verdict", "").replace("nemotron", "nano"): f"{sum(r[j] == 'UNSAFE' for r in ps if r['tau'] == 0)}/"
                                                                     f"{sum(r['tau'] == 0 for r in ps)}"
               for j in ("llama_verdict", "qwen_verdict", "nemotron_verdict")}
        for name, ps in (("deployed_prompt", gate), ("calibration_prompt", calib))}

    # cross-check: subsample drops against all controls (unweighted vagt_core), N_DRAW draws
    for slug, d in data.items():
        X, tau = d["X"], d["tau"]
        pos, neg = np.where(tau == 1)[0], np.where(tau == 0)[0]
        chk = {}
        for p in PREVALENCES:
            k = min(len(pos), int(round(p * len(neg) / (1 - p))))
            rng = np.random.default_rng(V.SEED)
            vals = np.array([V.paired_delta(X[s], tau[s], N_INCUMBENT)["phi_v"] for s in
                             (np.concatenate([rng.choice(pos, k, replace=False), neg]) for _ in range(N_DRAW))])
            chk[f"{p:.2f}"] = {"drops_drawn": k, "controls": int(len(neg)), "actual_p": round(k / (k + len(neg)), 3),
                               "median": r4(np.median(vals)),
                               "draw_range_2_5_97_5": [r4(np.percentile(vals, 2.5)), r4(np.percentile(vals, 97.5))]}
        out["candidates"][slug]["subsample_check"] = chk
    out["subsample_check_note"] = ("k drops drawn without replacement against all controls, unweighted vagt_core; "
                                   "the range reflects which drops were drawn only (controls fixed), so it is not a CI")

    # ── ranking and selector pick by p (each candidate on its own complete-case rows, as the selector) ──
    def ranked(p):
        return sorted(data, key=lambda s: -grid_delta[s][p])

    def selector_pick(p):
        # selector.audit_panel's sort key for a one-stratum pool: banded Delta, collateral (0.0 here),
        # fewest ERROR rows, specificity, mean Delta (= Delta), model id; highest first
        return max(data, key=lambda s: (round(grid_delta[s][p] / selector.TIE_BAND) * selector.TIE_BAND, 0.0,
                                        -data[s]["errors"], data[s]["spec"], grid_delta[s][p], data[s]["model"]))

    eq_delta = {s: dphi(d["X"], d["tau"], np.ones(len(d["tau"]))) for s, d in data.items()}
    pub_pick = max(data, key=lambda s: (round(eq_delta[s] / selector.TIE_BAND) * selector.TIE_BAND, 0.0,
                                        -data[s]["errors"], data[s]["spec"], eq_delta[s], data[s]["model"]))
    assert pub_pick == "gpt-oss-120b", pub_pick  # the published recommendation

    common = set.intersection(*[set(d["keys"]) for d in data.values()])
    cm = {s: np.array([k in common for k in d["keys"]]) for s, d in data.items()}
    tcm = data[OSS]["tau"][cm[OSS]]

    def common_delta(s, p):
        Xs, ts = data[s]["X"][cm[s]], data[s]["tau"][cm[s]]
        return dphi(Xs, ts, weights(ts, p))

    def own_term(s, p, key):   # 3-rater panel term on the candidate's own rows at prevalence p
        return vagt_w(data[s]["X"], data[s]["tau"], weights(data[s]["tau"], p))[key]

    def lower(a, b):
        return OSS if a < b else (DS if b < a else "equal")

    h2h = {f"{p:.2f}": {OSS: r4(common_delta(OSS, p)), DS: r4(common_delta(DS, p))} for p in PREVALENCES}
    out["ranking"] = {
        "basis": "each candidate on its own complete-case rows (DeepSeek 233, others 240), as selector.py ranks",
        "by_prevalence": {f"{p:.2f}": {"order": ranked(p), "delta_phi_v": {s: r4(grid_delta[s][p]) for s in ranked(p)},
                                       "selector_pick": selector_pick(p)} for p in PREVALENCES},
        "top_by_delta_runs": runs([(p, ranked(p)[0]) for p in GRID]),
        "selector_pick_runs": runs([(p, selector_pick(p)) for p in GRID]),
        "selector_note": ("selector.py bands Delta by rounding to the nearest 0.01 (round(Delta/0.01)*0.01), then "
                          "breaks ties on fewest ERROR rows and specificity; the published pick (equal weights) is "
                          "gpt-oss-120b (asserted)"),
        "gpt_oss_vs_deepseek": {
            "higher_delta_own_rows_runs": runs([(p, OSS if grid_delta[OSS][p] > grid_delta[DS][p] else DS) for p in GRID]),
            "higher_delta_common_rows_runs": runs([(p, OSS if common_delta(OSS, p) > common_delta(DS, p) else DS)
                                                   for p in GRID]),
            "common_rows": {"n": int(len(tcm)), "drops": int(tcm.sum()), "by_prevalence": h2h},
            "lower_panel_mean_b2_runs": runs([(p, lower(own_term(OSS, p, "mean_b2"), own_term(DS, p, "mean_b2")))
                                              for p in GRID]),
            "lower_panel_sigma_R_runs": runs([(p, lower(own_term(OSS, p, "sigma_R"), own_term(DS, p, "sigma_R")))
                                              for p in GRID]),
            "terms_note": ("3-rater panel (Llama+Qwen+candidate) on each candidate's own rows; mean b^2 is the "
                           "weighted mean squared consensus bias, sigma_R the rater-bias spread (enters as sigma_R/3)"),
        },
    }

    # ── 4: deployed gate operating characteristics (deployed prompt, 120 + 120) ──
    assert all(gate_rule(r) == r["consensus"] for r in gate)
    n1 = sum(r["tau"] == 1 for r in gate)
    n0 = sum(r["tau"] == 0 for r in gate)
    oss = candidate_verdicts("gpt-oss-120b", "pool", gate)
    rules = {
        "strict_any_non_safe (Qwen UNSAFE or Nano UNSAFE)": lambda r: r["consensus"] != "SAFE",
        "block_consensus_unsafe (= Qwen UNSAFE)": lambda r: r["consensus"] == "UNSAFE",
        "disagree_branch (Nano UNSAFE, Qwen SAFE)": lambda r: r["consensus"] == "DISAGREE",
        "nano_alone": lambda r: r["nemotron_verdict"] == "UNSAFE",
        "llama_alone (advisory)": lambda r: r["llama_verdict"] == "UNSAFE",
        "reference: Qwen UNSAFE or gpt-oss UNSAFE": lambda r: (r["qwen_verdict"] == "UNSAFE"
                                                             or oss[(str(r["idx"]), int(r["tau"]))] == "UNSAFE"),
    }
    out["gate_operating_characteristics"] = {
        "source": "results/judgebench_v2_panel_gate.json (deployed prompt); consensus matches src/safety_gate.py (asserted)",
        "independent_of_prevalence": "recall and false-positive rate",
        "depends_on_prevalence": "share of flags that are real / false alarms, and per-1,000 counts",
        "reference_note": "gpt-oss-120b was selected on this same data, so the reference row is optimistic",
        "rules": {name: operating(sum(f(r) for r in gate if r["tau"] == 1), n1,
                                  sum(f(r) for r in gate if r["tau"] == 0), n0,
                                  component=name.startswith("disagree")) for name, f in rules.items()},
    }
    g7 = _load(GATE708)["per_sample"]
    d1 = sum(r["condition"] == "corrupted" and r["consensus"] == "DISAGREE" for r in g7)
    d0 = sum(r["condition"] == "clean" and r["consensus"] == "DISAGREE" for r in g7)
    c1 = sum(r["condition"] == "corrupted" for r in g7)
    c0 = sum(r["condition"] == "clean" for r in g7)
    assert (d1, c1, d0, c0) == (96, 508, 51, 200), (d1, c1, d0, c0)
    by_type = {}
    for r in g7:
        if r["condition"] == "corrupted":
            t = by_type.setdefault(r["error_type"], {"items": 0, "disagree": 0})
            t["items"] += 1
            t["disagree"] += r["consensus"] == "DISAGREE"
    out["gate_708_disagree_reference"] = {
        "source": "results/gate_calibration_full.json (deployed prompt, automated labels)",
        "disagree_on_corrupted": f"{d1}/{c1}", "disagree_on_clean": f"{d0}/{c0}",
        "corrupted_by_error_type": by_type,
        "prevalence": round(c1 / (c1 + c0), 3),
        "prevalence_note": "share of items corrupted by automated label, all four error types (not diagnosis drops alone)",
        "false_alarm_share_pct_at_own_prevalence": round(100 * d0 / (d0 + d1), 1),
        "false_alarm_share_pct_by_prevalence": {
            f"{p:.2f}": round(100 * (d0 / c0) * (1 - p) / ((d0 / c0) * (1 - p) + (d1 / c1) * p), 1)
            for p in PREVALENCES},
    }

    assert CLAMP[0] == 0, CLAMP[0]
    out["checks"] = {"sigma_B_clamp_bound": CLAMP[0],
                     "asserted": ["equal weights reproduce vagt_core.vagt (all metrics, < 1e-12)",
                                  "equal weights reproduce every pool-table delta, CI and n",
                                  "p = 0.50 reproduces the pool-table CI for the five 240-row candidates",
                                  "the mirrored selector key picks gpt-oss-120b at equal weights",
                                  "recorded consensus matches the safety_gate.py rule on all 240 rows",
                                  "708-set DISAGREE counts 96/508 corrupted, 51/200 clean",
                                  "sigma_B never clamped (so Phi_V does not depend on the sigma_N estimator)"]}
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ── print ──
    print(f"Delta Phi_V by prevalence (candidate added to Llama+Qwen; SEED={V.SEED}, n_boot={V.N_BOOT})\n")
    for slug, c in out["candidates"].items():
        print(f"{slug}  (n={c['n']}, recall {c['recall']}, specificity {c['specificity']})")
        for p, v in c["by_prevalence"].items():
            print(f"   p={p}  Phi2={v['phi_incumbent']:.4f}  Phi3={v['phi_with_candidate']:.4f}  "
                  f"d={v['delta_phi_v']:+.4f} [{v['ci95'][0]:+.4f},{v['ci95'][1]:+.4f}]  {v['band']}")
        for key in ("delta_sign_runs", "ci_lower_above_0_runs", "ci_upper_below_0_runs", "ci_lower_above_0_fixed_p_runs",
                    "ci_upper_below_0_fixed_p_runs", "phi_with_candidate_ge_0_5_runs"):
            print(f"   {key}:", ", ".join(f"{r['from']:.2f}-{r['to']:.2f} {r['value']}" for r in c[key]))
    print("\nSelector pick:", ", ".join(f"{r['from']:.2f}-{r['to']:.2f} {r['value']}" for r in out["ranking"]["selector_pick_runs"]))
    print(f"\nSaved -> {OUT}")


if __name__ == "__main__":
    main()
