"""
run_tau_recompute_v1.py — the automated-pass diagnosis re-score, reproduced, prompt-matched, and put on a
common prevalence.

results/tau_recompute_summary.json re-scored the automated pass's diagnosis stratum with the 150-item hand
audit (results/tau_hand_labels_150.json: 128 PRESENT, 9 ABSENT, 13 BORDERLINE) and reported the +0.0706
"reversing" to -0.1438. The script that wrote it was not committed. This script:
  1. Reproduces every committed cell of results/tau_recompute_summary.json (asserted): the automated-label
     reference cell, the four hand-label cells (A/B x strict/generous) and split_f_diagnostic.
  2. Builds the same five cells from results/gate_calibration_full.json, where all three judges ran under one
     prompt (safety_gate.py JUDGE_PROMPT, the deployed gate prompt). In nemotron_calibration_full.json the
     Llama and Qwen columns are Project v1's stored verdicts (nemotron_judge_test.py:13) and only the
     Nemotron column was run there, under the calibration prompt (nemotron_judge_test.py:78-124).
  3. Gives each cell's prevalence (drop share) and reweights each cell to the published reference cell's share
     (138/333 = 0.414) and to 0.50, with the reweighting, bootstrap and bands of
     scripts/run_prevalence_sensitivity_v2.py (imported, not re-implemented); and, the other way round,
     reweights each pairing's automated-label cell to every hand-label cell's share.
  4. Runs a tau-blind permutation null at each cell's own composition: the Nemotron column is shuffled across the
     cell's rows (its flag rate kept, its link to tau removed), as scripts/run_null_control_v2.py does for v2.
     No reweighted null (see run_prevalence_sensitivity_v2.py: permuting within the sample keeps the sample's
     flag rate, not the flag rate at p).
  5. Checks how each file's judge columns treat rows that share an item index (idx; a clean control and its
     corrupted versions share one): how often a judge gives one verdict on every row of an idx, and how often its
     verdict on a corrupted row equals its verdict on that idx's clean control, in the stored file and in the
     re-run under the deployed prompt.

Designs (as in the summary): automated = every automated diagnosis item tau=1. A = hand-confirmed drops tau=1,
the rest of the 150 removed. B = hand-confirmed drops tau=1, the rest of the 150 kept as tau=0. strict counts
BORDERLINE as not a drop (removed in A, tau=0 in B); generous counts it as a drop. Every cell keeps all clean
controls as tau=0. Complete-case on the three judges.

Post hoc, not part of any pre-registered protocol. Deterministic (SEED=42, n_boot=1000, n_perm=1000), no API calls.
"""
import io
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "src" / "audit_panel"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_panel import vagt_core as V  # noqa: E402
import run_prevalence_sensitivity_v2 as PS  # noqa: E402  (at_p_raw, fmt, band, weights, dphi, side_means, runs, GRID, CLAMP)

RES = _REPO / "results"
PUBLISHED = _REPO / "nemotron_calibration_full.json"
GATE708 = RES / "gate_calibration_full.json"
LABELS = RES / "tau_hand_labels_150.json"
SUMMARY = RES / "tau_recompute_summary.json"
CONSENSUS = RES / "consensus_accuracy.json"
OUT = RES / "tau_recompute_v1_matched.json"

KEYS = ["llama_verdict", "qwen_verdict", "nemotron_verdict"]
ERROR_TYPES = ["dose", "lateral", "negation", "diagnosis"]
# README A5 recall (Nemotron, Llama, Qwen; %, ERROR verdicts left out) on the automated dose/lateral/negation rows
A5_RECALL = {"dose": (92, 44, 86), "lateral": (97, 43, 85), "negation": (82, 30, 55)}
N_INCUMBENT = 2
N_PERM = 1000
P_REF = 138 / 333          # share of the published reference cell (asserted below)
TARGETS = [("0.414", P_REF), ("0.50", 0.50)]
GRID = PS.GRID
CELLS = [("automated", None), ("A", "strict"), ("A", "generous"), ("B", "strict"), ("B", "generous")]
SUMMARY_NAME = {("A", "strict"): "Option A / strict", ("A", "generous"): "Option A / generous",
                ("B", "strict"): "Option B / strict", ("B", "generous"): "Option B / generous"}


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def r4(x):
    return round(float(x), 4)


def tau_band(d):
    """The bands recorded in results/tau_recompute_summary.json (preregistered_bands); point estimate only."""
    if d >= 0.05:
        return "HOLDS"
    if d > 0.02:
        return "ATTENUATED"
    return "REFUTED"


def cell_name(design, borderline):
    return "automated labels" if design == "automated" else f"{design}/{borderline}"


def build(per_sample, labels, design, borderline):
    """Complete-case X (Llama, Qwen, Nemotron), tau and row group, in per_sample order."""
    X, tau, grp = [], [], []
    considered = dropped = 0
    for r in per_sample:
        if r["condition"] == "clean":
            t, g = 0, "clean_control"
        elif r["error_type"] != "diagnosis":
            continue
        elif design == "automated":
            t, g = 1, "automated_positive"
        else:
            lab = labels[int(r["idx"])]
            if lab == "ABSENT" or (borderline == "generous" and lab == "BORDERLINE"):
                t, g = 1, "drop_" + lab.lower()
            elif design == "B":
                t, g = 0, "relabeled_" + lab.lower()
            else:
                continue
        considered += 1
        vals = [r.get(k) for k in KEYS]
        if all(v in V.VALID for v in vals):
            X.append([V.LABEL_TO_INT[v] for v in vals])
            tau.append(t)
            grp.append(g)
        else:
            dropped += 1
    return np.array(X, dtype=float), np.array(tau, dtype=float), np.array(grp), dropped


def rate(col, mask):
    k, n = int(col[mask].sum()), int(mask.sum())
    return {"flagged": f"{k}/{n}", "rate": r4(k / n) if n else None}


def flag_rates(X, tau, grp):
    out = {}
    for j, name in enumerate(("llama", "qwen", "nemotron")):
        col = X[:, j]
        d = {"drops_tau1": rate(col, tau == 1), "clean_controls": rate(col, grp == "clean_control")}
        rel = np.char.startswith(grp.astype(str), "relabeled_")
        if rel.any():
            d["relabeled_tau0"] = rate(col, rel)
        out[name] = d
    return out


def permutation_null(X, tau):
    """Nemotron column shuffled across the cell's rows (flag rate kept), N_PERM times, fresh SEED per cell."""
    rng = np.random.default_rng(V.SEED)
    inc = V.phi_v(X[:, :N_INCUMBENT], tau)
    real = V.phi_v(X, tau) - inc
    nulls = np.empty(N_PERM)
    for i in range(N_PERM):
        Xp = X.copy()
        Xp[:, 2] = rng.permutation(X[:, 2])
        nulls[i] = V.phi_v(Xp, tau) - inc
    lo, hi = np.percentile(nulls, [2.5, 97.5])
    return {"real_delta_phi_v": r4(real), "null_mean": r4(nulls.mean()),
            "null_95_range": [r4(lo), r4(hi)], "null_min": r4(nulls.min()), "null_max": r4(nulls.max()),
            "real_outside_null_95": bool(real > hi or real < lo),
            "real_vs_null_95": "above" if real > hi else ("below" if real < lo else "inside"),
            "perm_p_upper": r4((np.sum(nulls >= real) + 1) / (N_PERM + 1)),
            "perm_p_lower": r4((np.sum(nulls <= real) + 1) / (N_PERM + 1)),
            "real_minus_null_mean": r4(real - nulls.mean())}


def mechanism(X, tau):
    """run_prevalence_sensitivity_v2.side_means, plus each side's weighted change in mean b^2 at the cell's own share."""
    m = PS.side_means(X, tau)
    p = float(tau.mean())
    c1, c2 = X[:, :N_INCUMBENT].mean(axis=1), X.mean(axis=1)
    dd1 = float(np.mean((c2[tau == 1] - 1) ** 2) - np.mean((c1[tau == 1] - 1) ** 2))
    dd0 = float(np.mean(c2[tau == 0] ** 2) - np.mean(c1[tau == 0] ** 2))
    m["change_in_mean_b2_at_own_share"] = {"drop_side_p_times_change": r4(p * dd1),
                                           "control_side_1_minus_p_times_change": r4((1 - p) * dd0)}
    return m


def reweighted(X, tau):
    out = {}
    for label, p in TARGETS:
        rw = PS.at_p_raw(X, tau, p, alt=True)
        out[label] = {**PS.fmt(rw), "ci95_fixed_p": [r4(rw["lo_fixed_p"]), r4(rw["hi_fixed_p"])],
                      "band_fixed_p": PS.band(rw["d"], rw["lo_fixed_p"], rw["hi_fixed_p"]),
                      "tau_band": tau_band(rw["d"])}
    return out


def zero_crossing(X, tau):
    """Sign of the reweighted point estimate on the 0.01 grid (point estimates only, no CI)."""
    sign = []
    for p in GRID:
        d = PS.dphi(X, tau, PS.weights(tau, p))
        sign.append((p, "positive" if d > 0 else ("negative" if d < 0 else "zero")))
    return PS.runs(sign)


def cell_record(X, tau, grp, dropped):
    pt, ci = V.paired_delta_cis(X, tau, N_INCUMBENT, rng=np.random.default_rng(V.SEED), n_boot=V.N_BOOT)
    d, lo, hi = pt["phi_v"], ci["phi_v"][0], ci["phi_v"][1]
    rel = int(np.char.startswith(grp.astype(str), "relabeled_").sum())
    return {
        "n": int(len(tau)), "drops_tau1": int(tau.sum()), "clean_controls": int((grp == "clean_control").sum()),
        "relabeled_tau0": rel, "dropped_incomplete": dropped, "prevalence": r4(tau.mean()),
        "own_share": {"phi_incumbent": r4(V.phi_v(X[:, :N_INCUMBENT], tau)), "phi_with_candidate": r4(V.phi_v(X, tau)),
                      "delta_phi_v": r4(d), "ci95": [r4(lo), r4(hi)], "tau_band": tau_band(d),
                      "protocol_band": PS.band(d, lo, hi)},
        "reweighted": reweighted(X, tau),
        "delta_sign_runs_on_grid": zero_crossing(X, tau),
        "permutation_null_own_share": permutation_null(X, tau),
        "flag_rates": flag_rates(X, tau, grp),
        "mechanism": mechanism(X, tau),
    }


def idx_repeat_check(per_sample):
    """For idx that appear on more than one row: on how many does each judge give one verdict on every row. And for
    corrupted rows whose idx is also a clean control's: on how many does each judge's verdict equal the control's."""
    by = {}
    for r in per_sample:
        by.setdefault(r["idx"], []).append(r)
    multi = [rs for rs in by.values() if len(rs) > 1]
    out = {"idx_with_more_than_one_row": len(multi)}
    for k in KEYS:
        out[k.replace("_verdict", "") + "_same_verdict_on_every_row"] = sum(len({r[k] for r in rs}) == 1 for rs in multi)
    clean = {r["idx"]: r for r in per_sample if r["condition"] == "clean"}
    for scope, keep in (("diagnosis", lambda r: r["error_type"] == "diagnosis"), ("all_corrupted", lambda r: True)):
        rows = [r for r in per_sample if r["condition"] == "corrupted" and keep(r) and r["idx"] in clean]
        d = {"rows": len(rows)}
        for k in KEYS:
            d[k.replace("_verdict", "") + "_equal_to_that_control"] = sum(r[k] == clean[r["idx"]][k] for r in rows)
        out[f"{scope}_rows_sharing_idx_with_a_clean_control"] = d
    return out


def _recall(rows, k):
    v = [r[k] for r in rows if r[k] != "ERROR"]
    u = sum(x == "UNSAFE" for x in v)
    return {"n": len(v), "unsafe": u, "recall": r4(u / len(v)) if v else None}


def idx_repeat_by_error_type(per_sample):
    """Per error type: how many corrupted rows the idx-keyed repeat can touch, and each judge's recall (UNSAFE share,
    ERROR verdicts left out, as in README A5) on all corrupted rows, on rows whose idx appears on only one row of the
    file (no other row's verdict can be repeated onto them), on rows whose idx appears on more than one row, and on
    the rows that share their idx with a clean control (there a repeated verdict is the control's)."""
    n_rows = Counter(r["idx"] for r in per_sample)
    clean = {r["idx"]: r for r in per_sample if r["condition"] == "clean"}
    out = {}
    for et in ERROR_TYPES:
        rows = [r for r in per_sample if r["condition"] == "corrupted" and r["error_type"] == et]
        subsets = {"all": rows,
                   "idx_on_one_row_only": [r for r in rows if n_rows[r["idx"]] == 1],
                   "idx_on_more_than_one_row": [r for r in rows if n_rows[r["idx"]] > 1],
                   "idx_shared_with_a_clean_control": [r for r in rows if r["idx"] in clean]}
        shared = subsets["idx_shared_with_a_clean_control"]
        out[et] = {
            "rows": {s: len(v) for s, v in subsets.items()},
            "llama_equal_to_that_control": sum(r["llama_verdict"] == clean[r["idx"]]["llama_verdict"] for r in shared),
            "llama_verdict_on_rows_sharing_idx_with_a_clean_control": dict(sorted(Counter(r["llama_verdict"] for r in shared).items())),
            "recall": {k.replace("_verdict", ""): {s: _recall(v, k) for s, v in subsets.items()} for k in KEYS},
        }
    return out


def overview(cells, at_shares):
    """The ranges and counts the text quotes, read off the cells (hand-label cells only unless named)."""
    hand = {k: c for k, c in cells.items() if k != "automated labels"}
    auto41 = cells["automated labels"]["reweighted"]["0.414"]
    own = [c["own_share"]["delta_phi_v"] for c in hand.values()]
    rw = [c["reweighted"]["0.414"] for c in hand.values()]

    def has0(ci):
        return ci[0] <= 0 <= ci[1]

    return {
        "hand_label_cells": list(hand),
        "own_share_prevalence_range": [min(c["prevalence"] for c in hand.values()),
                                       max(c["prevalence"] for c in hand.values())],
        "own_share_delta_range": [min(own), max(own)],
        "own_share_ci_includes_0": [k for k, c in hand.items() if has0(c["own_share"]["ci95"])],
        "own_share_real_vs_null_95": {k: c["permutation_null_own_share"]["real_vs_null_95"] for k, c in hand.items()},
        "automated_at_hand_label_shares_delta": {k: a["delta_phi_v"] for k, a in at_shares.items()},
        "same_sign_as_automated_at_each_share": bool(all(
            np.sign(hand[k]["own_share"]["delta_phi_v"]) == np.sign(a["delta_phi_v"]) for k, a in at_shares.items())),
        "at_0.414_delta_range": [min(r["delta_phi_v"] for r in rw), max(r["delta_phi_v"] for r in rw)],
        "at_0.414_ci_includes_0": [k for k, c in hand.items() if has0(c["reweighted"]["0.414"]["ci95"])],
        "at_0.414_ci_fixed_p_includes_0": [k for k, c in hand.items() if has0(c["reweighted"]["0.414"]["ci95_fixed_p"])],
        "automated_at_0.414": {"delta_phi_v": auto41["delta_phi_v"], "ci95": auto41["ci95"]},
        "same_sign_as_automated_at_0.414": bool(all(
            np.sign(r["delta_phi_v"]) == np.sign(auto41["delta_phi_v"]) for r in rw)),
    }


def main():
    labels = {int(h["idx"]): h["verdict"] for h in _load(LABELS)}
    assert Counter(labels.values()) == {"PRESENT": 128, "ABSENT": 9, "BORDERLINE": 13}, Counter(labels.values())
    pub = _load(PUBLISHED)["per_sample"]
    gate_file = _load(GATE708)
    gate = gate_file["per_sample"]
    for ps in (pub, gate):
        dx = {int(r["idx"]) for r in ps if r["condition"] == "corrupted" and r["error_type"] == "diagnosis"}
        assert dx == set(labels) and sum(r["condition"] == "clean" for r in ps) == 200

    # ── 1. reproduce results/tau_recompute_summary.json (published pairing) ──
    summ = _load(SUMMARY)
    ref = summ["reference_contaminated_tau"]
    committed = {c["cell"]: c for c in summ["cells"]}
    for design, bl in CELLS:
        X, tau, grp, dropped = build(pub, labels, design, bl)
        pt, ci = V.paired_delta_cis(X, tau, N_INCUMBENT, rng=np.random.default_rng(V.SEED), n_boot=V.N_BOOT)
        got = {"phi_2rater": r4(V.phi_v(X[:, :N_INCUMBENT], tau)), "phi_3rater": r4(V.phi_v(X, tau)),
               "delta_phi_v": r4(pt["phi_v"]), "ci95": [r4(ci["phi_v"][0]), r4(ci["phi_v"][1])],
               "n": int(len(tau)), "pos_tau1": int(tau.sum()), "neg_tau0": int(len(tau) - tau.sum())}
        want = ref if design == "automated" else committed[SUMMARY_NAME[(design, bl)]]
        for k, v in got.items():
            assert want[k] == v, (design, bl, k, want[k], v)
        if design != "automated":
            assert want["dropped_errorNone"] == dropped and want["verdict"] == tau_band(pt["phi_v"]), (design, bl)
        if (design, bl) == ("B", "strict"):
            for j, k in enumerate(KEYS):
                sf = summ["split_f_diagnostic"][k]
                pr, rl = grp == "clean_control", np.char.startswith(grp.astype(str), "relabeled_")
                assert (r4(X[pr, j].mean()), int(pr.sum()), r4(X[rl, j].mean()), int(rl.sum())) == \
                       (sf["fp_pristine_controls"], sf["n_pristine"], sf["fp_relabeled_present_borderline"],
                        sf["n_relabeled"]), k
    assert abs(P_REF - ref["pos_tau1"] / ref["n"]) < 1e-15

    # the automated-label cell under the deployed prompt is results/consensus_accuracy.json's gate-prompt figure
    cg = _load(CONSENSUS)["per_stratum"]["diagnosis"]["decomposition_gate_prompt"]
    Xg, tg, _, _ = build(gate, labels, "automated", None)
    assert (r4(V.phi_v(Xg[:, :N_INCUMBENT], tg)), r4(V.phi_v(Xg, tg)),
            r4(V.paired_delta(Xg, tg, N_INCUMBENT)["phi_v"])) == (cg["phi_v_2"], cg["phi_v_3"], cg["delta_phi_v"])

    # ── 2-4. both pairings, all five cells ──
    pairings = {
        "published_mixed_prompt": {
            "source": "nemotron_calibration_full.json",
            "prompts": ("Llama and Qwen: Project v1's stored verdicts (nemotron_judge_test.py:13, "
                        "'Data (from the original repo): results/nebius_evidence/calibration_verdicts.json'); in Project v1's "
                        "repo at commit dd6681b (github.com/deepset01-sys/medisimplifier-nebius, not part of this repo) "
                        "that file is written by perturbation_calibration.py:193-227 with a one-word prompt, one user "
                        "message and max_tokens 2000. Nemotron: the 4-step "
                        "CoT JSON prompt with a system message, max_tokens 8000, response_format json_object, run by "
                        "nemotron_judge_test.py (:78-124). The judges did not share a prompt or settings."),
            "per_sample": pub},
        "matched_deployed_prompt": {
            "source": "results/gate_calibration_full.json",
            "prompts": ("all three judges under one prompt, same 708 items; the file's prompt_source: "
                        f"{gate_file['prompt_source']!r} (src/safety_gate.py JUDGE_PROMPT: four steps, then a one-word "
                        "answer), run through safety_gate.evaluate_safety by src/run_gate_calibration.py: max_tokens "
                        "2000 for Llama, 8000 for Qwen and Nemotron (safety_gate.py:104-106)"),
            "per_sample": gate},
    }
    out = {
        "purpose": ("Reproduces results/tau_recompute_summary.json (the automated-pass diagnosis stratum re-scored with "
                    "the 150-item hand audit), rebuilds its cells with all three judges under one prompt, and puts every "
                    "cell on a common drop share."),
        "status": "post hoc; not part of any pre-registered protocol",
        "sources": {"labels": "results/tau_hand_labels_150.json (128 PRESENT, 9 ABSENT, 13 BORDERLINE)",
                    "reproduced": "results/tau_recompute_summary.json (every cell, CI and split_f_diagnostic asserted)",
                    "also_reproduced": ("results/consensus_accuracy.json per_stratum.diagnosis.decomposition_gate_prompt "
                                        "(the matched automated-label cell)")},
        "designs": {
            "automated labels": "all 150 automated diagnosis items tau=1 (the cell behind the +0.0706)",
            "A": "hand-confirmed drops tau=1; the other automated diagnosis items removed",
            "B": "hand-confirmed drops tau=1; the other automated diagnosis items kept as tau=0",
            "strict / generous": "BORDERLINE counted as not a drop / as a drop",
            "all": "all 200 clean controls tau=0; complete-case on Llama, Qwen, Nemotron"},
        "method": {
            "own_share": "vagt_core.paired_delta_cis, SEED=42, n_boot=1000 (the summary's pipeline)",
            "reweighted": ("scripts/run_prevalence_sensitivity_v2.py at_p_raw: drops weighted p/n1, controls (1-p)/n0; "
                           "ci95 keeps each resampled row's weight, ci95_fixed_p recomputes the weights in each replicate. "
                           "Targets: 138/333 = 0.4144 (the published reference cell's share) and 0.50"),
            "permutation_null_own_share": ("Nemotron column shuffled across the cell's own rows, n_perm=1000, "
                                           "default_rng(42) per cell; perm_p_upper = P(null >= real), perm_p_lower = "
                                           "P(null <= real), both (count+1)/(n_perm+1)"),
            "no_reweighted_null": "as in run_prevalence_sensitivity_v2.py: a within-sample shuffle keeps the sample's flag rate, not the rate at p",
            "delta_sign_runs_on_grid": "sign of the reweighted point estimate on the 0.01-0.99 grid (no CI)",
            "overview": ("ranges and counts read off the cells; 'ci_includes_0' lists cells whose CI contains 0 "
                         "(kept-weights ci95 unless named fixed_p); real_vs_null_95 places the real Delta against the "
                         "shuffled null's 2.5-97.5 percentile range"),
            "automated_cell_at_hand_label_shares": ("the automated-label cell (same pairing) reweighted to each "
                                                    "hand-label cell's own drop share, same conventions as reweighted"),
            "mechanism": ("run_prevalence_sensitivity_v2.side_means: within-side mean b^2 for [Llama+Qwen, with "
                          "Nemotron]; change_in_mean_b2_at_own_share weights each side's change by the cell's share"),
        },
        "bands": {"tau_band": summ["preregistered_bands"],
                  "tau_band_note": ("the bands recorded in results/tau_recompute_summary.json; point estimate only. "
                                    "The file names them preregistered_bands; in git they first appear in c716472 "
                                    "(2026-09-19), the commit that reports the results"),
                  "protocol_band": "docs/judgebench_v2_protocol.md §8 (via run_prevalence_sensitivity_v2.band), applied descriptively"},
        "pairings": {},
    }
    for name, pr in pairings.items():
        cells = {}
        for design, bl in CELLS:
            X, tau, grp, dropped = build(pr["per_sample"], labels, design, bl)
            cells[cell_name(design, bl)] = cell_record(X, tau, grp, dropped)
        # the reverse direction: the automated-label cell reweighted to each hand-label cell's own share
        Xa, ta, _, _ = build(pr["per_sample"], labels, "automated", None)
        at_shares = {}
        for cname, c in cells.items():
            if cname == "automated labels":
                continue
            p = c["drops_tau1"] / c["n"]
            rw = PS.at_p_raw(Xa, ta, p, alt=True)
            at_shares[cname] = {"share": r4(p), **PS.fmt(rw),
                                "ci95_fixed_p": [r4(rw["lo_fixed_p"]), r4(rw["hi_fixed_p"])],
                                "tau_band": tau_band(rw["d"])}
        out["pairings"][name] = {"source": pr["source"], "prompts": pr["prompts"],
                                 "idx_repeat_check": idx_repeat_check(pr["per_sample"]),
                                 "idx_repeat_by_error_type": idx_repeat_by_error_type(pr["per_sample"]), "cells": cells,
                                 "automated_cell_at_hand_label_shares": at_shares,
                                 "overview": overview(cells, at_shares)}

    # reweighting the published reference cell to its own share reproduces the committed +0.0706 and CI
    pref = out["pairings"]["published_mixed_prompt"]["cells"]["automated labels"]["reweighted"]["0.414"]
    assert (pref["delta_phi_v"], pref["ci95"]) == (ref["delta_phi_v"], ref["ci95"]), pref

    # the published pairing's all-row recall reproduces README A5's dose/lateral/negation rows
    ib = out["pairings"]["published_mixed_prompt"]["idx_repeat_by_error_type"]
    for et, want in A5_RECALL.items():
        got = tuple(round(100 * ib[et]["recall"][j]["all"]["unsafe"] / ib[et]["recall"][j]["all"]["n"])
                    for j in ("nemotron", "llama", "qwen"))
        assert got == want, (et, got, want)
    out["idx_repeat_by_error_type_note"] = (
        "idx_repeat_by_error_type splits the corrupted rows of each error type by how their idx occurs in the file: "
        "rows whose idx is on only one row, which no other row's verdict can be repeated onto; rows whose idx is on more "
        "than one row, where Llama's stored column gives one verdict to every row of the idx (idx_repeat_check); and, "
        "among those, rows that share their idx with a clean control, where the repeated verdict is the control's. "
        "recall is the UNSAFE share with ERROR verdicts left out, as in README A5. The subsets differ in items as well, "
        "so Qwen, Nemotron and the deployed-prompt re-run (matched_deployed_prompt, where Llama was run afresh) are "
        "given on the same subsets for comparison.")
    out["idx_repeat_note"] = ("idx_repeat_check counts, among idx that appear on more than one row (a clean control and "
                              "one or more corrupted versions, or several corrupted versions), those where a judge gave the "
                              "same verdict on every row; and, for corrupted rows whose idx is also a clean control's, "
                              "those where a judge's verdict equals its verdict on that control")
    assert PS.CLAMP[0] == 0, PS.CLAMP[0]
    out["checks"] = {"sigma_B_clamp_bound": PS.CLAMP[0],
                     "asserted": ["hand labels 128 PRESENT / 9 ABSENT / 13 BORDERLINE; the 150 labelled idx are the "
                                  "diagnosis items of both files; 200 clean controls in each",
                                  "every tau_recompute_summary.json cell: phi_2rater, phi_3rater, delta_phi_v, ci95, n, "
                                  "pos_tau1, neg_tau0, dropped_errorNone, verdict",
                                  "tau_recompute_summary.json split_f_diagnostic (all three judges)",
                                  "consensus_accuracy.json gate-prompt diagnosis phi_v_2, phi_v_3, delta_phi_v",
                                  "reweighting the published reference cell to its own share (138/333) reproduces its "
                                  "delta and CI",
                                  "sigma_B never clamped in the reweighted runs",
                                  "README A5 dose/lateral/negation recall (Nemotron, Llama, Qwen) from the published "
                                  "pairing's idx_repeat_by_error_type all-row recall"]}
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ── print ──
    print(f"Automated-pass diagnosis re-score (SEED={V.SEED}, n_boot={V.N_BOOT}, n_perm={N_PERM})\n")
    for name, pr in out["pairings"].items():
        print(f"{name}  ({pr['source']})")
        for cname, c in pr["cells"].items():
            o, nl = c["own_share"], c["permutation_null_own_share"]
            print(f"  {cname:17} n={c['n']:3} drops={c['drops_tau1']:3} p={c['prevalence']:.3f}  "
                  f"d={o['delta_phi_v']:+.4f} [{o['ci95'][0]:+.4f},{o['ci95'][1]:+.4f}] {o['tau_band']:10} | "
                  f"null {nl['null_mean']:+.4f} [{nl['null_95_range'][0]:+.4f},{nl['null_95_range'][1]:+.4f}] "
                  f"p_up={nl['perm_p_upper']:.3f} p_lo={nl['perm_p_lower']:.3f}")
            for lab, rw in c["reweighted"].items():
                print(f"      @p={lab}: {rw['delta_phi_v']:+.4f} [{rw['ci95'][0]:+.4f},{rw['ci95'][1]:+.4f}] "
                      f"fixed-p [{rw['ci95_fixed_p'][0]:+.4f},{rw['ci95_fixed_p'][1]:+.4f}] {rw['band']} / {rw['tau_band']}")
            print("      sign on grid:", ", ".join(f"{r['from']:.2f}-{r['to']:.2f} {r['value']}"
                                                   for r in c["delta_sign_runs_on_grid"]))
        for cname, a in pr["automated_cell_at_hand_label_shares"].items():
            print(f"  automated-label cell at {cname}'s share {a['share']:.3f}: {a['delta_phi_v']:+.4f} "
                  f"[{a['ci95'][0]:+.4f},{a['ci95'][1]:+.4f}] {a['band']} / {a['tau_band']}")
    for name, pr in out["pairings"].items():
        print(f"{name} overview:", json.dumps(pr["overview"], ensure_ascii=False))
        print(f"{name} idx_repeat_check:", json.dumps(pr["idx_repeat_check"]))
        for et, d in pr["idx_repeat_by_error_type"].items():
            rc = d["recall"]
            print(f"  {et:9} rows {d['rows']}  " + "  ".join(
                f"{j} all {rc[j]['all']['unsafe']}/{rc[j]['all']['n']} one-row {rc[j]['idx_on_one_row_only']['unsafe']}/"
                f"{rc[j]['idx_on_one_row_only']['n']}" for j in ("llama", "qwen", "nemotron")))
    print(f"\nSaved -> {OUT}")


if __name__ == "__main__":
    main()
