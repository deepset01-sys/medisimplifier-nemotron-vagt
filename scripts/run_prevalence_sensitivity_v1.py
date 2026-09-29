"""
run_prevalence_sensitivity_v1.py — how the automated-pass cross-stratum figures depend on each stratum's corrupted share.

The automated pass scored the 708-item MedSimp-JudgeBench (Project v1's benchmark, automated labels). Each stratum is its
corrupted items plus the same 200 clean controls (195 in the calibration file's Llama+Qwen+Nano complete case), so
each sits at its own corrupted share (calibration file: dose 0.30, negation 0.34, lateral 0.43, diagnosis 0.41;
vagt_nemotron_results.txt). Phi_V depends on that share (README A8 threats 11-12), so a mean over strata, a ranking
of strata, or a sign near zero mixes shares. This reweights the SAME verdicts (no new judge calls, no new labels):
  1. calibration file (nemotron_calibration_full.json -> vagt_bootstrap_cis.json, README A6 rows, FINDINGS.md §2):
     Delta Phi_V and Delta sigma^2_B of adding Nano to Llama+Qwen, per stratum.
  2. deployed-gate file (results/gate_calibration_full.json -> results/consensus_accuracy.json): the same, and the
     number of strata on which Phi_V and majority-vote balanced accuracy move in opposite directions.
  3. null-rater control (audit_pool/ + the two synthetic raters of scripts/compute_null_baseline.py ->
     results/null_baseline_cis.json): per-stratum Delta Phi_V and the four-stratum mean for constant-UNSAFE,
     random-47% and Nano.
  4. selector.py's ranking of the v1 pool with the two nulls added, with and without its collateral key, under
     BOTH tie rules: "rounding" (blind-spot Delta rounded to 0.01 bins; selector.py at 400ef54) and "within_top"
     (tied when within TIE_BAND of the top candidate's blind-spot Delta). selector.audit_panel itself, with its
     Delta computation swapped for the reweighted one, is asserted to equal one of the two mirrors at every share.
  5. the automated diagnosis Delta Phi_V next to the v2 figures at a common share.
  6. the README A5 recall-by-type table (counts behind each percentage, both prompts).

Reweighting is that of scripts/run_prevalence_sensitivity_v2.py (vagt_w and weights are imported from it): each
corrupted row weighted p/n1, each clean row (1-p)/n0; every mean over rows is weighted, means over raters are not.
"Common share p" puts every stratum at the same p. CIs are paired item bootstraps on vagt_core's index stream
(SEED=42, n_boot=1000), each resampled row keeping its weight, with the stream conventions of the committed files:
one rng shared across strata in canonical order for the calibration file (vagt_nemotron_analysis.py) and, with no
committed CI to match, for the gate file; a fresh rng per stratum for the null control (compute_null_baseline.py).
Equal weights reproduce vagt_bootstrap_cis.json, consensus_accuracy.json, null_baseline_cis.json, the
prevalences printed in vagt_nemotron_results.txt, and the ranking in results/audit_panel_live_receipt.json (asserted).
When sigma_B is clamped at 0 (vagt_core does the same), Phi_V depends on the sigma_N estimator; the clamp counts
(point estimates and bootstrap replicates, own share vs common shares, and the 0.01 grids) are reported as
sigma_B_clamps; the grid point estimates are asserted clamp-free.

Post hoc; not part of any pre-registration. The automated diagnosis labels are ~85% wrong (README A8 threat 1):
the diagnosis figures here are disclosed history, and reweighting does not correct the labels. Dose, negation and
lateral keep their automated labels (README A8). Assumes corrupted and clean items behave at other shares as they
do here. Grid orderings are of point estimates; the CIs at 0.50 and 0.30 are in common_share.

Deterministic, no API calls.
"""
import io
import json
import re
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "src" / "audit_panel"))
sys.path.insert(0, str(_REPO / "scripts"))
from audit_panel import vagt_core as V  # noqa: E402
from pool_loader import Pool  # noqa: E402
import selector  # noqa: E402
import compute_null_baseline as NB  # noqa: E402  (inject_nulls, INCUMBENT, NANO)
import compute_consensus_accuracy as CA  # noqa: E402  (consensus_bal_acc)
import run_prevalence_sensitivity_v2 as PS2  # noqa: E402  (vagt_w, weights, runs, GRID, load_rows)

RES = _REPO / "results"
CALIB = _REPO / "nemotron_calibration_full.json"
CALIB_TXT = _REPO / "vagt_nemotron_results.txt"
CALIB_CIS = _REPO / "vagt_bootstrap_cis.json"
GATE708 = RES / "gate_calibration_full.json"
CONSENSUS = RES / "consensus_accuracy.json"
NULLS = RES / "null_baseline_cis.json"
RECEIPT = RES / "audit_panel_live_receipt.json"
V2_SENS = RES / "judgebench_v2_prevalence_sensitivity.json"
V2_GATE = RES / "judgebench_v2_panel_gate.json"
V2_CALIB = RES / "judgebench_v2_panel_calib.json"
OUT = RES / "judgebench_v1_prevalence_sensitivity.json"

SEED = V.SEED
assert SEED == 42
KEYS = ["llama_verdict", "qwen_verdict", "nemotron_verdict"]   # incumbent first, candidate last
STRATA = V.STRATA
SOUND = ["dose", "negation", "lateral"]                        # strata whose automated labels were not found wrong
COMMON = [0.50, 0.30]
GRID = PS2.GRID
NANO_SLUG = "NVIDIA-Nemotron-3-Nano-30B-A3B"
TB = selector.TIE_BAND
RULES = ("rounding", "within_top")
EDGE_TOL = 1e-9
r4 = PS2.r4
runs = PS2.runs

# README A5 "Recall by injected error type" table, percentages as printed (Nemotron, Llama, Qwen)
A5_TABLE = {"diagnosis": (92, 47, 47), "dose": (92, 44, 86), "lateral": (97, 43, 85), "negation": (82, 30, 55)}


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def dstats(X, tau, w, n_inc=2):
    """Weighted Phi_V of the incumbent columns (first n_inc) and of the full panel, and the paired changes."""
    inc, full = PS2.vagt_w(X[:, :n_inc], tau, w), PS2.vagt_w(X, tau, w)
    return {"phi2": inc["phi_v"], "phi3": full["phi_v"], "d": full["phi_v"] - inc["phi_v"],
            "dsB": full["sigma_B"] - inc["sigma_B"]}


def wts(tau, p):
    """Row weights: equal (each stratum at its own share) when p is None, else every stratum at share p."""
    return np.ones(len(tau)) if p is None else PS2.weights(tau, p)


def boot(X, tau, w, rng):
    """Paired item bootstrap on vagt_core.paired_delta_cis's index stream (the caller owns rng);
    each resampled row keeps its weight. Returns 95% percentile CIs for Delta Phi_V and Delta sigma^2_B."""
    n = len(tau)
    d, s = np.empty(V.N_BOOT), np.empty(V.N_BOOT)
    for i in range(V.N_BOOT):
        ii = rng.integers(0, n, n)
        r = dstats(X[ii], tau[ii], w[ii])
        d[i], s[i] = r["d"], r["dsB"]
    d, s = d[np.isfinite(d)], s[np.isfinite(s)]
    return ([float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            [float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))])


def cell(X, tau, w, rng):
    pt = dstats(X, tau, w)
    ci_d, ci_s = boot(X, tau, w, rng)
    return {"phi_incumbent": r4(pt["phi2"]), "phi_with_nano": r4(pt["phi3"]),
            "delta_phi_v": r4(pt["d"]), "ci95": [r4(v) for v in ci_d],
            "ci95_6dp": [round(v, 6) for v in ci_d],
            "ci_excludes_0": bool(ci_d[0] > 0 or ci_d[1] < 0),
            "delta_sigma_B": r4(pt["dsB"]), "delta_sigma_B_ci95": [r4(v) for v in ci_s],
            "delta_sigma_B_ci_excludes_0": bool(ci_s[0] > 0 or ci_s[1] < 0)}


def sign(x):
    return "positive" if x > 0 else ("negative" if x < 0 else "zero")


def strata_matrices(records, keys):
    out = {}
    for f in STRATA:
        X, tau, dropped = V.stratum(records, f, keys)
        out[f] = {"X": X, "tau": tau, "dropped": dropped}
    return out


def by_share_block(mats, shared_stream):
    """Delta at each stratum's own share and at each common share. shared_stream: one rng across strata in
    canonical order per share (vagt_nemotron_analysis.py); otherwise a fresh rng per stratum (compute_null_baseline.py)."""
    own, common = {}, {f"{p:.2f}": {} for p in COMMON}
    PS2.CLAMP[0] = 0
    rng = np.random.default_rng(SEED)
    for f in STRATA:
        X, tau = mats[f]["X"], mats[f]["tau"]
        if not shared_stream:
            rng = np.random.default_rng(SEED)
        own[f] = {"n": int(len(tau)), "corrupted": int(tau.sum()), "clean": int(len(tau) - tau.sum()),
                  "share": r4(tau.mean()), **cell(X, tau, wts(tau, None), rng)}
    clamps = {"own_share": PS2.CLAMP[0]}
    PS2.CLAMP[0] = 0
    for p in COMMON:
        rng = np.random.default_rng(SEED)
        for f in STRATA:
            X, tau = mats[f]["X"], mats[f]["tau"]
            if not shared_stream:
                rng = np.random.default_rng(SEED)
            common[f"{p:.2f}"][f] = cell(X, tau, wts(tau, p), rng)
    clamps["common_shares"] = PS2.CLAMP[0]
    return own, common, clamps


def grid_points(mats):
    """Point estimates on the 0.01 grid, every stratum at the same share p. Returns (grid, sigma_B clamp count)."""
    PS2.CLAMP[0] = 0
    g = {p: {f: dstats(mats[f]["X"], mats[f]["tau"], wts(mats[f]["tau"], p)) for f in STRATA} for p in GRID}
    return g, PS2.CLAMP[0]


def grid_runs(g):
    def argext(fn, strata, key):
        return runs([(p, fn(strata, key=lambda f: g[p][f][key])) for p in GRID])
    return {
        "delta_sign_runs": {f: runs([(p, sign(g[p][f]["d"])) for p in GRID]) for f in STRATA},
        "largest_delta_runs": argext(max, STRATA, "d"),
        "smallest_delta_runs": argext(min, STRATA, "d"),
        "largest_delta_runs_dose_negation_lateral": argext(max, SOUND, "d"),
        "smallest_delta_runs_dose_negation_lateral": argext(min, SOUND, "d"),
        "delta_sigma_B_sign_runs": {f: runs([(p, sign(g[p][f]["dsB"])) for p in GRID]) for f in STRATA},
        "smallest_delta_sigma_B_runs": argext(min, STRATA, "dsB"),
        "strata_with_sigma_B_cut_runs": runs([(p, ", ".join(f for f in STRATA if g[p][f]["dsB"] < 0) or "none")
                                              for p in GRID]),
        "blindest_runs": argext(min, STRATA, "phi2"),
    }


def ci_overlaps(own, common):
    """Whether two strata's Delta Phi_V CIs overlap, per pair, at the own shares and each common share."""
    def ov(block):
        return {f"{a}|{b}": bool(block[a]["ci95_6dp"][0] <= block[b]["ci95_6dp"][1] and
                                  block[b]["ci95_6dp"][0] <= block[a]["ci95_6dp"][1])
                for i, a in enumerate(STRATA) for b in STRATA[i + 1:]}
    return {"own_share": ov(own), **{f"common_{k}": ov(v) for k, v in common.items()}}


def txt_prevalences():
    """(n, prevalence) per feature as printed in vagt_nemotron_results.txt (3-rater complete case)."""
    pat = re.compile(r"FEATURE:\s+(\w+)\s+\(3-rater n=(\d+), corrupted prevalence=([\d.]+)")
    return {m.group(1): (int(m.group(2)), float(m.group(3)))
            for m in pat.finditer(CALIB_TXT.read_text(encoding="utf-8"))}


# ── selector: both tie rules ──────────────────────────────────────────────────
def selector_rank(per_phi, inc_phi, rel, rule, collateral=True):
    """selector.audit_panel's sort key over precomputed per-stratum Delta under one tie rule.
    rounding:   primary key = round(Delta_blind / TIE_BAND) * TIE_BAND; tied = same bin as the top.
    within_top: primary key = the top's Delta for every candidate with top - Delta <= TIE_BAND, else its own Delta;
                tied = those candidates.
    Then collateral floor (min Delta over the other strata), fewest ERROR rows, specificity, mean Delta, model id.
    collateral=False drops the collateral key only. Returns blind, order, tied, edge (closest distance to a tie edge)."""
    blind = min(inc_phi, key=inc_phi.get)
    bd = {c: per_phi[c][blind] for c in per_phi}
    top = max(bd.values())
    if rule == "rounding":
        prim = {c: round(bd[c] / TB) * TB for c in bd}
        tied_set = {c for c in bd if prim[c] == round(top / TB) * TB}
        edge = min(abs(abs(bd[c] / TB - np.floor(bd[c] / TB)) - 0.5) * TB for c in bd)
    else:
        tied_set = {c for c in bd if top - bd[c] <= TB}
        prim = {c: (top if c in tied_set else bd[c]) for c in bd}
        edge = min(abs(top - bd[c] - TB) for c in bd)

    def key(c):
        coll = min(per_phi[c][f] for f in per_phi[c] if f != blind)
        tail = (-rel[c][0], rel[c][1], float(np.mean(list(per_phi[c].values()))), c)
        return (prim[c], coll) + tail if collateral else (prim[c],) + tail

    order = sorted(per_phi, key=key, reverse=True)
    return blind, order, [c for c in order if c in tied_set], edge


class WeightedSelector:
    """Swap selector.py's Delta computation for the reweighted one (share p; None = equal weights) so that
    selector.audit_panel ranks with its OWN sort key and tie rule on reweighted Delta. Restored on exit."""

    def __init__(self, p, cache):
        self.p, self.cache = p, cache

    def _mat(self, records, f, keys):
        k = (f, tuple(keys))
        if k not in self.cache:
            X, tau, _ = V.stratum(records, f, list(keys))
            self.cache[k] = (X, tau)
        return self.cache[k]

    def __enter__(self):
        self._orig = (selector._incumbent_summary, selector._candidate_deltas)
        p = self.p

        def inc_summary(records, incumbent_ids, strata):
            phi, sB = {}, {}
            for f in strata:
                X, tau = self._mat(records, f, incumbent_ids)
                v = PS2.vagt_w(X, tau, wts(tau, p))
                phi[f], sB[f] = v["phi_v"], v["sigma_B"]
            return phi, sB, {m: 0.0 for m in incumbent_ids}, min(phi, key=phi.get)

        def cand_deltas(records, incumbent_ids, candidate_id, strata):
            per_phi, per_sB = {}, {}
            for f in strata:
                X, tau = self._mat(records, f, list(incumbent_ids) + [candidate_id])
                r = dstats(X, tau, wts(tau, p), n_inc=len(incumbent_ids))
                per_phi[f], per_sB[f] = r["d"], r["dsB"]
            return per_phi, per_sB

        selector._incumbent_summary, selector._candidate_deltas = inc_summary, cand_deltas
        return self

    def __exit__(self, *exc):
        selector._incumbent_summary, selector._candidate_deltas = self._orig
        return False


def a5_recall():
    """Counts behind README A5's recall-by-type table: diagnosis row from the v2 hand-verified stratum (120 tau=1;
    deployed gate prompt, and the calibration prompt for comparison); dose/lateral/negation rows from the calibration
    file (each judge's ERROR verdicts left out) and, for comparison, the deployed-gate file."""
    judges = (("nemotron", "nemotron_verdict"), ("llama", "llama_verdict"), ("qwen", "qwen_verdict"))

    def rec(rows, key):
        unsafe = sum(r[key] == "UNSAFE" for r in rows)
        valid = sum(r[key] in V.VALID for r in rows)
        return {"unsafe": unsafe, "valid": valid, "n": len(rows), "recall": r4(unsafe / valid)}

    out = {"diagnosis_v2": {}, "automated": {}}
    for name, path in (("deployed_prompt", V2_GATE), ("calibration_prompt", V2_CALIB)):
        rows = [r for r in _load(path)["per_sample"] if int(r["tau"]) == 1]
        out["diagnosis_v2"][name] = {j: rec(rows, k) for j, k in judges}
    for name, path in (("calibration_file", CALIB), ("gate_file", GATE708)):
        ps = _load(path)["per_sample"]
        out["automated"][name] = {f: {j: rec([r for r in ps if r["condition"] == "corrupted" and r["error_type"] == f], k)
                                      for j, k in judges} for f in ("dose", "lateral", "negation")}
    got = {"diagnosis": tuple(round(100 * out["diagnosis_v2"]["deployed_prompt"][j]["recall"]) for j, _ in judges)}
    for f in ("dose", "lateral", "negation"):
        got[f] = tuple(round(100 * out["automated"]["calibration_file"][f][j]["recall"]) for j, _ in judges)
    assert got == A5_TABLE, got
    return out


def main():
    out = {
        "purpose": ("How the automated-pass (Project v1's benchmark, automated labels) cross-stratum figures depend on each "
                    "stratum's corrupted share. Each stratum is its corrupted items plus the same 200 clean controls "
                    "(195 in the calibration file's complete case), so the strata sit at different shares; the same "
                    "verdicts are reweighted to common shares."),
        "status": "post hoc sensitivity analysis; not part of any pre-registration",
        "method": {
            "reweighting": ("scripts/run_prevalence_sensitivity_v2.py vagt_w / weights (imported): each corrupted row "
                            "weighted p/n1, each clean row (1-p)/n0; every mean over rows weighted, means over raters not. "
                            "'common share p' puts every stratum at the same p"),
            "ci": ("paired item bootstrap, vagt_core index stream, SEED=42, n_boot=1000, each resampled row keeping its "
                   "weight. Calibration and gate files: one rng shared across strata in canonical order per share "
                   "(vagt_nemotron_analysis.py convention); null control: a fresh rng per stratum "
                   "(compute_null_baseline.py convention). ci95 is rounded to 4 dp, ci95_6dp to 6 dp; ci_excludes_0 "
                   "uses the unrounded bounds"),
            "labels": ("the automated diagnosis labels are ~85% wrong (README A8 threat 1): diagnosis figures here are "
                       "disclosed history and reweighting does not correct them; dose/negation/lateral keep automated labels"),
            "assumption": "corrupted and clean items behave at other shares as they do here",
            "grid": ("0.01 to 0.99 in steps of 0.01, every stratum at the same share; point estimates only (no CIs), "
                     "so a grid ordering is an ordering of point estimates"),
            "sigma_B_sign": ("delta_sigma_B < 0 is a cut in shared bias, > 0 a rise; smallest_delta_sigma_B_runs is the "
                             "argmin whatever its sign, strata_with_sigma_B_cut_runs lists the strata with a cut"),
        },
        "common_shares": COMMON,
    }
    checks = []

    # ── 1. calibration file ──
    cal = _load(CALIB)["per_sample"]
    mats = strata_matrices(cal, KEYS)
    own, common, clamp_cal = by_share_block(mats, shared_stream=True)
    pub = _load(CALIB_CIS)["features"]
    txt = txt_prevalences()
    for f in STRATA:
        c, q = own[f], pub[f]
        assert (c["n"], c["delta_phi_v"], c["ci95"]) == (q["n"], q["delta_phi_v"]["point"], q["delta_phi_v"]["ci95"]), f
        assert (c["delta_sigma_B"], c["delta_sigma_B_ci95"]) == (q["delta_sigma_B"]["point"], q["delta_sigma_B"]["ci95"]), f
        assert (c["n"], round(c["share"], 2)) == txt[f], (f, c["n"], c["share"], txt[f])
    checks += ["calibration file: equal weights reproduce vagt_bootstrap_cis.json (n, Delta Phi_V, Delta sigma_B, CIs)",
               "calibration file: n and corrupted share match vagt_nemotron_results.txt"]
    g_cal, clamp_cal["grid"] = grid_points(mats)
    out["calibration_file"] = {
        "source": ("nemotron_calibration_full.json (the file behind vagt_bootstrap_cis.json, vagt_nemotron_results.txt, "
                   "README A6 dose/negation/lateral rows and FINDINGS.md §2); Llama+Qwen -> +Nano, complete case. "
                   "Llama and Qwen verdicts are stored from Project v1; Nano's were run with "
                   "nemotron_judge_test.py's calibration prompt"),
        "own_share": own, "common_share": common, "ci_overlap": ci_overlaps(own, common), "grid": grid_runs(g_cal),
        "sigma_B_clamps": clamp_cal,
    }

    # ── 2. deployed-gate file ──
    gate = _load(GATE708)["per_sample"]
    gmats = strata_matrices(gate, KEYS)
    gown, gcommon, clamp_gate = by_share_block(gmats, shared_stream=True)
    ca = _load(CONSENSUS)["per_stratum"]
    for f in STRATA:
        X, tau = gmats[f]["X"], gmats[f]["tau"]
        pt = dstats(X, tau, wts(tau, None))
        dg = ca[f]["decomposition_gate_prompt"]
        assert (gown[f]["n"], gown[f]["corrupted"]) == (ca[f]["n"], ca[f]["n_corrupted"]), f
        assert (r4(pt["phi2"]), r4(pt["phi3"]), r4(pt["d"]), r4(pt["dsB"])) == \
               (dg["phi_v_2"], dg["phi_v_3"], dg["delta_phi_v"], dg["delta_sigma_B"]), f
        _, _, ba2 = CA.consensus_bal_acc(X[:, :2], tau)
        _, _, ba3 = CA.consensus_bal_acc(X, tau)
        assert r4(ba3 - ba2) == ca[f]["consensus"]["delta_bal_acc"], f
        gown[f]["delta_bal_acc"] = ca[f]["consensus"]["delta_bal_acc"]
    checks.append("gate file: equal weights reproduce consensus_accuracy.json (n, Phi_V, Delta Phi_V, Delta sigma_B, "
                  "Delta balanced accuracy)")
    dba = {f: gown[f]["delta_bal_acc"] for f in STRATA}

    def opposite(deltas):
        return sorted(f for f in STRATA if dba[f] * deltas[f] < 0)

    g_gate, clamp_gate["grid"] = grid_points(gmats)
    out["gate_file"] = {
        "source": ("results/gate_calibration_full.json (all three judges under the deployed gate prompt; the file behind "
                   "results/consensus_accuracy.json), Llama+Qwen -> +Nano, complete case"),
        "ci_note": "consensus_accuracy.json reports no CIs; these use the calibration file's stream convention",
        "own_share": gown, "common_share": gcommon, "ci_overlap": ci_overlaps(gown, gcommon), "grid": grid_runs(g_gate),
        "balanced_accuracy_note": ("majority-vote balanced accuracy averages recall and specificity, so it does not "
                                   "depend on the share; Delta balanced accuracy is copied from consensus_accuracy.json"),
        "phi_v_and_bal_acc_opposite": {
            "own_share": opposite({f: gown[f]["delta_phi_v"] for f in STRATA}),
            **{f"common_{p:.2f}": opposite({f: gcommon[f"{p:.2f}"][f]["delta_phi_v"] for f in STRATA})
               for p in COMMON},
            "count_runs": runs([(p, len(opposite({f: g_gate[p][f]["d"] for f in STRATA}))) for p in GRID]),
        },
        "sigma_B_clamps": clamp_gate,
    }

    # ── 3. null-rater control ──
    pool = Pool.load(_REPO / "audit_pool")
    NB.inject_nulls(pool.records)
    raters = [("null_unsafe (constant UNSAFE)", "null_unsafe"), ("null_random (p=0.47)", "null_random"),
              ("Nemotron Nano (real)", NB.NANO)]
    pub_nulls = _load(NULLS)["raters"]
    nulls_out, nmeans_grid, clamp_null = {}, {}, {}
    for label, cand in raters:
        nm = strata_matrices(pool.records, NB.INCUMBENT + [cand])
        rown, rcommon, clamp_null[label] = by_share_block(nm, shared_stream=False)
        for f in STRATA:
            q = pub_nulls[label]["per_stratum"][f]
            assert (rown[f]["n"], rown[f]["delta_phi_v"], rown[f]["ci95"]) == (q["n"], q["delta_phi_v"], q["ci_95"]), (label, f)
        pub_mean = float(np.mean([pub_nulls[label]["per_stratum"][f]["delta_phi_v"] for f in STRATA]))
        gp, clamp_null[label]["grid"] = grid_points(nm)
        nmeans_grid[label] = {p: float(np.mean([gp[p][f]["d"] for f in STRATA])) for p in GRID}

        def mean_at(p):   # unrounded per-stratum Delta; p None = each stratum's own share
            return float(np.mean([dstats(nm[f]["X"], nm[f]["tau"], wts(nm[f]["tau"], p))["d"] for f in STRATA]))
        own_mean = mean_at(None)
        nulls_out[label] = {
            "model": cand,
            "own_share": rown,
            "mean_over_strata": {"own_share": r4(own_mean), **{f"common_{p:.2f}": r4(mean_at(p)) for p in COMMON}},
            "common_share": rcommon,
            "mean_sign_runs": runs([(p, sign(nmeans_grid[label][p])) for p in GRID]),
            "delta_sign_runs": {f: runs([(p, sign(gp[p][f]["d"])) for p in GRID]) for f in STRATA},
        }
        assert abs(own_mean - pub_mean) < 1e-4, (label, own_mean, pub_mean)   # committed per-stratum values are rounded
    checks.append("null control: equal weights reproduce null_baseline_cis.json (n, Delta Phi_V, CI) for all three raters")
    out["null_control"] = {
        "source": ("audit_pool/ with the two synthetic raters of scripts/compute_null_baseline.py (inject_nulls, seed 42); "
                   "Llama+Qwen -> +rater, complete case (results/null_baseline_cis.json)"),
        "mean_note": ("unweighted mean of the four per-stratum Delta Phi_V, as in the committed 'net-negative / "
                      "net-positive' text; no CI is computed for the mean"),
        "raters": nulls_out,
        "positive_mean_raters_runs": runs([(p, ", ".join(sorted(lb for lb in nmeans_grid if nmeans_grid[lb][p] > 0)) or "none")
                                           for p in GRID]),
        "sigma_B_clamps": clamp_null,
    }

    # ── 4. selector.py ordering of the v1 pool with the two nulls added, both tie rules ──
    INC = NB.INCUMBENT
    real = sorted(m for m in pool.models if m not in INC)
    nulls = ["null_unsafe", "null_random"]
    pool.models |= set(nulls)
    assert selector.pool_strata(pool.records) == STRATA
    cands = real + nulls
    receipt = _load(RECEIPT)["response"]
    res_real = selector.audit_panel(pool, INC, real, bootstrap_iters=V.N_BOOT, seed=SEED)
    assert [r["model"] for r in res_real["candidates_ranked"]] == [r["model"] for r in receipt["candidates_ranked"]]
    for a, b in zip(res_real["candidates_ranked"], receipt["candidates_ranked"]):
        assert a["per_stratum_delta_Phi_V"] == b["per_stratum_delta_Phi_V"], a["model"]
    assert res_real["recommendation"]["model"] == receipt["recommendation"]["model"]
    assert res_real["recommendation"]["ci_95"] == receipt["recommendation"]["ci_95"]
    nano_rc = next(r for r in receipt["candidates_ranked"] if r["model"] == NB.NANO)
    assert nulls_out["Nemotron Nano (real)"]["mean_over_strata"]["own_share"] == nano_rc["mean_delta_Phi_V"]
    checks.append("selector.audit_panel on the v1 pool reproduces results/audit_panel_live_receipt.json's order, "
                  "per-stratum Delta Phi_V, recommended model and CI; the Nano four-stratum mean reproduces its "
                  "mean_delta_Phi_V")
    res_unpatched = selector.audit_panel(pool, INC, cands, bootstrap_iters=2, seed=SEED)
    smats = {c: strata_matrices(pool.records, INC + [c]) for c in cands}
    imats = strata_matrices(pool.records, INC)
    rel_cache = {}

    def at(p):
        PS2.CLAMP[0] = 0
        per_phi = {c: {f: dstats(smats[c][f]["X"], smats[c][f]["tau"], wts(smats[c][f]["tau"], p))["d"]
                       for f in STRATA} for c in cands}
        inc_phi = {f: PS2.vagt_w(imats[f]["X"], imats[f]["tau"], wts(imats[f]["tau"], p))["phi_v"] for f in STRATA}
        clamps = PS2.CLAMP[0]
        blind = min(inc_phi, key=inc_phi.get)
        if blind not in rel_cache:
            rel_cache[blind] = {c: selector._reliability(pool.records, c, blind) for c in cands}
        return per_phi, inc_phi, rel_cache[blind], clamps

    shares = [("own_share", None)] + [(f"common_{q:.2f}", q) for q in COMMON] + [(f"{p:.2f}", p) for p in GRID]
    ranked, sel_clamps, min_edge, mat_cache, matched = {}, 0, {r: 1.0 for r in RULES}, {}, set(RULES)
    for name, p in shares:
        per_phi, inc_phi, rel, cl = at(p)
        sel_clamps += cl
        ranked[name] = {"per_phi": per_phi, "inc_phi": inc_phi, "rel": rel}
        for rule in RULES:
            for coll in (True, False):
                blind, order, tied, edge = selector_rank(per_phi, inc_phi, rel, rule, coll)
                ranked[name][(rule, coll)] = (blind, order, tied)
            min_edge[rule] = min(min_edge[rule], edge)
        with WeightedSelector(p, mat_cache):
            res = selector.audit_panel(pool, INC, cands, bootstrap_iters=2, seed=SEED)
        got = ([r["model"] for r in res["candidates_ranked"]], res["recommendation"]["tied_top_candidates"])
        matched &= {rule for rule in RULES if got == tuple(ranked[name][(rule, True)][1:])}
        if p is None:
            assert got == ([r["model"] for r in res_unpatched["candidates_ranked"]],
                           res_unpatched["recommendation"]["tied_top_candidates"])
    assert matched, "selector.audit_panel matches neither tie-rule mirror at every share"
    assert all(e > EDGE_TOL for e in min_edge.values()), min_edge
    assert sel_clamps == 0, sel_clamps
    checks.append("selector.audit_panel, with its Delta swapped for the reweighted one, returns the same order and "
                  "tied set as one of the two tie-rule mirrors (the one selector.py implements) at the strata's own "
                  "shares, at 0.50, 0.30 and every grid share; unswapped at own shares it gives the same answer")
    print(f"selector.py tie rule (matched at every share): {sorted(matched)}")

    def by_share_entry(name):
        rk = ranked[name]
        blind = rk[("rounding", True)][0]
        e = {"blindest": blind,
             "blind_delta": {c: r4(rk["per_phi"][c][blind]) for c in sorted(cands, key=lambda c: -rk["per_phi"][c][blind])},
             "collateral_floor": {c: r4(min(rk["per_phi"][c][f] for f in STRATA if f != blind)) for c in cands}}
        for rule in RULES:
            _, order, tied = rk[(rule, True)]
            _, order_nc, _ = rk[(rule, False)]
            e[rule] = {"tied_top": tied, "order": order, "order_without_collateral_key": order_nc,
                       "recommendation": order[0], "recommendation_without_collateral_key": order_nc[0],
                       "rank_of_null_unsafe": {"with_collateral": order.index("null_unsafe") + 1,
                                               "without_collateral": order_nc.index("null_unsafe") + 1},
                       "rank_of_null_random": {"with_collateral": order.index("null_random") + 1,
                                               "without_collateral": order_nc.index("null_random") + 1}}
        return e

    def grid_rule_runs(rule):
        g = {}
        for coll, suffix in ((True, ""), (False, "_without_collateral_key")):
            g["recommendation_runs" + suffix] = runs([(p, ranked[f"{p:.2f}"][(rule, coll)][1][0]) for p in GRID])
            for nl in nulls:
                g[f"rank_of_{nl}_runs" + suffix] = runs(
                    [(p, ranked[f"{p:.2f}"][(rule, coll)][1].index(nl) + 1) for p in GRID])
        for nl in nulls:
            g[f"{nl}_in_top_tie_runs"] = runs([(p, nl in ranked[f"{p:.2f}"][(rule, True)][2]) for p in GRID])
        g["tied_top_runs"] = runs([(p, ", ".join(ranked[f"{p:.2f}"][(rule, True)][2])) for p in GRID])
        return g

    out["selector_with_nulls"] = {
        "pool": "audit_pool/ (automated pool): six real candidates + the two synthetic nulls, incumbent Llama+Qwen",
        "key": ("selector.py: blind-spot Delta (tie rule below), then collateral floor (min Delta over the other strata), "
                "then fewest ERROR rows, specificity, mean Delta, model id. 'without_collateral_key' drops the collateral "
                "key only; membership of the top tie does not depend on it"),
        "tie_rules": {"rounding": ("blind-spot Delta rounded to 0.01 bins, round(Delta/0.01)*0.01; tied = the top "
                                   "candidate's bin (selector.py at 400ef54)"),
                      "within_top": ("tied = blind-spot Delta within TIE_BAND (0.01) of the top candidate's; the tied "
                                     "candidates share the top's primary key, the rest keep their own Delta")},
        "closest_distance_to_a_tie_edge": {r: float(f"{min_edge[r]:.3g}") for r in RULES},
        "n_candidates": len(cands),
        "by_share": {name: by_share_entry(name) for name, _ in shares[:1 + len(COMMON)]},
        "grid": {"blindest_runs": runs([(p, ranked[f"{p:.2f}"][("rounding", True)][0]) for p in GRID]),
                 "largest_blind_delta_runs": runs([(p, max(cands, key=lambda c: ranked[f"{p:.2f}"]["per_phi"][c]["diagnosis"]))
                                                   for p in GRID]),
                 **{rule: grid_rule_runs(rule) for rule in RULES}},
        "sigma_B_clamps": {"point_estimates_all_shares": sel_clamps},
    }
    assert all(v["value"] == "diagnosis" for v in out["selector_with_nulls"]["grid"]["blindest_runs"])

    # ── 5. automated diagnosis figure vs v2 at a common share ──
    v2s = _load(V2_SENS)
    v2_dep = v2s["candidates"][NANO_SLUG]["by_prevalence"]["0.50"]
    v2_cal = v2s["panel_calibration_prompt"]["by_prevalence"]["0.50"]
    assert (v2_dep["delta_phi_v"], v2_cal["delta_phi_v"]) == (0.0765, 0.0591)
    p_v1 = float(mats["diagnosis"]["tau"].mean())
    v2g = _load(V2_GATE)["per_sample"]
    v2c = _load(V2_CALIB)["per_sample"]
    Xd, td, _, _, _ = PS2.load_rows(v2g, {(str(r["idx"]), int(r["tau"])): r["nemotron_verdict"] for r in v2g})
    Xc, tc, _, _, _ = PS2.load_rows(v2c, {(str(r["idx"]), int(r["tau"])): r["nemotron_verdict"] for r in v2c})
    out["diagnosis_automated_vs_v2"] = {
        "note": ("different labels (automated vs hand-verified), different items and different prompt pairings (the "
                 "automated file pairs Llama and Qwen verdicts stored from Project v1 with Nano under the calibration prompt; "
                 "v2 has all three judges under the calibration prompt in one column and under the deployed gate "
                 "prompt in the other); only the share is equalised here"),
        "automated_calibration_file": {"own_share": {"share": r4(p_v1), **{k: own["diagnosis"][k] for k in
                                                                         ("delta_phi_v", "ci95")}},
                                       "at_0.50": {k: common["0.50"]["diagnosis"][k] for k in ("delta_phi_v", "ci95")}},
        "v2_at_0.50": {"deployed_prompt": {k: v2_dep[k] for k in ("delta_phi_v", "ci95")},
                       "calibration_prompt": {k: v2_cal[k] for k in ("delta_phi_v", "ci95")},
                       "source": "results/judgebench_v2_prevalence_sensitivity.json by_prevalence 0.50"},
        "v2_at_automated_share": {
            "share": r4(p_v1),
            "deployed_prompt": PS2.fmt(PS2.at_p_raw(Xd, td, p_v1)),
            "calibration_prompt": PS2.fmt(PS2.at_p_raw(Xc, tc, p_v1)),
            "method": "run_prevalence_sensitivity_v2.at_p_raw (its bootstrap convention and bands)",
        },
    }

    # ── 6. README A5 recall-by-type table ──
    out["a5_recall_by_type"] = a5_recall()
    checks.append("README A5 recall-by-type table: every percentage reproduced (diagnosis row from "
                  "results/judgebench_v2_panel_gate.json, the others from nemotron_calibration_full.json)")

    for blk in (clamp_cal, clamp_gate, *clamp_null.values()):
        assert blk["grid"] == 0, blk
    checks.append("no sigma_B clamp in any grid point estimate or own-share cell")
    for blk in (clamp_cal, clamp_gate, *clamp_null.values()):
        assert blk["own_share"] == 0, blk
    out["checks"] = {"asserted": checks,
                     "v2_reference_asserted": "v2 figures at 0.50 read from judgebench_v2_prevalence_sensitivity.json (+0.0765, +0.0591)"}
    with io.open(OUT, "w", encoding="utf-8") as fh:   # as run_prevalence_sensitivity_v2.py writes its file
        json.dump(out, fh, ensure_ascii=False, indent=2)

    # ── print ──
    for blk, title in (("calibration_file", "calibration file"), ("gate_file", "deployed-gate file")):
        b = out[blk]
        print(f"\n{title}: Delta Phi_V (Llama+Qwen -> +Nano)")
        for f in STRATA:
            o = b["own_share"][f]
            s = f"  {f:<10} own {o['share']:.3f}: {o['delta_phi_v']:+.4f} [{o['ci95'][0]:+.4f},{o['ci95'][1]:+.4f}]"
            for p in COMMON:
                c = b["common_share"][f"{p:.2f}"][f]
                s += f" | {p:.2f}: {c['delta_phi_v']:+.4f} [{c['ci95'][0]:+.4f},{c['ci95'][1]:+.4f}]"
            print(s)
        for k, v in b["grid"].items():
            if isinstance(v, list):
                print(f"  {k}:", ", ".join(f"{r['from']:.2f}-{r['to']:.2f} {r['value']}" for r in v))
    print("\nopposite-direction strata (gate):", out["gate_file"]["phi_v_and_bal_acc_opposite"])
    print("\nnull control, mean over strata:")
    for lb, r in out["null_control"]["raters"].items():
        print(f"  {lb:<32} {r['mean_over_strata']}  sign runs:",
              ", ".join(f"{x['from']:.2f}-{x['to']:.2f} {x['value']}" for x in r["mean_sign_runs"]))
    sw = out["selector_with_nulls"]
    for name, s in sw["by_share"].items():
        print(f"\nselector {name}: blind={s['blindest']}")
        for rule in RULES:
            print(f"   {rule:<10} tied={s[rule]['tied_top']} rec={s[rule]['recommendation']} "
                  f"null_unsafe rank {s[rule]['rank_of_null_unsafe']} null_random rank {s[rule]['rank_of_null_random']}")
    for rule in RULES:
        print(f"\nselector grid, {rule}:")
        for k, v in sw["grid"][rule].items():
            print(f"  {k}:", ", ".join(f"{r['from']:.2f}-{r['to']:.2f} {r['value']}" for r in v))
    print("\nlargest blind delta:", ", ".join(f"{r['from']:.2f}-{r['to']:.2f} {r['value']}"
                                             for r in sw["grid"]["largest_blind_delta_runs"]))
    print("closest distance to a tie edge:", sw["closest_distance_to_a_tie_edge"])
    print("\ndiagnosis automated vs v2:", json.dumps(out["diagnosis_automated_vs_v2"], ensure_ascii=False))
    print(f"\nclamps: calibration {clamp_cal}, gate {clamp_gate}, nulls {clamp_null}, selector {sel_clamps}")
    print(f"\nSaved -> {OUT}")


if __name__ == "__main__":
    main()
